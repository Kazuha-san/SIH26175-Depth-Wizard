"""
Loads the GAMUS dataset (huggingface.co/datasets/earthflow/GAMUS) for
fine-tuning: RGB tiles + nDSM ground truth + 6-class land-cover masks.
"""


def load_gamus_split(split: str = "train"):
    """TODO: load via HuggingFace `datasets` library. split in {train, val, test}."""
    raise NotImplementedError


def get_landcover_mask(sample):
    """TODO: extract the 6-class semantic mask for a GAMUS sample (used by Stage 2)."""
    raise NotImplementedError
