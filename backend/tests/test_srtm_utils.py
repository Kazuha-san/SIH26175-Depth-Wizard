import numpy as np
import rasterio
from rasterio.transform import from_bounds
from app.data.srtm_utils import resample_to_match

print("=== Test: resample_to_match with a synthetic coarse 'SRTM' raster ===")

# Create a synthetic coarse raster (simulating SRTM at ~30m, i.e. fewer pixels
# over the same geographic area than our target fine-resolution grid)
coarse_h, coarse_w = 10, 10
bounds = (77.20, 28.60, 77.22, 28.62)  # a small lon/lat box (roughly Delhi-sized coords)
coarse_transform = from_bounds(*bounds, coarse_w, coarse_h)

# Synthetic elevation: a simple gradient so we can sanity-check the resample
# doesn't scramble values -- low in one corner, high in the other
coarse_data = np.linspace(100, 200, coarse_h * coarse_w).reshape(coarse_h, coarse_w).astype(np.float32)

srtm_path = "/tmp/test_srtm.tif"
with rasterio.open(
    srtm_path, "w", driver="GTiff", height=coarse_h, width=coarse_w,
    count=1, dtype="float32", crs="EPSG:4326", transform=coarse_transform,
) as dst:
    dst.write(coarse_data, 1)

# Target: a much finer grid (simulating our depth model's higher-res prediction)
target_h, target_w = 100, 100
target_transform = from_bounds(*bounds, target_w, target_h)

resampled = resample_to_match(srtm_path, (target_h, target_w), target_transform, "EPSG:4326")

print(f"Coarse input shape: {coarse_data.shape}, range [{coarse_data.min():.1f}, {coarse_data.max():.1f}]")
print(f"Resampled output shape: {resampled.shape}, range [{np.nanmin(resampled):.1f}, {np.nanmax(resampled):.1f}]")

assert resampled.shape == (target_h, target_w), "Output shape must match target grid"
# Bilinear resample of a smooth gradient should stay within (or very close to) the original value range
assert np.nanmin(resampled) >= coarse_data.min() - 5, "Resampled min shouldn't undershoot original range much"
assert np.nanmax(resampled) <= coarse_data.max() + 5, "Resampled max shouldn't overshoot original range much"

# Check the gradient direction is preserved (low corner still low, high corner still high)
assert resampled[0, 0] < resampled[-1, -1], "Gradient direction should be preserved after resampling"

print("PASS: resample_to_match produces correctly-shaped, value-sane output preserving the input gradient")
