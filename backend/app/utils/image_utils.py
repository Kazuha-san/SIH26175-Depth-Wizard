"""
Generic image I/O helpers (PNG/JPG loading, resizing, normalization)
shared across pipeline stages.
"""


def load_image(file_path: str):
    """TODO: load PNG/JPG as numpy array (RGB)."""
    raise NotImplementedError


def resize_for_model(image, target_size: tuple):
    """TODO: resize/pad image to the depth model's expected input size."""
    raise NotImplementedError
