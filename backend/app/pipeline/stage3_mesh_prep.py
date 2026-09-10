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
                        landcover_mask: np.ndarray = None) -> np.ndarray:
    """
    Convenience wrapper chaining the full Stage 3 cleanup:
    plane-fit flattening (if a land-cover mask is available) -> edge-aware
    smoothing. This is what pipeline.py / the API route should call before
    handing the DSM to generate_mesh() or package_result_for_frontend().
    """
    cleaned = dsm
    if landcover_mask is not None:
        cleaned = flatten_planar_classes(cleaned, landcover_mask)
    return smooth_dsm(cleaned, rgb_guide)


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
    The Three.js frontend builds its own mesh client-side from this data
    (frontend/src/components/viewport/meshBuilder.js) via GPU vertex
    displacement, which is why we ship raw height data here rather than
    a pre-built mesh -- the live viewer needs the full-resolution
    heightmap for smooth navigation, not a pre-triangulated asset.

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
        metadata: passed through as given (GSD info, calibration method, etc.)
    """
    valid = np.isfinite(dsm)
    height_min = float(np.min(dsm[valid])) if np.any(valid) else 0.0
    height_max = float(np.max(dsm[valid])) if np.any(valid) else 1.0
    if height_max <= height_min:
        height_max = height_min + 1.0

    dsm_filled = np.nan_to_num(dsm, nan=height_min)
    normalized = np.clip((dsm_filled - height_min) / (height_max - height_min), 0, 1)
    heightmap_16bit = (normalized * 65535).astype(np.uint16)

    confidence_png_b64 = None
    if confidence_map is not None:
        confidence_8bit = np.clip(confidence_map * 255, 0, 255).astype(np.uint8)
        confidence_png_b64 = _encode_png_base64(confidence_8bit)

    return {
        "heightmap_png_b64": _encode_png_base64(heightmap_16bit),
        "confidence_png_b64": confidence_png_b64,
        "texture_png_b64": _encode_png_base64(rgb_image.astype(np.uint8)),
        "height_min": height_min,
        "height_max": height_max,
        "metadata": metadata,
    }
