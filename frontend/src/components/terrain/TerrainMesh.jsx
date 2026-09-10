import React, { useEffect, useState } from "react";
import * as THREE from "three";

import { getHeightData } from "../../utils/getHeightData";
import { createTerrainGeometry } from "../../utils/terrainUtils";
import { loadTextureFromBase64 } from "../../utils/textureUtils";

const TerrainMesh = ({ resultData, verticalExaggeration = 0.5, onError }) => {
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

    if (!resultData?.texture_png_b64) {
      return undefined;
    }

    loadTextureFromBase64(resultData.texture_png_b64)
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
  }, [resultData, onError]);

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
      <meshStandardMaterial
        map={texture || undefined}
        color={texture ? "#ffffff" : "#8fa56b"}
        roughness={0.92}
        metalness={0}
        side={THREE.DoubleSide}
      />
    </mesh>
  );
};

export default TerrainMesh;
