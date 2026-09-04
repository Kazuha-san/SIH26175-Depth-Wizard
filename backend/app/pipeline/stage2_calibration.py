"""
STAGE 2 -- Scale Calibration. [Innovation #1 lives here]

Converts Stage 1's relative height map into either:
  - an absolute metric DSM (georeferenced input, anchored to SRTM)
  - a normalized rDSM (non-georeferenced input, no absolute anchor)

INNOVATION: instead of one global affine fit (H = a*h_rel + b) across
the whole scene, we fit calibration PER LAND-COVER CLASS using GAMUS's
semantic masks (ground/building/vegetation/water/road/tree), since the
depth model's bias is not uniform across terrain types.
"""
import numpy as np


def fetch_srtm_tile(bounds, resolution_m: int = 30):
    """TODO: fetch/crop SRTM 30m tile covering the image's geographic bounds."""
    raise NotImplementedError


def global_affine_fit(relative_height: np.ndarray, srtm_reference: np.ndarray):
    """
    Baseline calibration: single (a, b) least-squares fit of
    relative_height -> srtm_reference. Kept as a fallback / comparison
    baseline against the per-class innovation below.
    """
    raise NotImplementedError


def per_class_calibration(relative_height: np.ndarray, srtm_reference: np.ndarray,
                           landcover_mask: np.ndarray):
    """
    INNOVATION #1: fit a separate (a, b) per land-cover class, using
    `landcover_mask` to segment the scene before fitting each class's
    calibration against the SRTM reference. Stitches back into one
    absolute DSM.
    TODO: implement per-class robust regression (scipy.optimize / sklearn).
    """
    raise NotImplementedError


def normalize_for_visualization(relative_height: np.ndarray):
    """
    Non-georeferenced path: no SRTM anchor available, so just normalize
    the relative height map (e.g. percentile clipping + min-max) for a
    visually sensible rDSM.
    """
    raise NotImplementedError
