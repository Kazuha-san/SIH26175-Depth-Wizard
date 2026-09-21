import React, { forwardRef, useEffect, useState } from "react";
import { Canvas } from "@react-three/fiber";

import TerrainMesh from "./terrain/TerrainMesh";
import TerrainCamera from "./terrain/TerrainCamera";
import GroundGrid from "./terrain/GroundGrid";
import { TERRAIN_SIZE } from "../utils/terrainUtils";

const TerrainViewer = forwardRef(
  ({ resultData, verticalExaggeration = 0.5, cameraMode = "orbit", textureMode = "rgb", resetSignal = 0 }, ref) => {
    const [error, setError] = useState(null);

    useEffect(() => {
      setError(null);
    }, [resultData]);

    return (
      <div className="relative h-full min-h-[600px] w-full overflow-hidden bg-slate-950">
        <Canvas
          shadows
          dpr={[1, 2]}
          gl={{ antialias: true, powerPreference: "high-performance" }}
          camera={{ position: [0, 2.5, 5], fov: 60, near: 0.1, far: 1000 }}
        >
          <color attach="background" args={["#0b1117"]} />
          <fog attach="fog" args={["#0b1117", 32, 80]} />

          <ambientLight intensity={0.55} />
          <hemisphereLight intensity={0.45} groundColor="#5f6b58" />
          <directionalLight
            castShadow
            position={[12, 18, 10]}
            intensity={1.25}
            shadow-mapSize={[2048, 2048]}
          />

          <GroundGrid terrainSize={TERRAIN_SIZE} />

          <TerrainMesh
            resultData={resultData}
            verticalExaggeration={verticalExaggeration}
            textureMode={textureMode}
            onError={setError}
          />

          <TerrainCamera
            ref={ref}
            mode={cameraMode}
            resetSignal={resetSignal}
          />
        </Canvas>

        {error && (
          <div className="absolute inset-x-4 bottom-4 rounded-xl border border-red-200 bg-white/95 p-4 shadow-lg backdrop-blur">
            <p className="text-sm font-semibold text-red-700">Terrain generation failed</p>
            <p className="mt-1 text-xs leading-5 text-gray-600">{error}</p>
          </div>
        )}
      </div>
    );
  },
);

TerrainViewer.displayName = "TerrainViewer";

export default TerrainViewer;
