import { getHeightData } from "./getHeightData";
import { getElevationColor } from "./terrainUtils";

/**
 * Render the backend's 16-bit heightmap PNG into a flat, 2D hypsometric
 * preview image (same color ramp as the 3D "Elevation" mode) so it can be
 * shown as a plain <img> in the sidebar preview panels -- the raw 16-bit
 * grayscale PNG the backend returns is nearly black/unreadable to the eye
 * at typical elevation ranges, so this re-colors it the same way the 3D
 * view does instead of showing the raw file directly.
 *
 * Returns a data: URL (PNG) via canvas.toDataURL, or throws if the
 * heightmap can't be decoded -- callers should catch and fall back to a
 * placeholder rather than let this block the rest of the results screen.
 */
export const renderHeightmapPreview = (resultData) => {
  const { width, height, data, min, max } = getHeightData(
    resultData?.heightmap_png_b64,
    resultData?.height_min,
    resultData?.height_max,
  );

  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;

  const ctx = canvas.getContext("2d");
  const imageData = ctx.createImageData(width, height);
  const range = Math.max(1e-6, max - min);

  for (let index = 0; index < width * height; index += 1) {
    const normalized = (data[index] - min) / range;
    const [r, g, b] = getElevationColor(normalized);
    const offset = index * 4;
    imageData.data[offset] = Math.round(r * 255);
    imageData.data[offset + 1] = Math.round(g * 255);
    imageData.data[offset + 2] = Math.round(b * 255);
    imageData.data[offset + 3] = 255;
  }

  ctx.putImageData(imageData, 0, 0);
  return canvas.toDataURL("image/png");
};

export default renderHeightmapPreview;
