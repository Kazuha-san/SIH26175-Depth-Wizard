import React, { forwardRef, useEffect, useImperativeHandle, useRef } from "react";
import { OrbitControls } from "@react-three/drei";
import { useThree } from "@react-three/fiber";
import * as THREE from "three";

import FlythroughControls from "./FlythroughControls";

const INITIAL_POSITION = new THREE.Vector3(0, 4.5, 8.5);
const INITIAL_TARGET = new THREE.Vector3(0, 1.2, 0);

const TerrainCamera = forwardRef(
  ({ mode = "orbit", resetSignal = 0 }, ref) => {
    const { camera } = useThree();
    const orbitRef = useRef(null);

    const resetCamera = () => {
      camera.position.copy(
        mode === "top" ? new THREE.Vector3(0, 14, 0) : INITIAL_POSITION,
      );
      camera.up.set(0, 1, 0);
      camera.rotation.order = "YXZ";
      camera.lookAt(INITIAL_TARGET);

      if (orbitRef.current) {
        orbitRef.current.target.copy(INITIAL_TARGET);
        orbitRef.current.update();
      }
    };

    useImperativeHandle(
      ref,
      () => ({
        reset: resetCamera,
        camera,
      }),
      [camera],
    );

    useEffect(() => {
      resetCamera();
    }, [mode, resetSignal]);

    if (mode === "flythrough") {
      return (
        <FlythroughControls
          enabled
          resetSignal={resetSignal}
        />
      );
    }

    return (
      <OrbitControls
        ref={orbitRef}
        enableDamping
        dampingFactor={0.08}
        enableRotate={mode !== "top"}
        minDistance={2}
        maxDistance={24}
        maxPolarAngle={mode === "top" ? Math.PI / 2.02 : Math.PI * 0.49}
        target={INITIAL_TARGET}
      />
    );
  },
);

TerrainCamera.displayName = "TerrainCamera";

export default TerrainCamera;
