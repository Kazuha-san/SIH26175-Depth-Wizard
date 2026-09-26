import * as THREE from "three";

export const TERRAIN_SIZE = 12;

/**
 * Hypsometric-tint color ramp (classic elevation coloring: low = blue/
 * teal -> green -> yellow -> orange -> red -> white at the peaks) -- the
 * same idea as the reference DSM images (blue lowlands/water, green/
 * yellow midground, red/white highlands + a scale bar). t is normalized
 * height in [0, 1].
 *
 * This is what was MISSING before: the old renderer only ever drew the
 * raw uploaded photo (or a flat fallback color) with standard lighting --
 * there was no elevation-based color anywhere, and no way to read height
 * from color, which is the entire point of a DSM visualization.
 */
export const ELEVATION_STOPS = [
  { t: 0.0, color: [0.07, 0.13, 0.42] },  // deep blue -- lowest points / water
  { t: 0.15, color: [0.02, 0.45, 0.55] }, // teal
  { t: 0.32, color: [0.13, 0.55, 0.25] }, // green
  { t: 0.5, color: [0.55, 0.72, 0.18] },  // yellow-green
  { t: 0.65, color: [0.92, 0.78, 0.15] }, // yellow
  { t: 0.8, color: [0.88, 0.45, 0.1] },   // orange
  { t: 0.92, color: [0.68, 0.16, 0.1] },  // red
  { t: 1.0, color: [1.0, 1.0, 1.0] },     // white -- peaks
];

export const getElevationColor = (t) => {
  const clamped = Math.min(1, Math.max(0, t));

  for (let i = 0; i < ELEVATION_STOPS.length - 1; i += 1) {
    const a = ELEVATION_STOPS[i];
    const b = ELEVATION_STOPS[i + 1];
    if (clamped >= a.t && clamped <= b.t) {
      const localT = (clamped - a.t) / (b.t - a.t || 1);
      return [
        a.color[0] + (b.color[0] - a.color[0]) * localT,
        a.color[1] + (b.color[1] - a.color[1]) * localT,
        a.color[2] + (b.color[2] - a.color[2]) * localT,
      ];
    }
  }
  return ELEVATION_STOPS[ELEVATION_STOPS.length - 1].color;
};

/**
 * Build a terrain plane from decoded elevation samples.
 *
 * The geometry is centered around the minimum elevation so camera placement
 * stays stable for both relative and georeferenced backend results.
 *
 * Also attaches a per-vertex `color` attribute (hypsometric tint, based on
 * each vertex's OWN elevation, not the min/max of the whole scene clipped
 * to whatever exaggeration is applied) so the mesh can be rendered with
 * `vertexColors` -- this is what makes "Elevation" mode possible in
 * TerrainMesh.jsx.
 */
export const createTerrainGeometry = ({
  width,
  height,
  data,
  min = 0,
  max = 1,
  size = TERRAIN_SIZE,
  verticalExaggeration = 0.5,
}) => {
  if (width < 2 || height < 2) {
    throw new Error(`Invalid heightmap resolution: ${width} × ${height}.`);
  }

  if (!data || data.length !== width * height) {
    throw new Error("Decoded heightmap dimensions do not match its data.");
  }

  const geometry = new THREE.PlaneGeometry(size, size, width - 1, height - 1);
  const positions = geometry.attributes.position;
  const exaggeration = Math.max(0.01, Number(verticalExaggeration) || 0.5);
  const baseElevation = Number(min) || 0;
  const elevationRange = Math.max(1e-6, Number(max) - Number(min));

  const colors = new Float32Array(positions.count * 3);

  for (let index = 0; index < positions.count; index += 1) {
    const elevation = Number(data[index]);
    const validElevation = Number.isFinite(elevation) ? elevation : baseElevation;
    const relativeElevation = validElevation - baseElevation;

    positions.setZ(index, relativeElevation * exaggeration);

    const normalized = (validElevation - baseElevation) / elevationRange;
    const [r, g, b] = getElevationColor(normalized);
    colors[index * 3] = r;
    colors[index * 3 + 1] = g;
    colors[index * 3 + 2] = b;
  }

  geometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));

  positions.needsUpdate = true;
  geometry.computeVertexNormals();
  geometry.computeBoundingBox();
  geometry.computeBoundingSphere();

  return geometry;
};

export default createTerrainGeometry;
