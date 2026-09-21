"""
STAGE 1 -- Elevation Extraction.

Runs the fine-tuned Depth Anything V2 Small backbone on an input RGB image
and returns a RELATIVE height map (nDSM-like -- height above local
ground, arbitrary scale). This is the ONLY job of this file: RGB in,
relative height map out. Scale calibration is Stage 2's job, not this
file's.

Model: Depth Anything V2 Small (transformers AutoModelForDepthEstimation),
fine-tuned on GAMUS with last 12 backbone blocks + head/neck unfrozen,
scale-invariant + multi-scale gradient + building/tree class-weighted loss.
Checkpoint: depth_anything_v2_gamus_v4.pth (see training/ for how it was produced).
This is the current best-validated checkpoint: v5's added structure_loss term
(meant to flatten building rooftops / sharpen edges) regressed MAE across
every land-cover class once re-evaluated on a fixed validation split, so v4
was kept. Rooftop flattening is instead handled downstream, in Stage 3's
land-cover-guided post-processing (see stage3_mesh_prep.flatten_planar_classes),
which fixes shape without touching the depth model's numeric accuracy.

IMPORTANT -- confirmed via generalization testing on real Sentinel-2 imagery:
this model is sensitive to ground-sample-distance (GSD). GAMUS training tiles
are neighborhood-scale (individual buildings resolved across many pixels,
~0.33m/pixel -- cited from a GAMUS comparison table, arXiv 2507.08741, not
GAMUS's own paper directly). Feeding a wide district/city-scale image
produces nonsense (the model reverts to a natural-image "distant vista"
prior). ALWAYS run normalize_gsd() before run_inference() on any real-world
input.

NOTE: load_depth_model() and run_inference() require network access to
Hugging Face to fetch the base architecture -- this logic is ported directly
from the validated Colab notebook (stage1_final.ipynb / stage1_v3.ipynb)
where it was actually run and confirmed working, but has not been
re-executed in this exact file. Run the test suite / a smoke test in your
own environment (which has HF access) before relying on it in production.
"""
import numpy as np
from PIL import Image

MODEL_NAME = "depth-anything/Depth-Anything-V2-Small-hf"
MODEL_INPUT_SIZE = 512  # matches IMG_SIZE used throughout training

# Cited: GAMUS dataset spatial resolution, per a comparison table in
# arXiv 2507.08741 (HieraRS) -- NOT stated explicitly in GAMUS's own paper,
# so treat as a well-sourced estimate rather than an authoritative constant.
GAMUS_IMPLIED_GSD_M = 0.33


def load_depth_model(checkpoint_path: str, device: str = None):
    """
    Loads the Depth Anything V2 Small architecture and applies the
    fine-tuned checkpoint's weights on top of it.

    Ported from the notebook's confirmed-working loading pattern:
        model = AutoModelForDepthEstimation.from_pretrained(MODEL_NAME)
        model.load_state_dict(torch.load(checkpoint_path))
    """
    import torch
    from transformers import AutoModelForDepthEstimation

    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    model = AutoModelForDepthEstimation.from_pretrained(MODEL_NAME)
    state_dict = torch.load(checkpoint_path, map_location=device)
    model.load_state_dict(state_dict)
    model.to(device)
    model.eval()
    return model


def normalize_gsd(image: np.ndarray, source_gsd_m: float = None,
                   target_gsd_m: float = GAMUS_IMPLIED_GSD_M,
                   model_input_size: int = MODEL_INPUT_SIZE):
    """
    REQUIRED preprocessing step before run_inference -- center-crops the
    input so the cropped region, once resized to model_input_size, has each
    pixel representing approximately target_gsd_m meters of ground --
    matching the scale the backbone was trained on.

    source_gsd_m: meters/pixel of the INPUT image.
      - For GeoTIFF: comes from the file's own geotransform
        (see utils/geotiff_utils.read_geotiff_metadata -> "resolution_m").
      - For PNG/JPG with no metadata: pass None. We then assume the image
        already roughly matches training scale rather than guessing wildly --
        this is a known, documented limitation (see docstring above), not
        a silent guess dressed up as a real value.

    Returns (normalized_image, info_dict) where info_dict records what
    crop/assumption was actually applied, for logging/debugging/API response.
    """
    h, w = image.shape[0], image.shape[1]

    if source_gsd_m is None:
        crop_side_px = model_input_size
        mode = "assumed_no_metadata"
    else:
        crop_side_px = target_gsd_m * model_input_size / source_gsd_m
        if crop_side_px > min(w, h):
            crop_side_px = min(w, h)
            mode = "clamped_to_full_image"
        else:
            crop_side_px = max(1, round(crop_side_px))
            mode = "computed"

    # Center crop to crop_side_px x crop_side_px
    top = max(0, (h - crop_side_px) // 2)
    left = max(0, (w - crop_side_px) // 2)
    cropped = image[top:top + crop_side_px, left:left + crop_side_px]

    # Resize the crop to the model's expected input size. LANCZOS (not
    # BILINEAR) -- sharper for both directions, and specifically matters
    # when crop_side_px < model_input_size (a wide/zoomed-out source like
    # Sentinel-2 means the GSD-matching crop is small, so this step is
    # UPSCALING, not just resizing -- BILINEAR made that blur worse).
    is_upscaling = crop_side_px < model_input_size
    pil_img = Image.fromarray(cropped).resize((model_input_size, model_input_size), Image.LANCZOS)

    if is_upscaling:
        # Mild unsharp mask to recover perceived edge crispness after
        # upscaling. This does NOT invent real detail (no super-resolution
        # model, no training) -- it's a standard sharpening pass, applied
        # only when upscaling since it would just add ringing artifacts on
        # an already-correctly-sized or downsampled crop.
        from PIL import ImageFilter
        pil_img = pil_img.filter(ImageFilter.UnsharpMask(radius=1.5, percent=60, threshold=2))

    normalized = np.array(pil_img)

    info = {
        "mode": mode,
        "source_gsd_m": source_gsd_m,
        "target_gsd_m": target_gsd_m,
        "crop_side_px": int(crop_side_px),
        "original_shape": (h, w),
        "upscaled": is_upscaling,
    }
    return normalized, info


def run_inference(image: np.ndarray, model, device: str = None) -> np.ndarray:
    """
    Runs the forward pass and returns a relative height map at the SAME
    shape as the input `image`. Assumes `image` has already been through
    normalize_gsd() and is model_input_size x model_input_size.

    Ported from the notebook's confirmed-working inference pattern
    (stage1_v4_fixed.ipynb, section 6/8): normalize to [0,1], NCHW tensor,
    forward pass, bicubic-resize the raw (lower-res) predicted_depth back
    up to the input's own resolution, and apply edge-preserving guided filter
    with RGB as guide to eliminate blurry upsampling blobs.
    """
    import torch
    from app.utils.image_utils import guided_filter

    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    arr = image.astype(np.float32) / 255.0
    tensor = torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0).to(device)

    with torch.no_grad():
        outputs = model(pixel_values=tensor)
        pred = outputs.predicted_depth.unsqueeze(1)

    pred_resized = torch.nn.functional.interpolate(
        pred, size=(image.shape[0], image.shape[1]), mode="bicubic", align_corners=False
    )
    raw_depth = pred_resized[0, 0].cpu().numpy()
    return guided_filter(image, raw_depth)


# TTA perturbation set for run_inference_with_uncertainty. Each entry is
# (name, forward_fn, invert_fn):
#   forward_fn(arr)   -- applies the perturbation to the [0,1] HWC float array
#                         BEFORE it's turned into a tensor and fed to the model
#   invert_fn(pred)    -- undoes any SPATIAL change on the resulting (H, W)
#                         prediction so all passes line up pixel-for-pixel
#                         before variance is computed. Photometric-only
#                         perturbations (brightness/gamma) use identity here.
def _identity(x):
    return x


def _hflip(x):
    return x[:, ::-1, ...] if x.ndim == 3 else x[:, ::-1]


def _vflip(x):
    return x[::-1, :, ...] if x.ndim == 3 else x[::-1, :]


def _hvflip(x):
    return _hflip(_vflip(x))


def _brighten(factor):
    return lambda arr: np.clip(arr * factor, 0.0, 1.0)


def _gamma(g):
    return lambda arr: np.clip(arr, 1e-6, 1.0) ** g


_TTA_TRANSFORMS = [
    ("identity", _identity, _identity),
    ("hflip", _hflip, _hflip),
    ("vflip", _vflip, _vflip),
    ("hvflip", _hvflip, _hvflip),
    ("darker", _brighten(0.85), _identity),
    ("brighter", _brighten(1.15), _identity),
    ("gamma_down", _gamma(0.85), _identity),
    ("gamma_up", _gamma(1.15), _identity),
]


def run_inference_with_uncertainty(image: np.ndarray, model, n_passes: int = 8, device: str = None):
    """
    Innovation #2 -- test-time-augmentation (TTA) uncertainty estimation with guided filtering.
    """
    import torch
    from app.utils.image_utils import guided_filter

    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    n_passes = max(2, min(n_passes, len(_TTA_TRANSFORMS)))
    transforms = _TTA_TRANSFORMS[:n_passes]

    base_arr = image.astype(np.float32) / 255.0
    predictions = []
    with torch.no_grad():
        for _name, forward_fn, invert_fn in transforms:
            arr = forward_fn(base_arr)
            tensor = torch.from_numpy(np.ascontiguousarray(arr)).permute(2, 0, 1).unsqueeze(0).to(device)
            outputs = model(pixel_values=tensor)
            pred = outputs.predicted_depth.unsqueeze(1)
            pred_resized = torch.nn.functional.interpolate(
                pred, size=(image.shape[0], image.shape[1]), mode="bicubic", align_corners=False
            )
            pred_np = pred_resized[0, 0].cpu().numpy()
            pred_np = invert_fn(pred_np)  # undo flip so it lines up with the others
            guided_pred = guided_filter(image, pred_np)
            predictions.append(np.ascontiguousarray(guided_pred))

    stacked = np.stack(predictions, axis=0)  # (n_passes, H, W)
    mean_height_map = stacked.mean(axis=0)
    variance_map = stacked.var(axis=0)

    # Normalize variance to a [0,1] confidence score: low variance -> high confidence
    v_min, v_max = variance_map.min(), variance_map.max()
    if v_max - v_min < 1e-8:
        confidence_map = np.full_like(variance_map, 0.5)
    else:
        normalized_variance = (variance_map - v_min) / (v_max - v_min)
        confidence_map = 1.0 - normalized_variance

    return mean_height_map, confidence_map

