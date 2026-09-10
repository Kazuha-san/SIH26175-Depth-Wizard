import React, {
  forwardRef,
  useEffect,
  useImperativeHandle,
  useRef,
} from "react";
import { OrbitControls, PointerLockControls } from "@react-three/drei";
import { useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";

const INITIAL_POSITION = new THREE.Vector3(0, 3.5, 8);
const INITIAL_TARGET = new THREE.Vector3(0, 0, 0);
const TERRAIN_HALF_SIZE = 6;
const FLY_HEIGHT = 1.8;
const MOVE_SPEED = 4;

const TerrainCamera = forwardRef(({ mode = "orbit", resetSignal = 0 }, ref) => {
  const { camera } = useThree();
  const orbitRef = useRef(null);
  const pointerLockRef = useRef(null);
  const keysRef = useRef(new Set());

  const resetCamera = () => {
    camera.position.copy(INITIAL_POSITION);
    camera.up.set(0, 1, 0);
    camera.lookAt(INITIAL_TARGET);

    if (orbitRef.current) {
      orbitRef.current.target.copy(INITIAL_TARGET);
      orbitRef.current.update();
    }
  };

  useImperativeHandle(ref, () => ({
    reset: resetCamera,
    camera,
  }), [camera]);

  useEffect(() => {
    resetCamera();
  }, [mode, resetSignal]);

  useEffect(() => {
    if (mode !== "flythrough") return undefined;

    const handleKeyDown = (event) => {
      const movementKeys = ["KeyW", "KeyA", "KeyS", "KeyD", "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"];

      if (!movementKeys.includes(event.code)) return;

      event.preventDefault();
      keysRef.current.add(event.code);
    };

    const handleKeyUp = (event) => {
      keysRef.current.delete(event.code);
    };

    window.addEventListener("keydown", handleKeyDown, { passive: false });
    window.addEventListener("keyup", handleKeyUp);

    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("keyup", handleKeyUp);
      keysRef.current.clear();
    };
  }, [mode]);

  useFrame((_, delta) => {
    if (mode !== "flythrough" || !pointerLockRef.current?.isLocked) return;

    const keys = keysRef.current;
    const direction = new THREE.Vector3();
    const right = new THREE.Vector3();

    camera.getWorldDirection(direction);
    direction.y = 0;

    if (direction.lengthSq() > 0) {
      direction.normalize();
      right.crossVectors(direction, camera.up).normalize();
    }

    const movement = new THREE.Vector3();

    if (keys.has("KeyW") || keys.has("ArrowUp")) movement.add(direction);
    if (keys.has("KeyS") || keys.has("ArrowDown")) movement.sub(direction);
    if (keys.has("KeyD") || keys.has("ArrowRight")) movement.add(right);
    if (keys.has("KeyA") || keys.has("ArrowLeft")) movement.sub(right);

    if (movement.lengthSq() === 0) return;

    movement.normalize().multiplyScalar(MOVE_SPEED * delta);
    camera.position.add(movement);

    camera.position.x = THREE.MathUtils.clamp(
      camera.position.x,
      -TERRAIN_HALF_SIZE + 0.35,
      TERRAIN_HALF_SIZE - 0.35,
    );
    camera.position.z = THREE.MathUtils.clamp(
      camera.position.z,
      -TERRAIN_HALF_SIZE + 0.35,
      TERRAIN_HALF_SIZE - 0.35,
    );
    camera.position.y = Math.max(FLY_HEIGHT, camera.position.y);
  });

  if (mode === "top") {
    return (
      <OrbitControls
        ref={orbitRef}
        enableRotate={false}
        enableDamping
        minDistance={2}
        maxDistance={25}
        target={INITIAL_TARGET}
      />
    );
  }

  if (mode === "flythrough") {
    return <PointerLockControls ref={pointerLockRef} />;
  }

  return (
    <OrbitControls
      ref={orbitRef}
      enableDamping
      dampingFactor={0.08}
      minDistance={2}
      maxDistance={25}
      maxPolarAngle={Math.PI * 0.49}
      target={INITIAL_TARGET}
    />
  );
});

TerrainCamera.displayName = "TerrainCamera";

export default TerrainCamera;
