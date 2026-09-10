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

const normalizeHeight = (sample, min, max) => {
  return min + (sample / 65535) * (max - min);
};

/**
 * Decodes the backend 16-bit grayscale PNG into real-world height values.
 * This utility intentionally has no React or Three.js dependency.
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
  const source = image.data;

  if (!source) {
    throw new Error("Decoded heightmap contains no pixel data.");
  }

  let samples;

  if (source instanceof Uint16Array) {
    samples = source;
  } else if (source instanceof Uint8Array && source.byteLength >= pixelCount * 2) {
    samples = new Uint16Array(
      source.buffer,
      source.byteOffset,
      pixelCount,
    );
  } else {
    throw new Error("Heightmap decoder did not return 16-bit grayscale data.");
  }

  if (samples.length < pixelCount) {
    throw new Error(
      `Heightmap data is incomplete. Expected ${pixelCount} pixels but received ${samples.length}.`,
    );
  }

  const data = new Float32Array(pixelCount);

  for (let index = 0; index < pixelCount; index += 1) {
    data[index] = normalizeHeight(samples[index], min, max);
  }

  return {
    width: image.width,
    height: image.height,
    data,
  };
};

export default getHeightData;
