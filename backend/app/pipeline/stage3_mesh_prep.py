"""
STAGE 3 (backend side) -- prep only.

The actual mesh generation + rendering happens client-side in the
Three.js frontend (see frontend/src/components/viewport/). This file's
only job is to package the calibrated DSM + confidence map + RGB image
into a lightweight, frontend-friendly format before sending over the
API (e.g. downsampled heightmap PNG + full-res texture + JSON metadata).
"""
import numpy as np


def package_result_for_frontend(dsm: np.ndarray, confidence_map: np.ndarray,
                                 rgb_image: np.ndarray, metadata: dict):
    """TODO: encode heightmap + confidence map as PNGs, bundle with metadata JSON."""
    raise NotImplementedError
