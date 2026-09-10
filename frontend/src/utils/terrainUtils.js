import * as THREE from "three";

export const TERRAIN_SIZE = 12;

/**
 * Build a terrain plane from decoded elevation samples.
 *
 * The geometry is centered around the minimum elevation so camera placement
 * stays stable for both relative and georeferenced backend results.
 */
export const createTerrainGeometry = ({
  width,
  height,
  data,
  min = 0,
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

  for (let index = 0; index < positions.count; index += 1) {
    const elevation = Number(data[index]);
    const relativeElevation = Number.isFinite(elevation)
      ? elevation - baseElevation
      : 0;

    positions.setZ(index, relativeElevation * exaggeration);
  }

  positions.needsUpdate = true;
  geometry.computeVertexNormals();
  geometry.computeBoundingBox();
  geometry.computeBoundingSphere();

  return geometry;
};

export default createTerrainGeometry;
