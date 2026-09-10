import React from "react";
import { Minus, Plus, RotateCcw, Maximize2 } from "lucide-react";

const ViewerControls = ({
  cameraMode,
  setCameraMode,
  verticalExaggeration,
  setVerticalExaggeration,
  onResetView,
}) => {
  const handleFullscreen = () => {
    // Find the nearest parent that contains the 3D canvas.
    // This allows fullscreen without changing the parent component.
    const button = document.activeElement;

    let target = button;

    while (target && target.parentElement) {
      if (target.querySelector("canvas")) {
        break;
      }
      target = target.parentElement;
    }

    if (!target || !target.querySelector("canvas")) {
      target = document.querySelector("canvas")?.parentElement;
    }

    if (!target) return;

    if (!document.fullscreenElement) {
      target.requestFullscreen?.();
    } else {
      document.exitFullscreen?.();
    }
  };

  return (
    <div className="absolute top-4 left-4 z-50 flex flex-col gap-3">
      {/* Camera Modes */}
      <div className="flex items-center gap-1 rounded-xl bg-white/95 p-1 shadow-lg backdrop-blur-md">
        {[
          { id: "orbit", label: "Orbit" },
          { id: "flythrough", label: "Flythrough" },
          { id: "top", label: "Top" },
        ].map((mode) => (
          <button
            key={mode.id}
            onClick={() => setCameraMode(mode.id)}
            className={`
              rounded-lg px-3 py-2 text-sm font-medium transition-all
              ${
                cameraMode === mode.id
                  ? "bg-black text-white shadow"
                  : "text-gray-700 hover:bg-gray-100"
              }
            `}
          >
            {mode.label}
          </button>
        ))}
      </div>

      {/* Vertical Exaggeration */}
      <div className="w-56 rounded-xl bg-white/95 p-4 shadow-lg backdrop-blur-md">
        <div className="mb-2 flex items-center justify-between">
          <span className="text-xs font-semibold text-gray-700">
            Height Exaggeration
          </span>

          <span className="text-xs font-bold text-gray-900">
            {verticalExaggeration.toFixed(1)}x
          </span>
        </div>

        <div className="flex items-center gap-2">
          <Minus size={14} className="text-gray-500" />

          <input
            type="range"
            min="0.5"
            max="5"
            step="0.1"
            value={verticalExaggeration}
            onChange={(e) => setVerticalExaggeration(Number(e.target.value))}
            className="w-full cursor-pointer accent-black"
          />

          <Plus size={14} className="text-gray-500" />
        </div>
      </div>

      {/* Bottom Controls */}
      <div className="flex gap-2">
        {/* Reset */}
        <button
          onClick={onResetView}
          title="Reset View"
          className="
            flex items-center gap-2 rounded-xl
            bg-white/95 px-3 py-2
            text-sm font-medium text-gray-800
            shadow-lg backdrop-blur-md
            transition hover:bg-white
          "
        >
          <RotateCcw size={16} />
          Reset
        </button>

        {/* Fullscreen */}
        <button
          onClick={handleFullscreen}
          title="Fullscreen"
          className="
            flex items-center justify-center
            rounded-xl bg-white/95 p-2
            text-gray-800 shadow-lg
            backdrop-blur-md
            transition hover:bg-white
          "
        >
          <Maximize2 size={18} />
        </button>
      </div>

      {/* Flythrough Help */}
      {cameraMode === "flythrough" && (
        <div
          className="
            max-w-xs rounded-xl
            bg-black/75 px-4 py-3
            text-xs leading-5 text-white
            shadow-xl backdrop-blur-md
          "
        >
          <div className="mb-1 font-semibold text-white">
            Street View Controls
          </div>

          <div className="text-white/80">
            <b>W / ↑</b> Forward
            <br />
            <b>S / ↓</b> Backward
            <br />
            <b>A / ←</b> Left
            <br />
            <b>D / →</b> Right
            <br />
            <b>Q / E</b> Down / Up
            <br />
            <b>Shift</b> Fast Movement
            <br />
            <b>Mouse Drag</b> Look Around
            <br />
            <b>Scroll</b> Move Forward / Back
          </div>
        </div>
      )}
    </div>
  );
};

export default ViewerControls;
