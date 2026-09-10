"""
Smoke tests for the pipeline stages.

Stage 2 (calibration, SRTM utils, GeoTIFF utils) now has real, passing tests
in their own files: test_stage2_calibration.py, test_srtm_utils.py,
test_geotiff_utils.py. This file is for Stage 1 (depth model) and Stage 3
(mesh prep) once those have real implementations to test.
"""


def test_stage1_output_shape():
    """TODO: once stage1_depth.run_inference exists, assert output shape matches input."""
    pass


def test_stage1_gsd_normalization():
    """TODO: once stage1_depth.normalize_gsd exists, test it resamples correctly
    for a few different source_gsd_m values."""
    pass


def test_stage3_smoothing_preserves_edges():
    """TODO: once stage3_mesh_prep.smooth_dsm exists, test it reduces noise
    (e.g. variance in a flat region) while preserving a real step edge
    (e.g. a synthetic building-height discontinuity)."""
    pass
