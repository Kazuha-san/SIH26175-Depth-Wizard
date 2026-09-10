import UPNG from "upng-js";

const base64ToArrayBuffer = (base64) => {
  const normalized = base64.includes(",") ? base64.split(",").pop() : base64;
  const binary = atob(normalized);
  const bytes = new Uint8Array(binary.length);

  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }

  return bytes.buffer;
};

const readBigEndianUint16 = (bytes, offset) =>
  (bytes[offset] << 8) | bytes[offset + 1];

const normalizeHeight = (sample, min, max) =>
  min + (sample / 65535) * (max - min);

/**
 * Decode the backend 16-bit grayscale PNG into elevation values.
 *
 * UPNG exposes 16-bit grayscale pixel data as bytes in PNG big-endian
 * order. It must NOT be wrapped directly in Uint16Array because JS typed
 * arrays use the platform's native byte order (normally little-endian).
 */
export const getHeightData = (heightmapBase64, heightMin, heightMax) => {
  if (!heightmapBase64) {
    throw new Error("Heightmap data is missing from the processing result.");
  }

  const min = Number(heightMin);
  const max = Number(heightMax);

  if (!Number.isFinite(min) || !Number.isFinite(max)) {
    throw new Error("Invalid height range received from the backend.");
  }

  if (max <= min) {
    throw new Error(`Invalid height range: ${min} to ${max}.`);
  }

  const image = UPNG.decode(base64ToArrayBuffer(heightmapBase64));

  if (!image?.width || !image?.height) {
    throw new Error("Unable to decode the heightmap PNG.");
  }

  if (image.depth !== 16 || image.ctype !== 0) {
    throw new Error(
      `Unsupported heightmap format: ${image.depth}-bit color type ${image.ctype}. Expected 16-bit grayscale PNG.`,
    );
  }

  const pixelCount = image.width * image.height;
  const bytes = image.data instanceof Uint8Array
    ? image.data
    : new Uint8Array(image.data);

  const requiredBytes = pixelCount * 2;

  if (bytes.byteLength < requiredBytes) {
    throw new Error(
      `Heightmap data is incomplete. Expected at least ${requiredBytes} bytes but received ${bytes.byteLength}.`,
    );
  }

  const data = new Float32Array(pixelCount);

  for (let index = 0; index < pixelCount; index += 1) {
    const sample = readBigEndianUint16(bytes, index * 2);
    data[index] = normalizeHeight(sample, min, max);
  }

  return {
    width: image.width,
    height: image.height,
    data,
    min,
    max,
  };
};

export default getHeightData;
