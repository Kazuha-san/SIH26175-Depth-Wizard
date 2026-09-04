/**
 * Innovation #2 -- swaps/blends the terrain mesh's texture between
 * the RGB image and the per-pixel confidence/uncertainty heatmap
 * (produced by the backend's MC-dropout inference).
 */

export function applyConfidenceOverlay(mesh, confidenceMap, blend = 1.0) {
  // TODO: generate a heatmap texture from confidenceMap, blend with
  // or swap out the mesh's current RGB material map
  throw new Error('not implemented')
}
