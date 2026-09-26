import React, { useEffect, useState } from "react";
import * as THREE from "three";

import { getHeightData } from "../../utils/getHeightData";
import { createTerrainGeometry } from "../../utils/terrainUtils";
import { loadConfidenceTextureFromBase64 } from "../../utils/textureUtils";

const TerrainMesh = ({ resultData, verticalExaggeration = 0.5, textureMode = "elevation", onError }) => {
  const [geometry, setGeometry] = useState(null);
  const [texture, setTexture] = useState(null);

  useEffect(() => {
    let cancelled = false;
    let createdGeometry = null;

    try {
      if (!resultData) {
        throw new Error("Terrain result data is missing.");
      }

      const heightData = getHeightData(
        resultData.heightmap_png_b64,
        resultData.height_min,
        resultData.height_max,
      );

      createdGeometry = createTerrainGeometry({
        ...heightData,
        verticalExaggeration,
      });

      if (cancelled) {
        createdGeometry.dispose();
        return undefined;
      }

      setGeometry((previousGeometry) => {
        previousGeometry?.dispose();
        return createdGeometry;
      });
    } catch (error) {
      console.error("Terrain geometry generation failed:", error);

      if (!cancelled) {
        setGeometry((previousGeometry) => {
          previousGeometry?.dispose();
          return null;
        });
        onError?.(
          error instanceof Error
            ? error.message
            : "Unable to generate the terrain geometry.",
        );
      }
    }

    return () => {
      cancelled = true;
    };
  }, [resultData, verticalExaggeration, onError]);

  useEffect(() => {
    let cancelled = false;
    let createdTexture = null;

    setTexture((previousTexture) => {
      previousTexture?.dispose();
      return null;
    });

    // Elevation mode uses per-vertex colors baked into the geometry itself
    // (see terrainUtils.createTerrainGeometry) -- no texture to load.
    // Solid mode is a flat, untextured structural view (single tint,
    // flat-shaded so slanted vs flat roofs catch light differently) --
    // also no texture to load.
    if (textureMode === "elevation" || textureMode === "solid") {
      return undefined;
    }

    // Elevation, Solid, and Confidence are the only remaining modes --
    // the RGB/Imagery drape was dropped (looked stretched/ugly on
    // non-georeferenced crops and didn't distinguish buildings from
    // vegetation, per judge feedback). This branch only ever runs for
    // "confidence" now.
    const base64 = resultData?.confidence_png_b64;

    if (!base64) {
      onError?.(
        "No confidence data available for this result (uncertainty pass wasn't run).",
      );
      return undefined;
    }

    loadConfidenceTextureFromBase64(base64)
      .then((loadedTexture) => {
        if (cancelled) {
          loadedTexture.dispose();
          return;
        }

        createdTexture = loadedTexture;
        setTexture(loadedTexture);
      })
      .catch((error) => {
        if (!cancelled) {
          console.error("Terrain texture loading failed:", error);
          onError?.(
            error instanceof Error
              ? `Terrain texture could not be loaded: ${error.message}`
              : "Terrain texture could not be loaded.",
          );
        }
      });

    return () => {
      cancelled = true;
      createdTexture?.dispose();
    };
  }, [resultData, textureMode, onError]);

  useEffect(() => {
    return () => {
      geometry?.dispose();
    };
  }, [geometry]);

  useEffect(() => {
    return () => {
      texture?.dispose();
    };
  }, [texture]);

  if (!geometry) {
    return null;
  }

  return (
    <mesh
      geometry={geometry}
      rotation={[-Math.PI / 2, 0, 0]}
      castShadow
      receiveShadow
    >
      {/* key={textureMode} forces a fresh material instance on mode switch --
          flatShading is a shader-recompile flag that React Three Fiber
          won't pick up on a prop change to an existing material instance
          (it needs material.needsUpdate = true), so remounting avoids that
          gotcha entirely. */}
      <meshStandardMaterial
        key={`${textureMode}-${texture ? "textured" : "untextured"}`}
        map={
          textureMode === "elevation" || textureMode === "solid"
            ? undefined
            : texture || undefined
        }
        vertexColors={textureMode === "elevation"}
        flatShading={textureMode === "solid"}
        color={
          textureMode === "elevation"
            ? "#ffffff"
            : textureMode === "solid"
              ? "#a9c2d9"
              : texture
                ? "#ffffff"
                : "#4c1d95"
        }
        roughness={textureMode === "solid" ? 0.65 : 0.92}
        metalness={0}
        side={THREE.DoubleSide}
      />
    </mesh>
  );
};

export default TerrainMesh;
