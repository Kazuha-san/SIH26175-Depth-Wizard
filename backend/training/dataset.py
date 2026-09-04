"""
PyTorch Dataset wrapper around GAMUS for training
(separate from app/data/gamus_loader.py, which is the inference-side
lightweight loader -- this one handles augmentation/batching for training).
"""
from torch.utils.data import Dataset


class GamusDataset(Dataset):
    """TODO: implement __len__ and __getitem__, return (rgb, ndsm, landcover_mask)."""

    def __init__(self, split: str = "train"):
        raise NotImplementedError

    def __len__(self):
        raise NotImplementedError

    def __getitem__(self, idx):
        raise NotImplementedError
