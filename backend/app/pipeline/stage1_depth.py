"""
STAGE 1 -- Elevation Extraction.

Runs the fine-tuned Depth Anything V2 backbone on an input RGB image
and returns a RELATIVE height map (nDSM-like -- height above local
ground, arbitrary scale). This is the ONLY job of this file: RGB in,
relative height map out. Scale calibration is Stage 2's job, not this
file's.
"""
import numpy as np


def load_depth_model(checkpoint_path: str):
    """TODO: load fine-tuned Depth Anything V2 model + weights."""
    raise NotImplementedError


def run_inference(image: np.ndarray, model) -> np.ndarray:
    """
    TODO: run forward pass, return relative height map same H x W as image.
    """
    raise NotImplementedError


def run_inference_with_uncertainty(image: np.ndarray, model, n_passes: int = 8):
    """
    Innovation #2 -- MC-dropout uncertainty estimation.
    TODO: run `n_passes` forward passes with dropout enabled at inference,
    return (mean_height_map, confidence_map) where confidence is derived
    from the variance across passes (low variance = high confidence).
    """
    raise NotImplementedError
