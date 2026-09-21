import * as THREE from "three";

export const loadTextureFromBase64 = (base64) => {
  if (!base64) {
    return Promise.reject(new Error("Terrain texture is missing."));
  }

  const source = base64.includes(",")
    ? base64
    : `data:image/png;base64,${base64}`;

  return new Promise((resolve, reject) => {
    const loader = new THREE.TextureLoader();

    loader.load(
      source,
      (texture) => {
        texture.colorSpace = THREE.SRGBColorSpace;
        texture.wrapS = THREE.ClampToEdgeWrapping;
        texture.wrapT = THREE.ClampToEdgeWrapping;
        texture.minFilter = THREE.LinearFilter;
        texture.magFilter = THREE.LinearFilter;
        texture.needsUpdate = true;
        resolve(texture);
      },
      undefined,
      (error) => reject(error instanceof Error ? error : new Error("Unable to load terrain texture.")),
    );
  });
};

// Low-confidence -> high-confidence color ramp for the uncertainty overlay.
// Red/orange reads as "less sure" and green as "confident" -- a common,
// intuitive convention, not a domain-specific one that needs a legend to parse.
const CONFIDENCE_RAMP = [
  { stop: 0.0, color: [239, 68, 68] },   // red   -- low confidence
  { stop: 0.5, color: [250, 204, 21] },  // amber -- mid
  { stop: 1.0, color: [34, 197, 94] },   // green -- high confidence
];

const rampColorAt = (t) => {
  for (let i = 0; i < CONFIDENCE_RAMP.length - 1; i += 1) {
    const a = CONFIDENCE_RAMP[i];
    const b = CONFIDENCE_RAMP[i + 1];
    if (t >= a.stop && t <= b.stop) {
      const localT = (t - a.stop) / (b.stop - a.stop || 1);
      return [
        Math.round(a.color[0] + (b.color[0] - a.color[0]) * localT),
        Math.round(a.color[1] + (b.color[1] - a.color[1]) * localT),
        Math.round(a.color[2] + (b.color[2] - a.color[2]) * localT),
      ];
    }
  }
  return CONFIDENCE_RAMP[CONFIDENCE_RAMP.length - 1].color;
};

// Precompute a 256-entry LUT once per module load -- cheap, avoids
// recomputing the ramp per-pixel on every confidence texture load.
const CONFIDENCE_LUT = Array.from({ length: 256 }, (_, i) => rampColorAt(i / 255));

/**
 * Decodes the backend's 8-bit grayscale confidence PNG and recolors it
 * through CONFIDENCE_RAMP on a canvas, returning a THREE.CanvasTexture --
 * this is what makes the uncertainty overlay (Innovation #2) actually
 * visible on the terrain instead of a hard-to-read grayscale map.
 */
export const loadConfidenceTextureFromBase64 = (base64) => {
  if (!base64) {
    return Promise.reject(new Error("Confidence data is missing from this result."));
  }

  const source = base64.includes(",")
    ? base64
    : `data:image/png;base64,${base64}`;

  return new Promise((resolve, reject) => {
    const image = new Image();

    image.onload = () => {
      const canvas = document.createElement("canvas");
      canvas.width = image.width;
      canvas.height = image.height;
      const ctx = canvas.getContext("2d");
      ctx.drawImage(image, 0, 0);

      const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
      const { data } = imageData;

      for (let i = 0; i < data.length; i += 4) {
        const gray = data[i]; // grayscale PNG -- R, G, B channels are equal
        const [r, g, b] = CONFIDENCE_LUT[gray];
        data[i] = r;
        data[i + 1] = g;
        data[i + 2] = b;
        // alpha channel (data[i + 3]) left untouched
      }

      ctx.putImageData(imageData, 0, 0);

      const texture = new THREE.CanvasTexture(canvas);
      texture.colorSpace = THREE.SRGBColorSpace;
      texture.wrapS = THREE.ClampToEdgeWrapping;
      texture.wrapT = THREE.ClampToEdgeWrapping;
      texture.minFilter = THREE.LinearFilter;
      texture.magFilter = THREE.LinearFilter;
      texture.needsUpdate = true;
      resolve(texture);
    };

    image.onerror = () => reject(new Error("Unable to load confidence texture."));
    image.src = source;
  });
};

export default loadTextureFromBase64;
