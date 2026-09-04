"""
Loss functions for depth backbone fine-tuning.
Scale-invariant loss is important here since the raw scale is
ambiguous (that's Stage 2's job to fix later, not the training loss's).
"""


def scale_invariant_loss(pred, target):
    """TODO: standard scale-invariant log loss used across MHE literature."""
    raise NotImplementedError
