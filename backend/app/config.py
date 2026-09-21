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

# Land-cover segmentation checkpoint, feeds Stage 2's per-class calibration
# (Innovation #1) at inference time, when no ground-truth GAMUS mask exists.
# Drop the trained notebook checkpoint here (e.g. landcover_seg_v6.pth once
# validated). If this file is missing, routes.py logs a warning and the
# pipeline falls back to global affine calibration -- degraded, not broken.
LANDCOVER_MODEL_CHECKPOINT = "checkpoints/landcover_seg_v6.pth"

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

# Tree canopy is the noisiest class for the depth model (high-frequency,
# individual branches/gaps) and a plane-fit would misrepresent it, so
# instead of flattening it we remove it and infer the ground underneath
# by nearest-neighbor inpainting from surrounding non-tree pixels (see
# stage3_mesh_prep.suppress_tree_noise). Prioritizes clean terrain/
# building shape over any attempt at representing canopy height.
SUPPRESS_TREE_HEIGHT = True
TREE_LANDCOVER_CLASS = "tree"

# Global outlier clamp on the final DSM -- catches raw Stage 1 depth
# hallucination in non-building/non-tree terrain (a known failure mode:
# the depth model reverting to a "distant vista gradient" prior when
# uncertain about a region, producing a tall dome/ridge that neither
# flatten_planar_classes (buildings only) nor suppress_tree_noise (tree
# only) ever touches). Clips to the given percentile range as the last
# step in clean_dsm_for_mesh, AFTER building protection, so a legitimate
# tall building can't get clipped by its own flattening -- only genuine
# outliers in the unprotected terrain get pulled in.
#
# IMPORTANT: percentile bounds are computed from STABLE_BASELINE_CLASSES
# pixels only (ground/road), NOT from all non-building pixels. Originally
# used all non-building pixels, which quietly failed on tree-dominated
# scenes: if trees make up most of the image, the hallucinating tree
# pixels dominate the percentile calculation itself, pulling the "97th
# percentile" threshold up to match their own inflated values -- so nothing
# meaningful got clamped in exactly the scenes that needed it most.
# Anchoring to ground/road instead means the clamp threshold reflects
# genuinely reliable terrain regardless of how much of the image is trees.
DSM_OUTLIER_CLAMP_PERCENTILES = (1, 97)
STABLE_BASELINE_CLASSES = ["ground", "road"]

SRTM_RESOLUTION_M = 30

# Stage 3 mesh export defaults
MESH_MAX_RESOLUTION = 256  # downsample DSM to at most this many px/side before meshing
MESH_VERTICAL_EXAGGERATION = 1.0
