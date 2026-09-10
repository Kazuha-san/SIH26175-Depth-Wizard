import { useEffect, useRef } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";

const MOVE_SPEED = 4;
const FAST_MOVE_MULTIPLIER = 2.5;
const LOOK_SENSITIVITY = 0.0025;
const MIN_HEIGHT = 1.35;
const TERRAIN_HALF_SIZE = 5.65;

const MOVEMENT_KEYS = new Set([
  "KeyW",
  "KeyA",
  "KeyS",
  "KeyD",
  "ArrowUp",
  "ArrowDown",
  "ArrowLeft",
  "ArrowRight",
  "KeyQ",
  "KeyE",
  "ShiftLeft",
  "ShiftRight",
]);

const FlythroughControls = ({ enabled = false, resetSignal = 0 }) => {
  const { camera, gl } = useThree();
  const keysRef = useRef(new Set());
  const draggingRef = useRef(false);
  const previousPointerRef = useRef({ x: 0, y: 0 });
  const yawRef = useRef(0);
  const pitchRef = useRef(-0.08);

  const resetOrientation = () => {
    camera.rotation.order = "YXZ";
    yawRef.current = 0;
    pitchRef.current = -0.08;
    camera.rotation.set(pitchRef.current, yawRef.current, 0);
  };

  useEffect(() => {
    if (!enabled) {
      keysRef.current.clear();
      draggingRef.current = false;
      return undefined;
    }

    const element = gl.domElement;

    const handleKeyDown = (event) => {
      if (!MOVEMENT_KEYS.has(event.code)) return;

      event.preventDefault();
      keysRef.current.add(event.code);
    };

    const handleKeyUp = (event) => {
      keysRef.current.delete(event.code);
    };

    const handleWindowBlur = () => {
      keysRef.current.clear();
      draggingRef.current = false;
    };

    const handlePointerDown = (event) => {
      if (event.button !== 0) return;

      draggingRef.current = true;
      previousPointerRef.current = {
        x: event.clientX,
        y: event.clientY,
      };
      element.style.cursor = "grabbing";
      element.setPointerCapture?.(event.pointerId);
    };

    const handlePointerMove = (event) => {
      if (!draggingRef.current) return;

      const previous = previousPointerRef.current;
      const deltaX = event.clientX - previous.x;
      const deltaY = event.clientY - previous.y;

      previousPointerRef.current = {
        x: event.clientX,
        y: event.clientY,
      };

      yawRef.current -= deltaX * LOOK_SENSITIVITY;
      pitchRef.current -= deltaY * LOOK_SENSITIVITY;
      pitchRef.current = THREE.MathUtils.clamp(
        pitchRef.current,
        -Math.PI / 2 + 0.08,
        Math.PI / 2 - 0.08,
      );

      camera.rotation.set(pitchRef.current, yawRef.current, 0);
    };

    const stopDragging = (event) => {
      draggingRef.current = false;
      element.style.cursor = "grab";

      if (event?.pointerId != null) {
        try {
          element.releasePointerCapture?.(event.pointerId);
        } catch {
          // Pointer capture may already have been released.
        }
      }
    };

    element.style.cursor = "grab";
    element.addEventListener("pointerdown", handlePointerDown);
    element.addEventListener("pointermove", handlePointerMove);
    element.addEventListener("pointerup", stopDragging);
    element.addEventListener("pointercancel", stopDragging);
    window.addEventListener("keydown", handleKeyDown, { passive: false });
    window.addEventListener("keyup", handleKeyUp);
    window.addEventListener("blur", handleWindowBlur);

    return () => {
      element.style.cursor = "";
      element.removeEventListener("pointerdown", handlePointerDown);
      element.removeEventListener("pointermove", handlePointerMove);
      element.removeEventListener("pointerup", stopDragging);
      element.removeEventListener("pointercancel", stopDragging);
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("keyup", handleKeyUp);
      window.removeEventListener("blur", handleWindowBlur);
      keysRef.current.clear();
      draggingRef.current = false;
    };
  }, [camera, gl, enabled]);

  useEffect(() => {
    if (!enabled) return;
    resetOrientation();
  }, [enabled, resetSignal]);

  useFrame((_, delta) => {
    if (!enabled) return;

    const keys = keysRef.current;
    const forward = new THREE.Vector3();
    const right = new THREE.Vector3();
    const movement = new THREE.Vector3();

    camera.getWorldDirection(forward);
    forward.y = 0;

    if (forward.lengthSq() > 0) {
      forward.normalize();
      right.crossVectors(forward, camera.up).normalize();
    }

    if (keys.has("KeyW") || keys.has("ArrowUp")) movement.add(forward);
    if (keys.has("KeyS") || keys.has("ArrowDown")) movement.sub(forward);
    if (keys.has("KeyD") || keys.has("ArrowRight")) movement.add(right);
    if (keys.has("KeyA") || keys.has("ArrowLeft")) movement.sub(right);

    if (keys.has("KeyE")) movement.y += 1;
    if (keys.has("KeyQ")) movement.y -= 1;

    if (movement.lengthSq() === 0) return;

    const speed = MOVE_SPEED *
      (keys.has("ShiftLeft") || keys.has("ShiftRight")
        ? FAST_MOVE_MULTIPLIER
        : 1);

    movement.normalize().multiplyScalar(speed * delta);
    camera.position.add(movement);

    camera.position.x = THREE.MathUtils.clamp(
      camera.position.x,
      -TERRAIN_HALF_SIZE,
      TERRAIN_HALF_SIZE,
    );
    camera.position.z = THREE.MathUtils.clamp(
      camera.position.z,
      -TERRAIN_HALF_SIZE,
      TERRAIN_HALF_SIZE,
    );
    camera.position.y = Math.max(MIN_HEIGHT, camera.position.y);
  });

  return null;
};

export default FlythroughControls;
