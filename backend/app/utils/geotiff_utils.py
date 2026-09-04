"""
GeoTIFF read/write + georeferencing detection.
Used by the /upload route to decide georeferenced vs non-georeferenced
input path, and to read CRS/bounds/GSD for the metadata panel.
"""


def is_georeferenced(file_path: str) -> bool:
    """TODO: check for CRS/transform via rasterio. True for valid GeoTIFF, False for PNG/JPG."""
    raise NotImplementedError


def read_geotiff_metadata(file_path: str) -> dict:
    """TODO: return {crs, bounds, resolution_m, width, height} via rasterio."""
    raise NotImplementedError


def write_dsm_geotiff(dsm_array, transform, crs, out_path: str):
    """TODO: write the final absolute DSM as a standard GeoTIFF (deliverable requirement)."""
    raise NotImplementedError
