/**
 * Preloaded example images for the demo gallery -- curated real satellite
 * imagery the model has never seen during training, so judges can trust
 * results are genuine generalization, not memorized training data.
 *
 * HOW TO ADD IMAGES:
 * 1. Drop the actual image file into frontend/public/example-images/
 * 2. Add an entry here with the matching filename.
 *
 * Good candidates already on hand (per project history):
 *   - Held-out GAMUS val tiles (never trained on -- e.g. the dense-tile
 *     qualitative-check crops used during segmentation evaluation)
 *   - The Wikimedia Commons Sentinel-2 crops used for the earlier
 *     generalization test (New Delhi, Kolkata, Gangotri Glacier) --
 *     real ESA imagery, genuinely out-of-distribution for GAMUS
 *   - test_images/san_francisco_geotiff.tif (already in the repo) for
 *     a georeferenced example specifically
 *
 * `type`: "png" | "jpg" | "tif" -- must match the actual file extension.
 * `georeferenced`: true only for real GeoTIFFs with valid geotransform/CRS
 *   (affects which badge shows in the gallery -- doesn't change behavior,
 *   the backend still auto-detects this independently on upload).
 */
const exampleImages = [
  // {
  //   id: "gamus-val-dense-01",
  //   filename: "gamus_val_tile_655.png",
  //   type: "png",
  //   label: "Dense urban block",
  //   source: "GAMUS (held-out validation tile)",
  //   description: "Never used in training -- validation split only.",
  //   georeferenced: false,
  // },
  // {
  //   id: "sentinel2-new-delhi",
  //   filename: "sentinel2_new_delhi_crop.png",
  //   type: "png",
  //   label: "New Delhi",
  //   source: "ESA Sentinel-2 (Wikimedia Commons)",
  //   description: "Real satellite imagery, out-of-distribution for GAMUS.",
  //   georeferenced: false,
  // },
  // {
  //   id: "sf-geotiff",
  //   filename: "san_francisco_geotiff.tif",
  //   type: "tif",
  //   label: "San Francisco",
  //   source: "GeoTIFF test asset",
  //   description: "Georeferenced -- exercises the SRTM calibration path.",
  //   georeferenced: true,
  // },
];

export default exampleImages;
