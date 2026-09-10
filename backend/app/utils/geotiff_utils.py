"""
GeoTIFF read/write + georeferencing detection.
Used by the /upload route to decide georeferenced vs non-georeferenced
input path, and to read CRS/bounds/GSD for the metadata panel and for
Stage 2's SRTM fetch (needs the input's own bounds to fetch a matching
SRTM tile).
"""
import rasterio
from rasterio.warp import transform_bounds


def is_georeferenced(file_path: str) -> bool:
    """
    True for a valid GeoTIFF with real CRS + transform metadata, False for
    plain PNG/JPG (or a TIFF with no georeferencing, which does happen --
    not every .tif is geo-tagged, so don't assume based on extension alone).
    """
    try:
        with rasterio.open(file_path) as src:
            return src.crs is not None and src.transform is not None and not src.transform.is_identity
    except rasterio.errors.RasterioIOError:
        # Not a format rasterio can open at all (e.g. a plain PNG/JPG) --
        # definitely not georeferenced.
        return False


def read_geotiff_metadata(file_path: str) -> dict:
    """
    Returns {crs, bounds_wgs84, resolution_m, width, height} for a
    georeferenced input. bounds_wgs84 is always reprojected to EPSG:4326
    (plain lon/lat) regardless of the file's native CRS, since that's what
    SRTM fetch (srtm_utils.fetch_srtm_for_bounds) needs.

    resolution_m is a rough estimate: for a file already in a projected
    (metric) CRS this is exact; for a file in a geographic CRS (degrees)
    this is an approximation using the pixel size in degrees converted
    at the scene's latitude -- good enough for GSD-normalization decisions,
    not survey-grade.
    """
    with rasterio.open(file_path) as src:
        bounds_native = src.bounds
        bounds_wgs84 = transform_bounds(src.crs, "EPSG:4326", *bounds_native)

        pixel_size_x = abs(src.transform.a)
        pixel_size_y = abs(src.transform.e)

        if src.crs.is_geographic:
            # Pixel size is in degrees -- convert to meters using the
            # standard ~111,320 m/degree at the equator, scaled by cos(latitude)
            # for the longitude direction. Approximate but adequate for our use.
            import math
            mean_lat = (bounds_wgs84[1] + bounds_wgs84[3]) / 2
            meters_per_deg_lat = 111_320
            meters_per_deg_lon = 111_320 * math.cos(math.radians(mean_lat))
            resolution_m = (
                (pixel_size_x * meters_per_deg_lon + pixel_size_y * meters_per_deg_lat) / 2
            )
        else:
            resolution_m = (pixel_size_x + pixel_size_y) / 2

        return {
            "crs": str(src.crs),
            "bounds_wgs84": bounds_wgs84,  # (min_lon, min_lat, max_lon, max_lat)
            "resolution_m": float(resolution_m),
            "width": src.width,
            "height": src.height,
        }


def write_dsm_geotiff(dsm_array, transform, crs, out_path: str):
    """Write the final absolute DSM as a standard GeoTIFF (deliverable requirement)."""
    with rasterio.open(
        out_path, "w", driver="GTiff",
        height=dsm_array.shape[0], width=dsm_array.shape[1],
        count=1, dtype=dsm_array.dtype, crs=crs, transform=transform,
    ) as dst:
        dst.write(dsm_array, 1)
