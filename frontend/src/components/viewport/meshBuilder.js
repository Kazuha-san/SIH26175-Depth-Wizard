/**
 * Converts a height map (grid of elevation values) into a Three.js
 * mesh, textured with the original RGB image via UV mapping.
 * Uses GPU-side vertex displacement (shader) for performance on
 * large images rather than CPU-side per-vertex loops.
 */

export function buildTerrainMesh(heightMap, rgbTexture) {
  // TODO: create PlaneGeometry, displace vertices via heightMap
  // (or a vertex shader sampling heightMap as a texture), apply
  // rgbTexture as the material map. Return a THREE.Mesh.
  throw new Error('not implemented')
}
