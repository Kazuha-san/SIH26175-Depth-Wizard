"""
Central config: paths, model checkpoint locations, constants.
Keep all magic numbers/paths here, not scattered in pipeline code.
"""

# Fine-tuned checkpoint in use. v4 is the current best-validated model
# (v5's structure_loss experiment regressed MAE across every class when
# re-scored on a fixed validation split -- see training/ notes -- so v4
# remains the checkpoint this pipeline loads until a future version beats
# it on an apples-to-apples comparison).
DEPTH_MODEL_CHECKPOINT = "checkpoints/depth_anything_v2_gamus_v4.pth"

# GAMUS land-cover class IDs (used by Stage 2 per-class calibration AND by
# Stage 3's per-instance shape cleanup). Must match gamus_loader.GAMUS_CLASS_NAMES.
LANDCOVER_CLASS_IDS = {
    "unlabeled": 0,
    "ground": 1,
    "low_vegetation": 2,
    "building": 3,
    "water": 4,
    "road": 5,
    "tree": 6,
}
LANDCOVER_CLASSES = list(LANDCOVER_CLASS_IDS.keys())

# Classes that get flattened/plane-fit in Stage 3's shape cleanup -- these
# are the "should look like a solid, mostly-flat-topped object" classes.
# Ground/road/water are naturally near-flat already; tree canopy is
# deliberately excluded (canopy has real internal height variance that
# flattening would misrepresent -- flag it via confidence instead, per
# Innovation #2).
PLANAR_LANDCOVER_CLASSES = ["building"]

SRTM_RESOLUTION_M = 30

# Stage 3 mesh export defaults
MESH_MAX_RESOLUTION = 256  # downsample DSM to at most this many px/side before meshing
MESH_VERTICAL_EXAGGERATION = 1.0
