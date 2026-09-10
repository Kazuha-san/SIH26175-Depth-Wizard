import numpy as np
from app.pipeline.stage2_calibration import global_affine_fit, per_class_calibration, normalize_for_visualization

np.random.seed(42)
H, W = 64, 64

# --- Build synthetic scene: 3 classes with DIFFERENT relative-height biases,
# mimicking what we actually found (buildings/trees behave differently than
# ground). True absolute height per class, then simulate a relative_height
# prediction that's scaled/shifted differently per class + noise.
landcover = np.random.choice([1, 3, 6], size=(H, W))  # ground, building, tree

true_height = np.zeros((H, W))
true_height[landcover == 1] = np.random.uniform(0, 2, size=(landcover == 1).sum())     # ground: near 0
true_height[landcover == 3] = np.random.uniform(8, 15, size=(landcover == 3).sum())    # building: 8-15m
true_height[landcover == 6] = np.random.uniform(5, 25, size=(landcover == 6).sum())    # tree: 5-25m

# Simulate relative_height: different scale/offset bias per class (this is
# exactly the scenario per-class calibration is meant to fix)
relative_height = np.zeros((H, W))
relative_height[landcover == 1] = true_height[landcover == 1] * 0.5 + 1.0 + np.random.normal(0, 0.1, (landcover==1).sum())
relative_height[landcover == 3] = true_height[landcover == 3] * 2.0 - 3.0 + np.random.normal(0, 0.3, (landcover==3).sum())
relative_height[landcover == 6] = true_height[landcover == 6] * 0.8 + 2.0 + np.random.normal(0, 0.5, (landcover==6).sum())

# "SRTM reference" = true height, heavily smoothed/coarsened to mimic 30m resolution
# (here just simulate as true_height + small noise, since we don't have a real raster to blur)
srtm_reference = true_height + np.random.normal(0, 0.2, (H, W))

print("=== Test 1: global_affine_fit ===")
a, b, global_calibrated = global_affine_fit(relative_height, srtm_reference)
global_mae = np.mean(np.abs(global_calibrated - true_height))
print(f"Global fit: a={a:.3f} b={b:.3f}  MAE vs true height: {global_mae:.3f}m")

print("\n=== Test 2: per_class_calibration ===")
per_class_calibrated, params = per_class_calibration(relative_height, srtm_reference, landcover)
per_class_mae = np.mean(np.abs(per_class_calibrated - true_height))
print(f"Per-class MAE vs true height: {per_class_mae:.3f}m")
for cid, p in params.items():
    print(f"  class {cid}: a={p['a']:.3f} b={p['b']:.3f} n={p['n_pixels']} fallback={p['fallback']}")

print(f"\nImprovement: global MAE {global_mae:.3f}m -> per-class MAE {per_class_mae:.3f}m "
      f"({100*(1 - per_class_mae/global_mae):.1f}% better)")

assert per_class_mae < global_mae, "Per-class calibration should beat global fit on this synthetic multi-bias scene"
print("PASS: per-class calibration outperforms global fit, as expected")

print("\n=== Test 3: rare/missing class fallback ===")
landcover_sparse = landcover.copy()
landcover_sparse[landcover_sparse == 6] = 1  # remove tree entirely
landcover_sparse[0, 0] = 6  # exactly 1 tree pixel -- should trigger fallback (< min_pixels_per_class)
_, params_sparse = per_class_calibration(relative_height, srtm_reference, landcover_sparse)
print("class 6 params (should be fallback=True with n_pixels=1):", params_sparse.get(6))
assert params_sparse[6]["fallback"] == True and params_sparse[6]["n_pixels"] == 1
print("PASS: rare class correctly falls back to global fit instead of unstable per-class fit")

print("\n=== Test 4: normalize_for_visualization (non-georeferenced path) ===")
norm = normalize_for_visualization(relative_height)
print(f"Normalized range: [{norm.min():.3f}, {norm.max():.3f}] (should be within [0,1])")
assert norm.min() >= 0.0 and norm.max() <= 1.0
print("PASS: normalized output stays in [0,1]")

print("\n=== Test 5: shape mismatch raises clearly ===")
try:
    global_affine_fit(relative_height, srtm_reference[:-1, :])
    print("FAIL: should have raised ValueError")
except ValueError as e:
    print(f"PASS: raised ValueError as expected: {e}")

print("\n=== Test 6: degenerate flat input for normalize_for_visualization ===")
flat = np.ones((10, 10)) * 5.0
norm_flat = normalize_for_visualization(flat)
print(f"Flat input -> output range [{norm_flat.min()}, {norm_flat.max()}] (should be all zeros, no crash)")
assert np.all(norm_flat == 0)
print("PASS: degenerate flat input handled without divide-by-zero crash")

print("\nAll tests passed.")
