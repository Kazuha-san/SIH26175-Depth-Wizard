"""
STAGE 2 -- Scale Calibration. [Innovation #1 lives here]

Converts Stage 1's relative height map into either:
  - an absolute metric DSM (georeferenced input, anchored to SRTM)
  - a normalized rDSM (non-georeferenced input, no absolute anchor)

INNOVATION: instead of one global affine fit (H = a*h_rel + b) across
the whole scene, we fit calibration PER LAND-COVER CLASS using GAMUS-style
semantic masks (ground/low-vegetation/building/water/road/tree), since the
depth model's bias is not uniform across terrain types (confirmed during
Stage 1 evaluation -- e.g. building and tree classes have very different
error characteristics than flat ground/road).

Absolute DSM reconstruction note (from Stage 1 architecture): the depth
backbone was trained to predict RELATIVE height (nDSM-like -- height above
LOCAL ground, not sea-level/global elevation). So absolute DSM here means:

    absolute_DSM ≈ calibrated_relative_height + local_ground_elevation

where local_ground_elevation comes from SRTM itself (SRTM approximates the
local ground/surface baseline at its own coarse 30m resolution). The
per-class calibration fixes the SCALE of the relative height signal;
adding the (resampled-to-match) SRTM baseline back in restores the
absolute elevation offset that nDSM-style training strips out.
"""
import numpy as np


def global_affine_fit(relative_height: np.ndarray, srtm_reference: np.ndarray,
                       valid_mask: np.ndarray = None):
    """
    Baseline calibration: single (a, b) least-squares fit of
    relative_height -> srtm_reference, i.e. srtm ≈ a * relative_height + b.
    Kept as a fallback / comparison baseline against the per-class
    innovation below -- useful when no land-cover mask is available.

    Returns (a, b, calibrated_height) where calibrated_height = a*relative_height + b.
    """
    if relative_height.shape != srtm_reference.shape:
        raise ValueError(
            f"relative_height {relative_height.shape} and srtm_reference "
            f"{srtm_reference.shape} must be the same shape -- resample SRTM "
            f"to match first (see srtm_utils.resample_to_match)."
        )

    if valid_mask is None:
        valid_mask = np.isfinite(relative_height) & np.isfinite(srtm_reference)

    x = relative_height[valid_mask].ravel()
    y = srtm_reference[valid_mask].ravel()

    if x.size < 2:
        raise ValueError("Not enough valid pixels to fit a calibration (need >= 2).")

    # Least squares fit: y = a*x + b  ->  A @ [a, b] = y
    A = np.vstack([x, np.ones_like(x)]).T
    (a, b), *_ = np.linalg.lstsq(A, y, rcond=None)

    calibrated_height = a * relative_height + b
    return float(a), float(b), calibrated_height


def per_class_calibration(relative_height: np.ndarray, srtm_reference: np.ndarray,
                           landcover_mask: np.ndarray, class_ids=None,
                           min_pixels_per_class: int = 30):
    """
    INNOVATION #1: fit a separate (a, b) per land-cover class, using
    `landcover_mask` to segment the scene before fitting each class's
    calibration against the SRTM reference. Stitches back into one
    absolute DSM.

    If a class has too few valid pixels to fit reliably (< min_pixels_per_class),
    falls back to the global affine fit for that class's pixels instead of a
    degenerate/unstable per-class fit -- this matters in practice since not
    every tile contains every class (e.g. no water in an inland scene).

    Returns:
        calibrated_height: np.ndarray, same shape as input
        per_class_params: dict[class_id] -> {"a": float, "b": float, "n_pixels": int, "fallback": bool}
    """
    if relative_height.shape != srtm_reference.shape or relative_height.shape != landcover_mask.shape:
        raise ValueError("relative_height, srtm_reference, and landcover_mask must all be the same shape.")

    valid = np.isfinite(relative_height) & np.isfinite(srtm_reference)

    if class_ids is None:
        class_ids = [c for c in np.unique(landcover_mask) if np.any((landcover_mask == c) & valid)]

    # Global fallback fit first, in case any class needs it
    global_a, global_b, _ = global_affine_fit(relative_height, srtm_reference, valid_mask=valid)

    calibrated_height = np.full_like(relative_height, np.nan, dtype=np.float64)
    per_class_params = {}

    for class_id in class_ids:
        class_mask = (landcover_mask == class_id) & valid
        n_pixels = int(class_mask.sum())

        if n_pixels < min_pixels_per_class:
            a, b, fallback = global_a, global_b, True
        else:
            x = relative_height[class_mask].ravel()
            y = srtm_reference[class_mask].ravel()
            A = np.vstack([x, np.ones_like(x)]).T
            (a, b), *_ = np.linalg.lstsq(A, y, rcond=None)
            fallback = False

        calibrated_height[class_mask] = a * relative_height[class_mask] + b
        per_class_params[int(class_id)] = {"a": float(a), "b": float(b), "n_pixels": n_pixels, "fallback": fallback}

    # Any pixels not covered by a known class (e.g. unlabeled/0, or invalid) get the global fit
    uncovered = valid & np.isnan(calibrated_height)
    if np.any(uncovered):
        calibrated_height[uncovered] = global_a * relative_height[uncovered] + global_b

    return calibrated_height, per_class_params


def normalize_for_visualization(relative_height: np.ndarray, low_percentile: float = 1.0,
                                 high_percentile: float = 99.0):
    """
    Non-georeferenced path: no SRTM anchor available, so just normalize
    the relative height map (percentile clipping + min-max) for a
    visually sensible rDSM. Percentile clipping (not raw min/max) avoids
    a single noisy outlier pixel from crushing the whole visible range.
    """
    valid = np.isfinite(relative_height)
    lo = np.percentile(relative_height[valid], low_percentile)
    hi = np.percentile(relative_height[valid], high_percentile)
    if hi <= lo:
        # degenerate case: flat input, avoid divide-by-zero
        return np.zeros_like(relative_height)
    clipped = np.clip(relative_height, lo, hi)
    return (clipped - lo) / (hi - lo)
