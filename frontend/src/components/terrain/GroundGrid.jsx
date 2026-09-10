import React, { useMemo } from "react";
import { Grid } from "@react-three/drei";

const MIN_GROUND_SIZE = 32;
const GROUND_MARGIN_FACTOR = 1.5;
const GROUND_Y = -0.12;

/**
 * Render the viewer reference ground underneath the terrain.
 *
 * The ground follows the rendered terrain footprint instead of relying on a
 * hard-coded size. A 32-unit minimum preserves the current visual scale for
 * the existing 12-unit terrain, while larger terrain footprints automatically
 * receive a larger reference grid.
 */
const GroundGrid = ({ terrainSize = 12 }) => {
  const groundSize = useMemo(() => {
    const size = Number(terrainSize);

    if (!Number.isFinite(size) || size <= 0) {
      return MIN_GROUND_SIZE;
    }

    return Math.max(MIN_GROUND_SIZE, size * GROUND_MARGIN_FACTOR);
  }, [terrainSize]);

  const fadeDistance = groundSize * 0.875;

  return (
    <group position={[0, GROUND_Y, 0]}>
      <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
        <planeGeometry args={[groundSize, groundSize]} />
        <meshStandardMaterial
          color="#111923"
          roughness={1}
          metalness={0}
        />
      </mesh>

      <Grid
        args={[groundSize, groundSize]}
        cellSize={1}
        cellThickness={0.45}
        cellColor="#1d6fa5"
        sectionSize={4}
        sectionThickness={0.8}
        sectionColor="#2c8ac4"
        fadeDistance={fadeDistance}
        fadeStrength={1.1}
        infiniteGrid={false}
      />
    </group>
  );
};

export default GroundGrid;
