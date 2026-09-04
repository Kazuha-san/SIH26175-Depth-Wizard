"""
Model definition wrapper around Depth Anything V2.
Keeps the fine-tuning architecture decisions (which layers frozen,
what head is attached) in ONE place, separate from inference logic
(stage1_depth.py) and training loop logic (training/train.py).
"""


class DepthBackbone:
    """
    TODO: wraps the pretrained Depth Anything V2 ViT encoder + decoder.
    Freeze most encoder layers, expose a fine-tunable head for the
    RS domain gap adaptation.
    """

    def __init__(self, pretrained_path: str, freeze_encoder: bool = True):
        raise NotImplementedError

    def forward(self, x):
        raise NotImplementedError
