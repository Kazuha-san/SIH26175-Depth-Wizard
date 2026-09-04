"""
Central config: paths, model checkpoint locations, constants.
Keep all magic numbers/paths here, not scattered in pipeline code.
"""

# TODO: set once fine-tuned checkpoint exists
DEPTH_MODEL_CHECKPOINT = "checkpoints/depth_anything_v2_finetuned.pth"

# GAMUS land-cover classes (used by Stage 2 per-class calibration)
LANDCOVER_CLASSES = ["ground", "low_vegetation", "building", "water", "road", "tree"]

SRTM_RESOLUTION_M = 30
