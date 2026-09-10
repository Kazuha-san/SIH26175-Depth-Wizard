import numpy as np
import rasterio
from rasterio.transform import from_bounds
from PIL import Image
from app.utils.geotiff_utils import is_georeferenced, read_geotiff_metadata, write_dsm_geotiff

print("=== Test 1: is_georeferenced -- real GeoTIFF ===")
bounds = (77.20, 28.60, 77.22, 28.62)
w, h = 50, 50
transform = from_bounds(*bounds, w, h)
geo_path = "/tmp/test_geo.tif"
with rasterio.open(geo_path, "w", driver="GTiff", height=h, width=w, count=3,
                    dtype="uint8", crs="EPSG:4326", transform=transform) as dst:
    for b in range(1, 4):
        dst.write(np.random.randint(0, 255, (h, w), dtype="uint8"), b)

assert is_georeferenced(geo_path) == True
print("PASS: real GeoTIFF correctly detected as georeferenced")

print("\n=== Test 2: is_georeferenced -- plain PNG (no geo metadata) ===")
png_path = "/tmp/test_plain.png"
Image.fromarray(np.random.randint(0, 255, (50, 50, 3), dtype="uint8")).save(png_path)
assert is_georeferenced(png_path) == False
print("PASS: plain PNG correctly detected as NOT georeferenced")

print("\n=== Test 3: is_georeferenced -- TIFF with no real georeferencing ===")
plain_tif_path = "/tmp/test_plain.tif"
with rasterio.open(plain_tif_path, "w", driver="GTiff", height=50, width=50,
                    count=3, dtype="uint8") as dst:  # no crs, no transform passed
    for b in range(1, 4):
        dst.write(np.random.randint(0, 255, (50, 50), dtype="uint8"), b)
result = is_georeferenced(plain_tif_path)
print(f"Plain TIFF (no crs/transform set) -> is_georeferenced = {result} (should be False)")
assert result == False
print("PASS: TIFF without real geo metadata correctly NOT treated as georeferenced")

print("\n=== Test 4: read_geotiff_metadata ===")
meta = read_geotiff_metadata(geo_path)
print(f"CRS: {meta['crs']}")
print(f"Bounds (WGS84): {meta['bounds_wgs84']}")
print(f"Resolution: {meta['resolution_m']:.2f}m")
print(f"Width x Height: {meta['width']} x {meta['height']}")

assert meta['crs'] == 'EPSG:4326'
assert meta['width'] == w and meta['height'] == h
# bounds should roughly match what we put in
assert abs(meta['bounds_wgs84'][0] - bounds[0]) < 0.01
# resolution: ~0.02 degrees over 50 pixels -> roughly 44m/pixel at this latitude, sanity check order of magnitude
assert 20 < meta['resolution_m'] < 80
print("PASS: metadata extraction returns sane CRS, bounds, and resolution estimate")

print("\n=== Test 5: write_dsm_geotiff round-trip ===")
dsm_out_path = "/tmp/test_dsm_out.tif"
fake_dsm = np.random.uniform(0, 50, (h, w)).astype(np.float32)
write_dsm_geotiff(fake_dsm, transform, "EPSG:4326", dsm_out_path)
with rasterio.open(dsm_out_path) as src:
    written_back = src.read(1)
    assert src.crs == "EPSG:4326"
    assert np.allclose(written_back, fake_dsm)
print("PASS: DSM writes out and reads back identical, with correct CRS")

print("\nAll tests passed.")
