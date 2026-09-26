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
// Deliberately a single-hue (violet) ramp rather than another red/green/
// rainbow scheme -- the elevation ramp already uses blue/teal/green/
// yellow/orange/red/white, so a red-amber-green confidence ramp read as
// "just another heatmap" and was easy to confuse with elevation at a
// glance. Both ends are kept far from white/black -- a near-white top
// stop made real, high-confidence results (which cluster ~0.85-0.98 in
// practice) render as a flat, near-blank surface indistinguishable from
// "no texture loaded", which is exactly the "confidence doesn't work"
// symptom this replaces.
const CONFIDENCE_RAMP = [
  { stop: 0.0, color: [30, 27, 75] },    // dark indigo -- low confidence
  { stop: 0.5, color: [147, 51, 234] },  // violet -- mid
  { stop: 1.0, color: [45, 212, 191] },  // teal -- high confidence
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
 *
 * Real confidence values tend to cluster in a narrow high range (e.g.
 * 0.85-0.98) rather than spanning 0-1, so mapping raw gray values
 * straight through the ramp only ever shows a thin sliver of it and the
 * whole terrain looks like one flat color. This does a per-image min/max
 * contrast stretch first (same idea as the heightmap preview) so the
 * full ramp -- and therefore real variation in confidence -- is always
 * visible, whatever the actual value range happens to be.
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

      let min = 255;
      let max = 0;
      for (let i = 0; i < data.length; i += 4) {
        const gray = data[i];
        if (gray < min) min = gray;
        if (gray > max) max = gray;
      }
      const range = Math.max(1, max - min);

      for (let i = 0; i < data.length; i += 4) {
        const gray = data[i]; // grayscale PNG -- R, G, B channels are equal
        const stretched = Math.round(((gray - min) / range) * 255);
        const [r, g, b] = CONFIDENCE_LUT[stretched];
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
