"""
Tests for normalize_gsd (pure numpy/PIL, no torch/model needed -- runs
anywhere). run_inference and run_inference_with_uncertainty need a real
model + torch and are NOT covered by an automated test here -- verify
those manually against the real checkpoint in an environment with GPU/HF
access (e.g. re-run the relevant cells in stage1_v3.ipynb) before trusting
them in production.
"""
import numpy as np
from app.pipeline.stage1_depth import normalize_gsd, MODEL_INPUT_SIZE


def test_normalize_gsd_coarse_source():
    """Sentinel-2-like coarse source should compute a small crop then upscale."""
    fake_wide_image = np.random.randint(0, 255, (5586, 5586, 3), dtype=np.uint8)
    normalized, info = normalize_gsd(fake_wide_image, source_gsd_m=10.0)
    assert normalized.shape == (MODEL_INPUT_SIZE, MODEL_INPUT_SIZE, 3)
    assert info["mode"] == "computed"
    assert info["crop_side_px"] < MODEL_INPUT_SIZE  # coarse source -> small crop, matches empirical finding


def test_normalize_gsd_matching_resolution():
    """Source already at GAMUS's implied resolution needs no effective crop."""
    fake_image = np.random.randint(0, 255, (1024, 1024, 3), dtype=np.uint8)
    normalized, info = normalize_gsd(fake_image, source_gsd_m=0.33)
    assert info["mode"] == "computed"
    assert info["crop_side_px"] == MODEL_INPUT_SIZE


def test_normalize_gsd_no_metadata():
    """PNG/JPG with no GSD info should be flagged, not silently guessed."""
    fake_png = np.random.randint(0, 255, (800, 600, 3), dtype=np.uint8)
    normalized, info = normalize_gsd(fake_png, source_gsd_m=None)
    assert normalized.shape == (MODEL_INPUT_SIZE, MODEL_INPUT_SIZE, 3)
    assert info["mode"] == "assumed_no_metadata"


def test_normalize_gsd_clamps_when_crop_exceeds_image():
    """Very fine source on a tiny image can't crop wider than the image itself."""
    tiny_image = np.random.randint(0, 255, (50, 50, 3), dtype=np.uint8)
    normalized, info = normalize_gsd(tiny_image, source_gsd_m=0.05)
    assert info["mode"] == "clamped_to_full_image"
    assert info["crop_side_px"] == 50
