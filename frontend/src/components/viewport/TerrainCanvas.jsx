/**
 * The core Three.js viewport. Owns the renderer/scene/camera lifecycle
 * (via useEffect + a ref'd <canvas>), and composes:
 *   - meshBuilder.js       (height map -> mesh + RGB texture)
 *   - CameraControls.js    (flythrough / orbit navigation)
 *   - ConfidenceOverlay.js (Innovation #2 toggle)
 * This file should stay thin -- actual Three.js logic lives in the
 * sibling .js modules, this just wires them into the React lifecycle.
 */
import { useEffect, useRef } from 'react'

export default function TerrainCanvas({ heightMap, rgbTexture, confidenceMap }) {
  const canvasRef = useRef(null)

  useEffect(() => {
    // TODO: init THREE.Scene/Camera/Renderer here, build mesh via
    // meshBuilder, attach CameraControls, cleanup on unmount
  }, [heightMap])

  return <canvas ref={canvasRef} className="terrain-canvas" />
}
