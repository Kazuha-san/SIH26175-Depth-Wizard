"""
STAGE 3 -- Mesh prep + generation.

Two related but separable jobs live here:

1. SHAPE CLEANUP + SMOOOTHING (numpy/opencv, cheap, fast to iterate):
   - flatten_planar_classes(): per-instance plane-fit snapping on
     "should be flat-topped" classes (buildings), using the land-cover
     mask -- this is the fix for the domed/blobby building shapes seen
     during Stage 1 evaluation, done as POST-processing on the height
     map rather than by fighting the depth model's loss function (that
     approach -- structure_loss -- was tried and reverted; see
     stage1_depth.py's module docstring for why).
   - smooth_dsm(): edge-aware guided-filter smoothing (reuses
     utils.image_utils.guided_filter) to remove pixel-level speckle
     without smearing real edges.

2. MESH GENERATION + PACKAGING:
   - generate_mesh(): turns a (H, W) height map into an actual
     triangulated 3D mesh (vertices/faces/UVs), for two consumption
     paths:
       a) exported as a standalone .glb (export_mesh_glb) -- a real,
          downloadable, standalone 3D asset (satisfies "standalone
          deployability" independent of the live viewer), viewable in
          any glTF viewer, not just our own frontend.
       b) packaged as lightweight JSON (package_result_for_frontend)
          for the Three.js viewer to build its OWN mesh client-side
          (frontend/src/components/viewport/meshBuilder.js) via GPU
          vertex displacement -- this is the live, navigable flythrough
          path, and needs raw height data + texture, not a pre-built mesh.
   Both consume the SAME cleaned-up DSM, so "what you download" and
   "what you fly through" are guaranteed to match.
"""
import base64
import io

import numpy as np


def flatten_planar_classes(dsm: np.ndarray, landcover_mask: np.ndarray,
                            class_ids=None, min_pixels: int = 30) -> np.ndarray:
    """
    Per-instance plane-fit snapping: for each connected blob of a
    "planar" land-cover class (buildings, by default -- see
    config.PLANAR_LANDCOVER_CLASSES), fit a tilted plane z = a*x + b*y + c
    to that blob's raw predicted heights via least squares, then replace
    every pixel in the blob with the plane's value at that pixel.

    This directly manufactures flat rooftops / sharp walls -- the thing
    the structure_loss training experiment was trying (and failing) to
    achieve -- because we're not fighting the network's gradients, we're
    imposing planarity where the land-cover mask already tells us it
    should exist. A plane (not a single constant) is used so pitched/
    sloped roofs aren't flattened into something visually wrong.

    Tree canopy is deliberately NOT in the default class list: canopy has
    real internal height variance (individual branches/gaps) that a plane
    fit would misrepresent -- that's a case for the confidence overlay
    (Innovation #2) to flag as "uncertain", not for flattening.

    class_ids: iterable of land-cover class IDs to flatten. Defaults to
        config.PLANAR_LANDCOVER_CLASSES mapped through
        config.LANDCOVER_CLASS_IDS.
    min_pixels: connected components smaller than this are left
        untouched -- a plane fit on a handful of pixels is unstable and
        more likely to be mask noise than a real building.
    """
    from scipy import ndimage
    from app import config

    if class_ids is None:
        class_ids = [config.LANDCOVER_CLASS_IDS[name] for name in config.PLANAR_LANDCOVER_CLASSES]

    if dsm.shape != landcover_mask.shape:
        raise ValueError(
            f"dsm shape {dsm.shape} must match landcover_mask shape {landcover_mask.shape}."
        )

    result = dsm.copy()
    yy, xx = np.mgrid[0:dsm.shape[0], 0:dsm.shape[1]]

    for class_id in class_ids:
        class_mask = (landcover_mask == class_id)
        if not np.any(class_mask):
            continue

        labeled, n_blobs = ndimage.label(class_mask)
        
        # Debug: count and size of connected components
        blob_sizes = []
        for blob_id in range(1, n_blobs + 1):
            blob_mask = labeled == blob_id
            blob_sizes.append(blob_mask.sum())
        
        print(f"[flatten_planar_classes] class_id={class_id}, n_blobs={n_blobs}, total_pixels={class_mask.sum()}")
        if blob_sizes:
            sorted_sizes = sorted(blob_sizes, reverse=True)
            print(f"[flatten_planar_classes] top 3 blob pixel counts: {sorted_sizes[:3]}")
        
        for blob_id in range(1, n_blobs + 1):
            blob_mask = labeled == blob_id
            n_pixels = int(blob_mask.sum())
            if n_pixels < min_pixels:
                continue  # leave small/noisy blobs untouched

            x = xx[blob_mask].astype(np.float64)
            y = yy[blob_mask].astype(np.float64)
            z = dsm[blob_mask].astype(np.float64)

            valid = np.isfinite(z)
            if valid.sum() < min_pixels:
                continue

            A = np.column_stack([x[valid], y[valid], np.ones(valid.sum())])
            coeffs, *_ = np.linalg.lstsq(A, z[valid], rcond=None)
            a, b, c = coeffs

            plane_values = a * x + b * y + c
            result[blob_mask] = plane_values

    return result


def suppress_tree_noise(dsm: np.ndarray, landcover_mask: np.ndarray,
                         tree_class_id: int, feather_px: int = 3,
                         max_nearest_neighbor_distance_px: float = 40.0) -> np.ndarray:
    """
    Removes tree-canopy pixels from the height map and replaces them with
    an inferred ground height, then lightly blurs just the filled region
    so the seam isn't a hard edge.

    Rationale: tree canopy is high-frequency, high-variance, and the depth
    model's per-pixel noise is worst exactly there (individual branches/
    gaps), which is why canopy is deliberately excluded from
    flatten_planar_classes' plane-fit (a plane fit would misrepresent it,
    per that function's docstring). Rather than trying to represent
    canopy height at all, this treats trees as "ignore and infer the
    ground underneath" -- for a demo prioritizing clean terrain/building
    shape over tree realism, that's the right tradeoff.

    FIX: originally used pure nearest-neighbor inpainting for every tree
    pixel, which silently broke for a LARGE contiguous canopy blob -- a
    tree pixel deep in the middle of a big forest region could have its
    "nearest non-tree pixel" be far away near the image edge, itself an
    elevated/noisy point rather than true ground level, so the whole
    canopy inherited an arbitrary distant value instead of a sensible
    baseline (confirmed: a scene that was almost entirely tree canopy
    only dropped from max=1.00 to max=0.92 after this ran -- barely
    touched, because there was no genuinely nearby low ground to pull
    from). Now: any tree pixel farther than
    max_nearest_neighbor_distance_px from real non-tree ground falls
    back to a robust GLOBAL baseline (a low percentile of all non-tree
    heights in the scene) instead of an unreliable distant nearest
    neighbor -- guarantees large canopy blobs settle near true ground
    level regardless of shape/size, while small/isolated tree patches
    near real ground still get the more locally-accurate nearest-neighbor
    value.

    feather_px: radius of a light box blur applied ONLY to the
        (dilated) tree region after inpainting, to soften the seam
        between real ground and inferred ground where they meet.
    """
    from scipy import ndimage

    tree_mask = (landcover_mask == tree_class_id)
    if not np.any(tree_mask):
        return dsm

    non_tree_mask = ~tree_mask
    if not np.any(non_tree_mask):
        return dsm  # entire scene is tree -- nothing to infer ground from at all

    global_baseline = float(np.percentile(dsm[non_tree_mask], 15))

    # Nearest-neighbor fill (good for small/isolated tree patches near real ground)
    distances, indices = ndimage.distance_transform_edt(
        tree_mask, return_distances=True, return_indices=True
    )
    filled = dsm.copy()
    nn_values = dsm[tuple(idx[tree_mask] for idx in indices)]
    filled[tree_mask] = nn_values

    # Any tree pixel too far from real ground gets the global baseline
    # instead of trusting a distant, unreliable nearest neighbor.
    far_from_ground = tree_mask & (distances > max_nearest_neighbor_distance_px)
    filled[far_from_ground] = global_baseline

    print(f"[suppress_tree_noise] global_baseline={global_baseline:.4f}, "
          f"{int(far_from_ground.sum())}/{int(tree_mask.sum())} tree px "
          f"used global baseline (too far from real ground for nearest-neighbor)")

    # Feather only near the old tree/non-tree boundary so we don't blur
    # real building edges elsewhere in the image.
    if feather_px > 0:
        seam_zone = ndimage.binary_dilation(tree_mask, iterations=feather_px)
        ksize = 2 * feather_px + 1
        blurred = ndimage.uniform_filter(filled, size=ksize)
        filled = np.where(seam_zone, blurred, filled)

    return filled


def smooth_dsm(dsm: np.ndarray, rgb_guide: np.ndarray) -> np.ndarray:
    """
    Edge-aware smoothing of the (optionally already plane-flattened) DSM,
    using the original RGB image as the guide so real edges (building
    outlines, ridgelines) are preserved while pixel-level speckle noise
    is removed -- a naive Gaussian blur would smear away exactly the
    edges flatten_planar_classes() just sharpened.

    Reuses the same guided_filter already validated in Stage 1's own
    inference path (utils.image_utils.guided_filter), so smoothing
    behavior is consistent across the pipeline rather than two different
    filters doing conceptually the same job differently.
    """
    from app.utils.image_utils import guided_filter

    return guided_filter(rgb_guide, dsm, radius=4, eps=1e-3)


def clean_dsm_for_mesh(dsm: np.ndarray, rgb_guide: np.ndarray,
                        landcover_mask: np.ndarray = None,
                        suppress_trees: bool = True) -> np.ndarray:
    """
    Convenience wrapper chaining the full Stage 3 cleanup:
    plane-fit flattening -> tree-noise suppression (both only if a
    land-cover mask is available) -> edge-aware smoothing. This is what
    pipeline.py / the API route should call before handing the DSM to
    generate_mesh() or package_result_for_frontend().

    Order matters: flatten buildings first (uses raw heights for the
    plane fit), THEN suppress trees (inpaints from whatever's
    surrounding them, including now-flattened buildings), THEN the
    final edge-aware smoothing pass over everything.
    """
    from app import config

    print(f"[stage3_mesh_prep] clean_dsm_for_mesh called - dsm.shape={dsm.shape}, dsm.min={dsm.min():.4f}, dsm.max={dsm.max():.4f}, dsm.std={dsm.std():.4f}")
    print(f"[stage3_mesh_prep] config.LANDCOVER_CLASS_IDS={config.LANDCOVER_CLASS_IDS}")
    print(f"[stage3_mesh_prep] config.SUPPRESS_TREE_HEIGHT={config.SUPPRESS_TREE_HEIGHT}")
    print(f"[stage3_mesh_prep] config.TREE_LANDCOVER_CLASS={config.TREE_LANDCOVER_CLASS}")
    print(f"[stage3_mesh_prep] landcover_mask is {'None' if landcover_mask is None else f'present, shape={landcover_mask.shape}'}")
    
    cleaned = dsm
    if landcover_mask is not None:
        print(f"[stage3_mesh_prep] BEFORE flatten_planar_classes: dsm.min={cleaned.min():.4f}, dsm.max={cleaned.max():.4f}, dsm.std={cleaned.std():.4f}")
        cleaned = flatten_planar_classes(cleaned, landcover_mask)
        print(f"[stage3_mesh_prep] AFTER flatten_planar_classes: dsm.min={cleaned.min():.4f}, dsm.max={cleaned.max():.4f}, dsm.std={cleaned.std():.4f}")
        if suppress_trees and config.SUPPRESS_TREE_HEIGHT:
            tree_class_id = config.LANDCOVER_CLASS_IDS.get(config.TREE_LANDCOVER_CLASS)
            print(f"[stage3_mesh_prep] suppress_tree_noise: tree_class_id={tree_class_id}, landcover_mask unique values={np.unique(landcover_mask)}")
            if tree_class_id is not None:
                print(f"[stage3_mesh_prep] BEFORE suppress_tree_noise: dsm.min={cleaned.min():.4f}, dsm.max={cleaned.max():.4f}, dsm.std={cleaned.std():.4f}")
                cleaned = suppress_tree_noise(cleaned, landcover_mask, tree_class_id)
                print(f"[stage3_mesh_prep] AFTER suppress_tree_noise: dsm.min={cleaned.min():.4f}, dsm.max={cleaned.max():.4f}, dsm.std={cleaned.std():.4f}")
    smoothed = smooth_dsm(cleaned, rgb_guide)

    # BUG FIX: smooth_dsm's guided filter (radius=4) was re-blurring the
    # sharp plane-fit edges flatten_planar_classes() just created -- the
    # docstring above even says "edges flatten_planar_classes() just
    # sharpened" but the code never actually protected them from this
    # pass, so every flattened building got melted right back into a
    # sloped blob. Composite: keep the exact flattened plane value on
    # building pixels (they don't need denoising, they're already a
    # deliberate flat plane, not raw model output), take the smoothed
    # value everywhere else (trees/ground/roads genuinely need the
    # noise reduction).
    if landcover_mask is not None:
        planar_ids = [config.LANDCOVER_CLASS_IDS[name] for name in config.PLANAR_LANDCOVER_CLASSES]
        planar_pixel_mask = np.isin(landcover_mask, planar_ids)
        result = np.where(planar_pixel_mask, cleaned, smoothed)
        print(f"[stage3_mesh_prep] Protected {int(planar_pixel_mask.sum())} planar (building) "
              f"pixels from post-flatten smoothing")
    else:
        result = smoothed

    print(f"[stage3_mesh_prep] AFTER smooth_dsm (with planar protection): "
          f"dsm.min={result.min():.4f}, dsm.max={result.max():.4f}, dsm.std={result.std():.4f}")

    # Global outlier clamp -- catches raw depth hallucination (a tall
    # dome/ridge in ground/vegetation terrain that flatten/suppress don't
    # touch, since they only target building/tree pixels specifically).
    # Only clips NON-building pixels, and percentile bounds are computed
    # from non-building pixels too, so a legitimate flattened building
    # roof at the high end of the range can't get clipped by its own fix.
    if landcover_mask is not None:
        planar_ids = [config.LANDCOVER_CLASS_IDS[name] for name in config.PLANAR_LANDCOVER_CLASSES]
        planar_pixel_mask = np.isin(landcover_mask, planar_ids)

        # FIX: percentile bounds used to be computed from ALL non-building
        # pixels, including tree canopy -- if a scene is mostly tree cover
        # and that canopy is hallucinating elevated height (confirmed: the
        # nearest-neighbor tree fix barely engaged, 0/24489 px in one real
        # run, meaning neighboring non-tree pixels are ALSO elevated), the
        # 97th percentile is computed from a mostly-contaminated
        # population and doesn't clip anything meaningful. Reference
        # bounds now come from ONLY ground+road pixels specifically --
        # the flattest, most reliable classes, least likely to hallucinate
        # -- so the clamp has a trustworthy baseline regardless of how
        # much of the image is tree-covered.
        reference_ids = [
            config.LANDCOVER_CLASS_IDS[name]
            for name in ("ground", "road")
            if name in config.LANDCOVER_CLASS_IDS
        ]
        reference_mask = np.isin(landcover_mask, reference_ids)
        min_reference_pixels = 200
        if reference_mask.sum() >= min_reference_pixels:
            reference_values = result[reference_mask]
            reference_source = "ground+road"
        else:
            reference_values = result[~planar_pixel_mask]
            reference_source = "all non-building (ground+road too sparse in this scene)"

        if reference_values.size > 0:
            lo_pct, hi_pct = config.DSM_OUTLIER_CLAMP_PERCENTILES
            lo, hi = np.percentile(reference_values, [lo_pct, hi_pct])
            before_max = result.max()
            clamped_non_planar = np.clip(result, lo, hi)
            result = np.where(planar_pixel_mask, result, clamped_non_planar)
            print(f"[stage3_mesh_prep] Outlier clamp (reference: {reference_source}, "
                  f"n={reference_values.size}): [{lo:.4f}, {hi:.4f}] "
                  f"(was max={before_max:.4f}, now max={result.max():.4f})")

    return result


def _downsample_to_max_resolution(array: np.ndarray, max_resolution: int) -> np.ndarray:
    """Downsamples a 2D or 3D array so its longer side is <= max_resolution."""
    from PIL import Image

    h, w = array.shape[0], array.shape[1]
    scale = min(1.0, max_resolution / max(h, w))
    if scale >= 1.0:
        return array

    new_h, new_w = max(1, int(h * scale)), max(1, int(w * scale))
    if array.ndim == 2:
        img = Image.fromarray(array.astype(np.float32), mode="F")
        return np.array(img.resize((new_w, new_h), Image.BILINEAR))
    else:
        img = Image.fromarray(array.astype(np.uint8))
        return np.array(img.resize((new_w, new_h), Image.BILINEAR))


def generate_mesh(dsm: np.ndarray, rgb_image: np.ndarray,
                   max_resolution: int = None, vertical_exaggeration: float = None):
    """
    Builds an actual triangulated 3D mesh from a cleaned height map:
    one vertex per pixel (after downsampling to max_resolution for a
    sane triangle count), two triangles per pixel quad, UVs mapping
    straight back to rgb_image for texturing.

    Downsampling here is a MESH-DENSITY decision (triangle count),
    separate from the DSM's own resolution -- a 512x512 DSM meshed
    1:1 would be 500k+ triangles, more than needed for a smooth
    flythrough and slow to export/load. config.MESH_MAX_RESOLUTION
    is the default cap.

    Returns (vertices, faces, uvs):
        vertices: (N, 3) float32 array of (x, y, z) in mesh-local units
                  (x, y in pixel-grid units, z in meters from the DSM)
        faces: (M, 3) int32 array of triangle vertex indices
        uvs: (N, 2) float32 array of (u, v) texture coordinates in [0, 1]
    """
    from app import config

    if max_resolution is None:
        max_resolution = config.MESH_MAX_RESOLUTION
    if vertical_exaggeration is None:
        vertical_exaggeration = config.MESH_VERTICAL_EXAGGERATION

    height_ds = _downsample_to_max_resolution(dsm, max_resolution)
    h, w = height_ds.shape

    yy, xx = np.mgrid[0:h, 0:w]
    zz = np.nan_to_num(height_ds, nan=0.0).astype(np.float32) * vertical_exaggeration

    vertices = np.stack([
        xx.astype(np.float32),
        yy.astype(np.float32),
        zz,
    ], axis=-1).reshape(-1, 3)

    uvs = np.stack([
        xx.astype(np.float32) / max(w - 1, 1),
        1.0 - yy.astype(np.float32) / max(h - 1, 1),  # flip V so texture isn't upside-down
    ], axis=-1).reshape(-1, 2)

    faces = []
    for row in range(h - 1):
        row_start = row * w
        next_row_start = (row + 1) * w
        for col in range(w - 1):
            v00 = row_start + col
            v01 = row_start + col + 1
            v10 = next_row_start + col
            v11 = next_row_start + col + 1
            faces.append([v00, v10, v01])
            faces.append([v01, v10, v11])
    faces = np.array(faces, dtype=np.int32)

    return vertices, faces, uvs


def export_mesh_glb(dsm: np.ndarray, rgb_image: np.ndarray, out_path: str,
                     max_resolution: int = None, vertical_exaggeration: float = None) -> str:
    """
    Exports a standalone, downloadable .glb (binary glTF) file -- a real
    3D asset viewable in any glTF viewer (not just our own frontend),
    which is what satisfies "standalone deployability" independent of
    the live browser viewer. Uses trimesh (already in requirements.txt)
    for glTF packaging rather than hand-writing glTF JSON.
    """
    import trimesh

    vertices, faces, uvs = generate_mesh(dsm, rgb_image, max_resolution, vertical_exaggeration)

    # trimesh expects the texture as a PIL Image for a SimpleMaterial/TextureVisuals
    from PIL import Image as PILImage
    texture_img = PILImage.fromarray(rgb_image.astype(np.uint8))

    visual = trimesh.visual.TextureVisuals(uv=uvs, image=texture_img)
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces, visual=visual, process=False)
    mesh.export(out_path, file_type="glb")
    return out_path


def _encode_png_base64(array: np.ndarray) -> str:
    """Encodes a numpy array as a base64 PNG data string for JSON transport."""
    from PIL import Image

    img = Image.fromarray(array)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def package_result_for_frontend(dsm: np.ndarray, confidence_map: np.ndarray,
                                 rgb_image: np.ndarray, metadata: dict) -> dict:
    """
    Packages the cleaned DSM + confidence map + RGB texture into a
    lightweight, JSON-serializable payload for the /result API response.
    The Three.js frontend builds its own mesh client-side from this data.

    IMPORTANT: downsamples dsm/confidence/rgb to config.MESH_MAX_RESOLUTION
    before encoding -- generate_mesh()/export_mesh_glb() already did this
    for the downloadable .glb, but this function used to send the FULL,
    un-downsampled resolution to the live browser view. On a fixed-size
    display plane (TERRAIN_SIZE in the frontend), that meant per-pixel
    noise in the raw depth output produced near-vertical spikes -- every
    pixel became its own mesh vertex on a plane far too small for that
    vertex density, so noise that would be invisible at a sane resolution
    read as dramatic fake "mountains." Downsampling here also acts as
    extra noise averaging on top of smooth_dsm()'s guided filter, which
    matters most for the relative-only (no SRTM/no calibration) fallback
    path, where the raw Stage 1 output is noisiest.

    Height data is shipped as 16-bit PNG (not 8-bit) to preserve enough
    vertical precision for tall scenes -- an 8-bit heightmap would band
    visibly on a 40m-tall building.

    Returns a dict of JSON-safe values:
        heightmap_png_b64: base64 16-bit grayscale PNG, values scaled to
            [0, 65535] linearly across [height_min, height_max] (both
            included in the response so the frontend can invert the scale)
        confidence_png_b64: base64 8-bit grayscale PNG (or None if no
            uncertainty pass was run), 0=low confidence, 255=high
        texture_png_b64: base64 RGB PNG of the original image, for UV texturing
        height_min / height_max: float, for decoding heightmap_png_b64
        height_units: "meters" if this DSM went through real SRTM
            calibration, "relative" otherwise -- the frontend must NOT
            label relative values with "m", they're not meters
        metadata: passed through as given (GSD info, calibration method, etc.)
    """
    from app import config

    dsm_ds = _downsample_to_max_resolution(dsm, config.MESH_MAX_RESOLUTION)
    rgb_ds = _downsample_to_max_resolution(rgb_image, config.MESH_MAX_RESOLUTION)
    confidence_ds = (
        _downsample_to_max_resolution(confidence_map, config.MESH_MAX_RESOLUTION)
        if confidence_map is not None else None
    )

    valid = np.isfinite(dsm_ds)
    height_min = float(np.min(dsm_ds[valid])) if np.any(valid) else 0.0
    height_max = float(np.max(dsm_ds[valid])) if np.any(valid) else 1.0
    if height_max <= height_min:
        height_max = height_min + 1.0

    dsm_filled = np.nan_to_num(dsm_ds, nan=height_min)
    normalized = np.clip((dsm_filled - height_min) / (height_max - height_min), 0, 1)
    heightmap_16bit = (normalized * 65535).astype(np.uint16)

    confidence_png_b64 = None
    if confidence_ds is not None:
        confidence_8bit = np.clip(confidence_ds * 255, 0, 255).astype(np.uint8)
        confidence_png_b64 = _encode_png_base64(confidence_8bit)

    calibration_method = metadata.get("calibration_method", "none_relative_only")
    height_units = "meters" if calibration_method != "none_relative_only" else "relative"

    return {
        "heightmap_png_b64": _encode_png_base64(heightmap_16bit),
        "confidence_png_b64": confidence_png_b64,
        "texture_png_b64": _encode_png_base64(rgb_ds.astype(np.uint8)),
        "height_min": height_min,
        "height_max": height_max,
        "height_units": height_units,
        "metadata": metadata,
    }
