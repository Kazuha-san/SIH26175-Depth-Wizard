import React from "react";
import { Maximize2, Minus, Plus, RotateCcw } from "lucide-react";

const ViewerControls = ({
  cameraMode,
  setCameraMode,
  verticalExaggeration,
  setVerticalExaggeration,
  onResetView,
  textureMode,
  setTextureMode,
  hasConfidence,
}) => {
  const handleFullscreen = async (event) => {
    const viewer = event.currentTarget.closest("[data-terrain-viewer]");

    if (!viewer) return;

    try {
      if (!document.fullscreenElement) {
        await viewer.requestFullscreen();
      } else {
        await document.exitFullscreen();
      }
    } catch (error) {
      console.error("Unable to toggle terrain fullscreen:", error);
    }
  };

  return (
    <div className="pointer-events-none absolute inset-0 z-20">
      {/* Primary viewer controls */}
      <div className="pointer-events-auto absolute left-4 top-4 flex flex-col gap-2">
        <div className="flex w-fit items-center gap-1 rounded-xl border border-white/70 bg-white/95 p-1 shadow-lg backdrop-blur-md">
          {["orbit", "flythrough", "top"].map((mode) => (
            <button
              key={mode}
              type="button"
              onClick={() => setCameraMode(mode)}
              className={`rounded-lg px-3 py-2 text-xs font-semibold transition ${
                cameraMode === mode
                  ? "bg-gray-950 text-white shadow-sm"
                  : "text-gray-600 hover:bg-gray-100 hover:text-gray-950"
              }`}
            >
              {mode === "flythrough" ? "Flythrough" : mode === "orbit" ? "Orbit" : "Top"}
            </button>
          ))}
        </div>

        <div className="w-60 rounded-xl border border-white/70 bg-white/95 p-3 shadow-lg backdrop-blur-md">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-xs font-semibold text-gray-700">
              Height Exaggeration
            </span>
            <span className="text-xs font-bold text-gray-950">
              {verticalExaggeration.toFixed(1)}x
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              aria-label="Decrease height exaggeration"
              onClick={() =>
                setVerticalExaggeration((value) =>
                  Math.max(0.5, Number((value - 0.1).toFixed(1)))
                )
              }
              className="rounded-md p-1 text-gray-500 hover:bg-gray-100"
            >
              <Minus size={14} />
            </button>

            <input
              type="range"
              min="0.5"
              max="5"
              step="0.1"
              value={verticalExaggeration}
              onChange={(event) =>
                setVerticalExaggeration(Number(event.target.value))
              }
              aria-label="Height exaggeration"
              className="w-full cursor-pointer accent-gray-950"
            />

            <button
              type="button"
              aria-label="Increase height exaggeration"
              onClick={() =>
                setVerticalExaggeration((value) =>
                  Math.min(5, Number((value + 0.1).toFixed(1))),
                )
              }
              className="rounded-md p-1 text-gray-500 hover:bg-gray-100"
            >
              <Plus size={14} />
            </button>
          </div>
        </div>

        {hasConfidence && (
          <div className="flex w-fit items-center gap-1 rounded-xl border border-white/70 bg-white/95 p-1 shadow-lg backdrop-blur-md">
            {[
              { key: "rgb", label: "Imagery" },
              { key: "confidence", label: "Confidence" },
            ].map(({ key, label }) => (
              <button
                key={key}
                type="button"
                onClick={() => setTextureMode(key)}
                className={`rounded-lg px-3 py-2 text-xs font-semibold transition ${
                  textureMode === key
                    ? "bg-gray-950 text-white shadow-sm"
                    : "text-gray-600 hover:bg-gray-100 hover:text-gray-950"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Viewer actions */}
      <div className="pointer-events-auto absolute bottom-4 right-4 flex items-center gap-2">
        <button
          type="button"
          onClick={onResetView}
          className="flex items-center gap-2 rounded-xl border border-white/70 bg-white/95 px-3 py-2 text-sm font-semibold text-gray-800 shadow-lg backdrop-blur-md transition hover:bg-white"
        >
          <RotateCcw size={16} />
          Reset
        </button>

        <button
          type="button"
          onClick={handleFullscreen}
          title="Fullscreen"
          aria-label="Toggle fullscreen"
          className="flex h-9 w-9 items-center justify-center rounded-xl border border-white/70 bg-white/95 text-gray-800 shadow-lg backdrop-blur-md transition hover:bg-white"
        >
          <Maximize2 size={17} />
        </button>
      </div>

      {/* Confidence legend (suppressed in flythrough mode -- same corner as the flythrough help panel) */}
      {textureMode === "confidence" && cameraMode !== "flythrough" && (
        <div className="pointer-events-none absolute bottom-4 left-4 max-w-xs rounded-xl border border-white/10 bg-gray-950/80 px-4 py-3 text-xs leading-5 text-white shadow-xl backdrop-blur-md">
          <div className="mb-2 font-semibold">Elevation Confidence</div>
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full" style={{ backgroundColor: "#ef4444" }} />
            <span className="text-white/75">Low confidence</span>
          </div>
          <div className="mt-1 flex items-center gap-2">
            <span className="h-2 w-2 rounded-full" style={{ backgroundColor: "#facc15" }} />
            <span className="text-white/75">Medium</span>
          </div>
          <div className="mt-1 flex items-center gap-2">
            <span className="h-2 w-2 rounded-full" style={{ backgroundColor: "#22c55e" }} />
            <span className="text-white/75">High confidence</span>
          </div>
        </div>
      )}

      {/* Flythrough help */}
      {cameraMode === "flythrough" && (
        <div className="pointer-events-none absolute bottom-4 left-4 max-w-xs rounded-xl border border-white/10 bg-gray-950/80 px-4 py-3 text-xs leading-5 text-white shadow-xl backdrop-blur-md">
          <div className="mb-1 font-semibold">Flythrough</div>
          <div className="text-white/75">
            <b>WASD / Arrow keys</b> Move
            <br />
            <b>Q / E</b> Down / Up
            <br />
            <b>Shift</b> Fast movement
            <br />
            <b>Drag</b> Look around
          </div>
        </div>
      )}
    </div>
  );
};

export default ViewerControls;
