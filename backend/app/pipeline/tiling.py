"""
STAGE 1 TILING -- splits a full input image into overlapping, GSD-matched
tiles (the size the depth model can actually see cleanly -- see
stage1_depth's module docstring on why a wide image fed in directly
produces nonsense), runs Stage 1 (+ optional land-cover) on each tile
independently, and stitches the per-tile outputs back into ONE set of
canvases covering the FULL original image extent -- not just one
center-cropped tile, which is what the single-shot path did.

CALIBRATION HAPPENS ONCE, AFTER STITCHING, NOT PER TILE. Fitting a
separate Stage 2 calibration per tile would let neighboring tiles
independently disagree on absolute scale/offset and produce a visible
height seam at every tile boundary. Instead this module only stitches
relative height (+ confidence + land-cover); pipeline.py's tiled entry
points run stage2_calibration exactly once against the stitched full
canvas, reusing those functions completely unchanged.
"""
import numpy as np
from PIL import Image

from app.pipeline import stage1_depth

MODEL_INPUT_SIZE = stage1_depth.MODEL_INPUT_SIZE


def compute_tile_grid(image_shape, tile_side_px: int, overlap_frac: float = 0.2):
    """
    Returns (list of (top, left) tile origins, actual tile_side_px used)
    covering image_shape with tile_side_px x tile_side_px tiles and
    overlap_frac overlap between neighbors.

    Edge tiles are SHIFTED INWARD (not padded, not cropped smaller) so
    every tile is always the full tile_side_px x tile_side_px and the
    entire image is always covered, including the case where the image
    is smaller than one tile (returns a single, full-image tile).
    """
    h, w = image_shape[0], image_shape[1]
    tile_side_px = max(1, min(tile_side_px, h, w))
    stride = max(1, int(tile_side_px * (1 - overlap_frac)))

    def _origins(size, tile, stride):
        if size <= tile:
            return [0]
        origins = list(range(0, size - tile + 1, stride))
        if origins[-1] != size - tile:
            origins.append(size - tile)  # guarantee the far edge is covered
        return origins

    tops = _origins(h, tile_side_px, stride)
    lefts = _origins(w, tile_side_px, stride)
    return [(top, left) for top in tops for left in lefts], tile_side_px


def _feather_weight(tile_side_px: int) -> np.ndarray:
    """
    2D raised-cosine (Hann) weight window, high in the tile center and
    tapering toward the edges, so overlapping tiles blend smoothly
    instead of one tile's output just stopping and another's starting
    (a hard seam). Never fully zero at the edge -- a tile at the image
    boundary (no neighbor to blend with there) still needs real weight
    at its own edge, not zero.
    """
    if tile_side_px <= 1:
        return np.ones((max(1, tile_side_px), max(1, tile_side_px)))
    ramp = np.hanning(tile_side_px)
    ramp = np.clip(ramp, 1e-3, None)
    return np.outer(ramp, ramp)


def _resize_float(arr: np.ndarray, target_side: int) -> np.ndarray:
    """Bilinear-resizes a float 2D array to (target_side, target_side)."""
    if arr.shape[0] == target_side and arr.shape[1] == target_side:
        return arr
    img = Image.fromarray(arr.astype(np.float32), mode="F")
    return np.array(img.resize((target_side, target_side), Image.BILINEAR))


def _resize_classes_nearest(arr: np.ndarray, target_side: int) -> np.ndarray:
    """
    Nearest-neighbor-resizes an integer class-ID 2D array. Never
    interpolate class IDs -- bilinear/bicubic between e.g. building=3
    and road=5 would invent a nonexistent class value at the boundary.
    """
    if arr.shape[0] == target_side and arr.shape[1] == target_side:
        return arr
    img = Image.fromarray(arr.astype(np.int32), mode="I")
    return np.array(img.resize((target_side, target_side), Image.NEAREST)).astype(np.int64)


def _align_tile_to_canvas(tile_height: np.ndarray, height_accum: np.ndarray,
                           weight_accum: np.ndarray, region) -> np.ndarray:
    """
    Rescales/offsets `tile_height` (this tile's raw relative-height output,
    on its own arbitrary scale-invariant-model scale) to match whatever has
    already been accumulated into the canvas in `region`, using ONLY the
    pixels that already have real weight there (i.e. the overlap with
    previously-placed tiles). First tile placed has no overlap yet -- it
    defines the canvas's scale and passes through unchanged.

    Without this, two tiles can each be internally correct but sit on
    different absolute relative-height scales (scale-invariant loss makes
    no promise they'll agree), and a purely spatial (Hann) blend between
    them produces a sharp value discontinuity right at the tile boundary --
    a straight/diagonal seam that tracks the tile grid, not the terrain.

    Fit is least-squares scale (a) + offset (b): a*tile + b ~= existing
    canvas value, solved only over already-covered pixels in this tile's
    footprint.

    FIX: this used to bail out to complete identity (a=1, b=0 -- NO
    correction at all) whenever the overlap region had near-zero
    variance (`np.ptp(tile_vals) < 1e-6`). That guard was meant for a
    genuinely degenerate case, but near-constant overlap is actually the
    COMMON case -- flat rooftops, roads, open ground/pavement, i.e.
    exactly the areas most likely to sit at a tile seam. A flat overlap
    means SCALE (the slope `a`) can't be reliably estimated (there's no
    variation to fit a slope against), but the OFFSET absolutely still
    can be: just the weighted mean difference between this tile and
    what's already in the canvas there. Skipping correction entirely
    left this tile's own mismatched absolute scale (scale-invariant
    model, no promise of agreement between tiles) blend straight into
    the canvas via the Hann window -- and because that window is peaked
    at the tile's own center and tapers to ~0 at its edges, an unaligned
    tile's mismatch shows up as a four-sided tent/pyramid centered on the
    tile, exactly the "spike out of nowhere on flat ground" artifact this
    was supposed to prevent in the first place.

    Never produces NaNs: only truly falls back to identity when there's
    no overlap to compare against at all (first tile placed).
    """
    existing_weight = weight_accum[region]
    covered = existing_weight > 1e-6
    if not np.any(covered):
        return tile_height  # nothing to align against yet -- first tile

    existing_height = height_accum[region][covered] / existing_weight[covered]
    tile_vals = tile_height[covered]
    w = existing_weight[covered]

    if tile_vals.size < 2 or np.ptp(tile_vals) < 1e-6:
        # Can't fit a reliable slope on a flat/near-constant overlap, but
        # an offset-only correction (a=1, weighted-mean b) still fixes
        # the far more common failure mode here: this tile's whole
        # absolute level disagreeing with its neighbor's.
        b = float(np.average(existing_height - tile_vals, weights=w))
        return tile_height + b

    # Weighted least squares (weight by existing confidence in that pixel)
    # for [a, b] in a*tile_vals + b = existing_height.
    A = np.stack([tile_vals, np.ones_like(tile_vals)], axis=1)
    W = np.sqrt(w)[:, None]
    try:
        sol, *_ = np.linalg.lstsq(A * W, existing_height * np.sqrt(w), rcond=None)
        a, b = sol
    except np.linalg.LinAlgError:
        # Same offset-only fallback if the full affine fit fails for any
        # other numerical reason -- still better than no correction.
        b = float(np.average(existing_height - tile_vals, weights=w))
        return tile_height + b

    if not np.isfinite(a) or not np.isfinite(b) or abs(a) < 1e-6:
        return tile_height  # degenerate fit -- don't blow up the tile

    return tile_height * a + b


def run_tiled_stage1(rgb_image: np.ndarray, model, landcover_model=None,
                      source_gsd_m: float = None, with_uncertainty: bool = False,
                      overlap_frac: float = 0.2, max_tiles: int = 64):
    """
    Runs Stage 1 (+ optional land-cover) over the FULL rgb_image via
    overlapping GSD-matched tiles, stitching the results into single
    full-resolution canvases (same H, W as rgb_image).

    Tile size is computed with the SAME formula normalize_gsd() uses for
    its single crop (target_gsd_m * model_input_size / source_gsd_m, or
    exactly model_input_size if source_gsd_m is unknown) -- tiling changes
    HOW MANY of these GSD-correct regions get processed and stitched, not
    what "a correctly-scaled tile" means.

    max_tiles is a safety cap: a very large image at a fine GSD could
    otherwise generate an impractically large number of tiles. If the
    naive grid would exceed it, tile_side_px is grown (fewer, larger
    tiles processed at a coarser effective scale) rather than silently
    covering only part of the image.

    Returns (relative_height, confidence_map, landcover_mask, gsd_info):
        relative_height: (H, W) float32, stitched
        confidence_map: (H, W) float32, stitched, or None if
            with_uncertainty=False
        landcover_mask: (H, W) int64, stitched, or None if no
            landcover_model given. Stitched via HARD per-pixel assignment
            to whichever tile's feather weight is highest at that pixel
            (i.e. nearest tile center wins) -- blending/averaging discrete
            class IDs across tiles is meaningless (building=3 and
            water=4 don't "average" to anything real), so this is a clean
            per-pixel choice between tiles rather than a smoothed value.
        gsd_info: dict describing the tile grid actually used (tile size,
            tile count, overlap) -- shipped through to the API response's
            metadata the same way normalize_gsd's info dict always was.
    """
    from app.models import landcover_model as landcover_model_module

    h, w = rgb_image.shape[0], rgb_image.shape[1]

    if source_gsd_m is None:
        tile_side_px = MODEL_INPUT_SIZE
        gsd_mode = "assumed_no_metadata"
    else:
        computed = stage1_depth.GAMUS_IMPLIED_GSD_M * MODEL_INPUT_SIZE / source_gsd_m
        tile_side_px = max(1, round(computed))
        gsd_mode = "computed"

    tile_origins, tile_side_px = compute_tile_grid((h, w), tile_side_px, overlap_frac)

    while len(tile_origins) > max_tiles and tile_side_px < max(h, w):
        tile_side_px = int(tile_side_px * 1.5)
        tile_origins, tile_side_px = compute_tile_grid((h, w), tile_side_px, overlap_frac)

    window = _feather_weight(tile_side_px)

    height_accum = np.zeros((h, w), dtype=np.float64)
    weight_accum = np.zeros((h, w), dtype=np.float64)
    conf_accum = np.zeros((h, w), dtype=np.float64) if with_uncertainty else None

    lc_mask = np.zeros((h, w), dtype=np.int64) if landcover_model is not None else None
    lc_best_weight = np.zeros((h, w), dtype=np.float64) if landcover_model is not None else None

    for (top, left) in tile_origins:
        tile_rgb = rgb_image[top:top + tile_side_px, left:left + tile_side_px]

        # This crop is already exactly tile_side_px (GSD-correct) on a
        # side, so normalize_gsd's own center-crop reduces to a no-op --
        # this call only resizes it to the model's fixed input size (and
        # applies the same upscale-sharpening normalize_gsd always does).
        resized_tile, _ = stage1_depth.normalize_gsd(
            tile_rgb, source_gsd_m=source_gsd_m, model_input_size=MODEL_INPUT_SIZE
        )

        if with_uncertainty:
            tile_height, tile_conf = stage1_depth.run_inference_with_uncertainty(resized_tile, model)
        else:
            tile_height = stage1_depth.run_inference(resized_tile, model)
            tile_conf = None

        tile_height_native = _resize_float(tile_height, tile_side_px)

        region = np.s_[top:top + tile_side_px, left:left + tile_side_px]

        # Reconcile this tile's arbitrary relative-height scale with
        # whatever's already been placed in the canvas (see
        # _align_tile_to_canvas docstring) BEFORE blending it in -- doing
        # this after would just blend two already-mismatched scales.
        tile_height_native = _align_tile_to_canvas(
            tile_height_native, height_accum, weight_accum, region
        )

        height_accum[region] += tile_height_native * window
        weight_accum[region] += window

        if with_uncertainty and tile_conf is not None:
            tile_conf_native = _resize_float(tile_conf, tile_side_px)
            conf_accum[region] += tile_conf_native * window

        if landcover_model is not None:
            tile_lc = landcover_model_module.run_landcover_inference(resized_tile, landcover_model)
            tile_lc_native = _resize_classes_nearest(tile_lc, tile_side_px)

            region_best_weight = lc_best_weight[region]
            this_tile_wins = window > region_best_weight
            region_mask = lc_mask[region]
            region_mask[this_tile_wins] = tile_lc_native[this_tile_wins]
            lc_mask[region] = region_mask
            lc_best_weight[region] = np.maximum(region_best_weight, window)

    weight_accum[weight_accum == 0] = 1.0  # defensive only -- compute_tile_grid guarantees full coverage
    relative_height = (height_accum / weight_accum).astype(np.float32)

    confidence_map = None
    if with_uncertainty:
        confidence_map = (conf_accum / weight_accum).astype(np.float32)

    landcover_mask = lc_mask if landcover_model is not None else None

    gsd_info = {
        "mode": f"tiled_{gsd_mode}",
        "source_gsd_m": source_gsd_m,
        "target_gsd_m": stage1_depth.GAMUS_IMPLIED_GSD_M,
        "tile_side_px": int(tile_side_px),
        "original_shape": (h, w),
        "n_tiles": len(tile_origins),
        "overlap_frac": overlap_frac,
    }
    return relative_height, confidence_map, landcover_mask, gsd_info
