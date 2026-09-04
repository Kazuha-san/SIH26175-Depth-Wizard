"""
SRTM 30m fetch + alignment helpers.
Used by Stage 2 to get the coarse elevation reference for calibration.
"""


def fetch_srtm_for_bounds(bounds, out_path: str = None):
    """TODO: fetch SRTM tile(s) covering `bounds` via OpenTopography API."""
    raise NotImplementedError


def resample_to_match(srtm_array, target_shape, target_transform):
    """TODO: resample SRTM grid to align pixel-for-pixel with the predicted height map."""
    raise NotImplementedError
