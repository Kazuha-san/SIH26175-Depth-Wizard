import React, { useEffect, useState } from "react";
import * as THREE from "three";

import { getHeightData } from "../../utils/getHeightData";
import { createTerrainGeometry } from "../../utils/terrainUtils";
import { loadTextureFromBase64 } from "../../utils/textureUtils";

const TerrainMesh = ({ resultData, verticalExaggeration = 0.5, onError }) => {
  const [geometry, setGeometry] = useState(null);
  const [texture, setTexture] = useState(null);

  useEffect(() => {
    let disposed = false;
    let nextGeometry = null;

    try {
      if (!resultData) throw new Error("Terrain result data is missing.");

      const heightData = getHeightData(
        resultData.heightmap_png_b64,
        resultData.height_min,
        resultData.height_max,
      );

      nextGeometry = createTerrainGeometry({
        ...heightData,
        verticalExaggeration,
      });

      if (disposed) {
        nextGeometry.dispose();
        return undefined;
      }

      setGeometry((previous) => {
        previous?.dispose();
        return nextGeometry;
      });
    } catch (error) {
      console.error("Terrain generation error:", error);
      if (!disposed) {
        setGeometry((previous) => {
          previous?.dispose();
          return null;
        });
        onError?.(error instanceof Error ? error.message : "Unable to generate terrain.");
      }
    }

    return () => {
      disposed = true;
    };
  }, [resultData, verticalExaggeration, onError]);

  useEffect(() => {
    let disposed = false;
    let nextTexture = null;

    setTexture((previous) => {
      previous?.dispose();
      return null;
    });

    if (!resultData?.texture_png_b64) return undefined;

    loadTextureFromBase64(resultData.texture_png_b64)
      .then((loadedTexture) => {
        if (disposed) {
          loadedTexture.dispose();
          return;
        }

        nextTexture = loadedTexture;
        setTexture(loadedTexture);
      })
      .catch((error) => {
        if (!disposed) {
          console.warn("Terrain texture could not be loaded:", error);
        }
      });

    return () => {
      disposed = true;
      nextTexture?.dispose();
    };
  }, [resultData]);

  useEffect(() => () => {
    geometry?.dispose();
    texture?.dispose();
  }, [geometry, texture]);

  if (!geometry) return null;

  return (
    <mesh
      geometry={geometry}
      rotation={[-Math.PI / 2, 0, 0]}
      castShadow
      receiveShadow
    >
      <meshStandardMaterial
        map={texture}
        color={texture ? "#ffffff" : "#8fa56b"}
        roughness={0.95}
        metalness={0}
        side={THREE.DoubleSide}
      />
    </mesh>
  );
};

export default TerrainMesh;
