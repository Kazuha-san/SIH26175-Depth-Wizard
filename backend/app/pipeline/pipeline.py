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
