"""
Pipeline orchestrator -- wires Stage 1 (depth) -> Stage 2 (calibration)
together. This is the FIRST place these two stages actually run back to
back; until now they'd only been tested independently (Stage 1 against a
real checkpoint, Stage 2 against synthetic data).

Two calibration paths, matching Stage 2's own two entry points:
  - georeferenced input (real or stand-in SRTM available) -> absolute DSM
    via per-class calibration (Innovation #1)
  - non-georeferenced input (no SRTM) -> normalized rDSM, no absolute scale

Stage 3 (mesh) is NOT wired in yet -- this stops at a calibrated height map.
"""
import numpy as np

from app.pipeline import stage1_depth
from app.pipeline import stage2_calibration


def run_stage1_to_stage2_georeferenced(
    rgb_image: np.ndarray,
    model,
    srtm_reference: np.ndarray,
    landcover_mask: np.ndarray = None,
    landcover_model=None,
    source_gsd_m: float = None,
    with_uncertainty: bool = False,
):
    """
    Full georeferenced path: RGB -> relative height (Stage 1) -> absolute
    DSM anchored to `srtm_reference` (Stage 2).

    srtm_reference must already be resampled to rgb_image's shape (that's
    srtm_utils.resample_to_match's job, not this function's -- kept
    separate since a stand-in reference, e.g. GAMUS's own height map used
    for wiring tests before live SRTM fetch works, won't need resampling
    the same way a real fetched SRTM tile would).

    Land-cover mask for Innovation #1 (per-class calibration), in priority order:
      1. `landcover_mask` passed in directly (e.g. GAMUS ground-truth mask for testing)
      2. predicted from `landcover_model` if one is supplied (the real inference-time
         path -- a real upload has no ground-truth mask, only RGB)
      3. neither given -> falls back to a single global affine fit, still correct,
         just without the innovation

    Whichever mask is used is computed AFTER GSD-normalization so it's pixel-aligned
    with the depth output and srtm_reference with no separate resize step to get wrong.

    Returns a dict with everything downstream stages / the API / debugging
    would want: the raw relative height, the calibrated absolute DSM, the
    GSD-normalization info, and (if with_uncertainty) the TTA confidence map.
    """
    normalized_image, gsd_info = stage1_depth.normalize_gsd(
        rgb_image, source_gsd_m=source_gsd_m
    )

    if normalized_image.shape[:2] != srtm_reference.shape:
        raise ValueError(
            f"srtm_reference shape {srtm_reference.shape} does not match "
            f"the GSD-normalized image shape {normalized_image.shape[:2]}. "
            f"Resample srtm_reference to match before calling this "
            f"(see srtm_utils.resample_to_match), or pass a stand-in "
            f"reference that's already the right shape."
        )

    if landcover_mask is None and landcover_model is not None:
        from app.models import landcover_model as landcover_model_module
        landcover_mask = landcover_model_module.run_landcover_inference(
            normalized_image, landcover_model
        )

    if landcover_mask is not None and landcover_mask.shape != srtm_reference.shape:
        raise ValueError(
            f"landcover_mask shape {landcover_mask.shape} must match "
            f"srtm_reference shape {srtm_reference.shape}."
        )

    confidence_map = None
    if with_uncertainty:
        relative_height, confidence_map = stage1_depth.run_inference_with_uncertainty(
            normalized_image, model
        )
    else:
        relative_height = stage1_depth.run_inference(normalized_image, model)

    if landcover_mask is not None:
        calibrated_dsm, per_class_params = stage2_calibration.per_class_calibration(
            relative_height, srtm_reference, landcover_mask
        )
        calibration_method = "per_class"
    else:
        a, b, calibrated_dsm = stage2_calibration.global_affine_fit(
            relative_height, srtm_reference
        )
        per_class_params = {"a": a, "b": b}
        calibration_method = "global_affine"

    return {
        "relative_height": relative_height,
        "calibrated_dsm": calibrated_dsm,
        "confidence_map": confidence_map,
        "calibration_method": calibration_method,
        "calibration_params": per_class_params,
        "gsd_info": gsd_info,
        "normalized_image": normalized_image,
        # BUG FIX: this was never returned, so routes.py's
        # pipeline_out.get("landcover_mask") always came back None for the
        # georeferenced path, which silently disabled Stage 3's
        # flatten_planar_classes for every GeoTIFF/SRTM
        # image -- exactly the path with real absolute heights worth cleaning.
        "landcover_mask": landcover_mask,
    }


def run_tiled_stage1_to_stage2_georeferenced(
    rgb_image: np.ndarray,
    model,
    srtm_reference: np.ndarray,
    landcover_mask: np.ndarray = None,
    landcover_model=None,
    source_gsd_m: float = None,
    with_uncertainty: bool = False,
    overlap_frac: float = None,
):
    """
    Tiled version of run_stage1_to_stage2_georeferenced: splits rgb_image
    into overlapping GSD-matched tiles (tiling.run_tiled_stage1), runs
    Stage 1 (+ land-cover) per tile, stitches into ONE full-resolution
    canvas covering the WHOLE input image, then runs Stage 2 calibration
    ONCE against srtm_reference over that full canvas -- not per tile,
    see tiling.py's module docstring for why (a per-tile calibration
    would let neighboring tiles disagree on absolute scale and produce a
    seam at every tile boundary; stitching relative height first and
    calibrating once afterward avoids that by construction).

    BUG FIX vs. the single-crop path: srtm_reference is expected at
    rgb_image's FULL native resolution (that's what routes.py's
    srtm_utils.resample_to_match already produces, and always did) -- the
    single-crop path instead produced a 512x512-cropped normalized_image
    and compared IT against srtm_reference's full-resolution shape, which
    would raise a shape-mismatch for any real upload that wasn't already
    exactly 512x512. Tiling fixes this as a side effect, simply by using
    the full-resolution canvas as "normalized_image" instead of one crop.

    landcover_mask passed in directly (e.g. GAMUS ground truth for
    testing) still takes priority over landcover_model, same as the
    single-crop path.
    """
    from app.pipeline import tiling
    from app import config

    if overlap_frac is None:
        overlap_frac = config.TILE_OVERLAP_FRAC

    relative_height, confidence_map, landcover_mask_tiled, gsd_info = tiling.run_tiled_stage1(
        rgb_image, model,
        landcover_model=(landcover_model if landcover_mask is None else None),
        source_gsd_m=source_gsd_m, with_uncertainty=with_uncertainty,
        overlap_frac=overlap_frac, max_tiles=config.MAX_TILES,
    )

    if landcover_mask is None:
        landcover_mask = landcover_mask_tiled

    if relative_height.shape != srtm_reference.shape:
        raise ValueError(
            f"Stitched relative_height shape {relative_height.shape} does not "
            f"match srtm_reference shape {srtm_reference.shape}. srtm_reference "
            f"must be resampled to rgb_image's own full shape (see "
            f"srtm_utils.resample_to_match) before calling this."
        )
    if landcover_mask is not None and landcover_mask.shape != srtm_reference.shape:
        raise ValueError(
            f"landcover_mask shape {landcover_mask.shape} must match "
            f"srtm_reference shape {srtm_reference.shape}."
        )

    if landcover_mask is not None:
        calibrated_dsm, per_class_params = stage2_calibration.per_class_calibration(
            relative_height, srtm_reference, landcover_mask
        )
        calibration_method = "per_class"
    else:
        a, b, calibrated_dsm = stage2_calibration.global_affine_fit(
            relative_height, srtm_reference
        )
        per_class_params = {"a": a, "b": b}
        calibration_method = "global_affine"

    return {
        "relative_height": relative_height,
        "calibrated_dsm": calibrated_dsm,
        "confidence_map": confidence_map,
        "calibration_method": calibration_method,
        "calibration_params": per_class_params,
        "gsd_info": gsd_info,
        # Full-resolution canvas, not one 512x512 crop -- this IS the
        # whole input image (RGB texture for the full DSM/mask).
        "normalized_image": rgb_image,
        "landcover_mask": landcover_mask,
    }


def run_tiled_stage1_only_nongeoreferenced(
    rgb_image: np.ndarray,
    model,
    source_gsd_m: float = None,
    with_uncertainty: bool = False,
    landcover_mask: np.ndarray = None,
    landcover_model=None,
    overlap_frac: float = None,
):
    """
    Tiled version of run_stage1_only_nongeoreferenced: same tiling +
    stitching as the georeferenced tiled path, minus the SRTM calibration
    step (normalize_for_visualization instead, exactly as the single-crop
    path did).
    """
    from app.pipeline import tiling
    from app import config

    if overlap_frac is None:
        overlap_frac = config.TILE_OVERLAP_FRAC

    relative_height, confidence_map, landcover_mask_tiled, gsd_info = tiling.run_tiled_stage1(
        rgb_image, model,
        landcover_model=(landcover_model if landcover_mask is None else None),
        source_gsd_m=source_gsd_m, with_uncertainty=with_uncertainty,
        overlap_frac=overlap_frac, max_tiles=config.MAX_TILES,
    )

    if landcover_mask is None:
        landcover_mask = landcover_mask_tiled

    normalized_rdsm = stage2_calibration.normalize_for_visualization(relative_height)

    return {
        "relative_height": relative_height,
        "normalized_rdsm": normalized_rdsm,
        "confidence_map": confidence_map,
        "calibration_method": "none_relative_only",
        "gsd_info": gsd_info,
        "normalized_image": rgb_image,
        "landcover_mask": landcover_mask,
    }


def run_stage1_only_nongeoreferenced(
    rgb_image: np.ndarray,
    model,
    source_gsd_m: float = None,
    with_uncertainty: bool = False,
    landcover_mask: np.ndarray = None,
    landcover_model=None,
):
    """
    Non-georeferenced path: RGB -> relative height (Stage 1) -> normalized
    rDSM (Stage 2's normalize_for_visualization, no SRTM anchor -> no
    absolute scale).
    
    Land-cover mask can be provided or generated for plane-flattening
    in Stage 3, even though we don't use it for calibration in Stage 2.
    """
    normalized_image, gsd_info = stage1_depth.normalize_gsd(
        rgb_image, source_gsd_m=source_gsd_m
    )

    if landcover_mask is None and landcover_model is not None:
        from app.models import landcover_model as landcover_model_module
        landcover_mask = landcover_model_module.run_landcover_inference(
            normalized_image, landcover_model
        )

    confidence_map = None
    if with_uncertainty:
        relative_height, confidence_map = stage1_depth.run_inference_with_uncertainty(
            normalized_image, model
        )
    else:
        relative_height = stage1_depth.run_inference(normalized_image, model)

    normalized_rdsm = stage2_calibration.normalize_for_visualization(relative_height)

    return {
        "relative_height": relative_height,
        "normalized_rdsm": normalized_rdsm,
        "confidence_map": confidence_map,
        "calibration_method": "none_relative_only",  # non-georeferenced path doesn't calibrate to SRTM
        "gsd_info": gsd_info,
        "normalized_image": normalized_image,
        "landcover_mask": landcover_mask,
    }
