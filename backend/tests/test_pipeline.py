"""
Smoke tests for the pipeline stages. Start simple: shapes in == shapes out,
no NaNs, calibration doesn't blow up on a dummy scene.
Expand as each stage gets implemented.
"""


def test_stage1_output_shape():
    """TODO: once stage1_depth.run_inference exists, assert output shape matches input."""
    pass


def test_stage2_per_class_calibration_runs():
    """TODO: once stage2_calibration.per_class_calibration exists, test on dummy arrays."""
    pass
