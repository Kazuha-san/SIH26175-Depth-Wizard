import * as THREE from "three";

export const TERRAIN_SIZE = 12;

export const createTerrainGeometry = ({
  width,
  height,
  data,
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

  for (let index = 0; index < positions.count; index += 1) {
    const elevation = Number(data[index]);
    positions.setZ(index, Number.isFinite(elevation) ? elevation * exaggeration : 0);
  }

  positions.needsUpdate = true;
  geometry.computeVertexNormals();
  geometry.computeBoundingBox();
  geometry.computeBoundingSphere();

  return geometry;
};

export default createTerrainGeometry;
