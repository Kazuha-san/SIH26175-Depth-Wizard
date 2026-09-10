"""
SRTM 30m fetch + alignment helpers.
Used by Stage 2 to get the coarse elevation reference for calibration.

Fetch uses the `elevation` package (Tilezen/Mapzen's public SRTM tile
store) -- free, no API key/account needed, unlike OpenTopography's API
which requires registration for some endpoints. Good fit given this
project has no budget for accounts/keys either.
"""
import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling
from rasterio.transform import from_bounds


def fetch_srtm_for_bounds(bounds: tuple, out_path: str = "/tmp/srtm_clip.tif",
                           product: str = "SRTM1", timeout_s: int = 60):
    """
    Fetch an SRTM tile clipped to `bounds` = (min_lon, min_lat, max_lon, max_lat),
    i.e. a WGS84 bounding box -- this must match the georeferenced input image's
    own bounds (see geotiff_utils.read_geotiff_metadata).

    Uses the `elevation` package, which wraps Mapzen/Tilezen's public SRTM tile
    store -- free, no API key. `product="SRTM1"` = 30m (default); "SRTM3" = 90m
    is a smaller/faster download if 30m ever proves too slow for the demo.

    IMPORTANT (Windows): `elevation` shells out to GDAL command-line tools
    (gdalwarp, gdalbuildvrt, gdal_translate), NOT just the `rasterio`/GDAL
    Python bindings you already have installed. If those aren't on PATH this
    raises a clear RuntimeError telling you what to install, instead of the
    opaque subprocess failure the `elevation` package gives by default.

    Raises RuntimeError (not NotImplementedError) on any failure -- caller
    (routes.py) already catches broad Exception and falls back to the
    non-georeferenced path, logging the real reason in srtm_fallback_reason.
    """
    import os
    import shutil
    import subprocess

    if shutil.which("gdalwarp") is None:
        raise RuntimeError(
            "SRTM fetch needs the GDAL command-line tools (gdalwarp etc.), "
            "not just rasterio's bundled GDAL. On your machine: "
            "`conda install -c conda-forge gdal elevation` (recommended on "
            "Windows), or if using pip, install GDAL's CLI tools separately "
            "and put them on PATH, then `pip install elevation`."
        )

    try:
        import elevation
    except ImportError as exc:
        raise RuntimeError(
            "The `elevation` package isn't installed. Run: pip install elevation"
        ) from exc

    min_lon, min_lat, max_lon, max_lat = bounds
    if not (-180 <= min_lon < max_lon <= 180 and -90 <= min_lat < max_lat <= 90):
        raise RuntimeError(f"Invalid/degenerate WGS84 bounds for SRTM fetch: {bounds}")

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    try:
        elevation.clip(bounds=(min_lon, min_lat, max_lon, max_lat),
                        output=out_path, product=product)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"elevation.clip() failed (GDAL subprocess error): {exc}. "
            f"Common cause: no network access to Mapzen's tile store, or a "
            f"stale/corrupt cache -- try `elevation.clean()` and retry."
        ) from exc
    except Exception as exc:
        raise RuntimeError(f"elevation.clip() failed: {exc}") from exc

    if not os.path.exists(out_path):
        raise RuntimeError(
            f"elevation.clip() reported success but produced no file at {out_path}."
        )

    # Sanity-check the fetched raster actually has real elevation values
    # (a bad clip can silently produce an all-nodata/all-zero tile).
    with rasterio.open(out_path) as src:
        data = src.read(1)
        valid = data[data != src.nodata] if src.nodata is not None else data
        if valid.size == 0 or (valid.max() - valid.min()) < 0.5:
            raise RuntimeError(
                f"Fetched SRTM tile at {out_path} looks empty/flat "
                f"(min={valid.min() if valid.size else 'n/a'}, "
                f"max={valid.max() if valid.size else 'n/a'}) -- likely a bad "
                f"clip (bounds over ocean/void, or corrupted cache)."
            )

    return out_path


def resample_to_match(srtm_path: str, target_shape: tuple, target_transform,
                       target_crs) -> np.ndarray:
    """
    Resamples an SRTM raster (read from `srtm_path`) onto the SAME pixel
    grid as the predicted height map -- i.e. same shape, same transform,
    same CRS -- so Stage 2's per-pixel calibration math can operate on two
    arrays that line up 1:1.

    `target_transform` / `target_crs`: from the input image's own rasterio
    dataset (see geotiff_utils.read_geotiff_metadata) -- SRTM must be
    reprojected/resampled to match the georeferenced INPUT's grid, not the
    other way around, since the input's resolution is what we're producing
    a DSM at.

    Uses bilinear resampling since SRTM is being upsampled (30m -> finer
    target resolution) -- bilinear is the right choice for continuous
    elevation data (nearest-neighbor would introduce blocky artifacts,
    cubic can overshoot/ring near sharp SRTM voids).
    """
    with rasterio.open(srtm_path) as src:
        resampled = np.empty(target_shape, dtype=np.float32)
        reproject(
            source=rasterio.band(src, 1),
            destination=resampled,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=target_transform,
            dst_crs=target_crs,
            resampling=Resampling.bilinear,
        )
    return resampled
