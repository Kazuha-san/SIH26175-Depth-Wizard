import React from "react";
import { Maximize2, Minus, Plus, RotateCcw } from "lucide-react";

/**
 * Static left-rail controls (camera mode, height exaggeration, imagery/
 * confidence toggle, reset, fullscreen) -- previously an absolute-
 * positioned overlay floating on top of the viewer; now docked in
 * ResultsView's left column per the "map control & options" panel in the
 * layout brief. Same state/handlers as before, just a plain block
 * layout instead of pointer-events-auto/absolute positioning.
 */
export const ViewerRailControls = ({
  cameraMode,
  setCameraMode,
  verticalExaggeration,
  setVerticalExaggeration,
  onResetView,
  textureMode,
  setTextureMode,
  hasConfidence,
}) => {
  const handleFullscreen = async () => {
    const viewer = document.querySelector("[data-terrain-viewer]");
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
    <div className="flex flex-col gap-4">
      <div>
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-soft">
          Camera
        </p>
        <div className="flex w-full items-center gap-1 rounded-xl border border-gray-100 bg-surface p-1">
          {["orbit", "flythrough", "top"].map((mode) => (
            <button
              key={mode}
              type="button"
              onClick={() => setCameraMode(mode)}
              className={`flex-1 rounded-lg px-3 py-2 text-xs font-semibold transition ${
                cameraMode === mode
                  ? "bg-white text-ink shadow-sm"
                  : "text-ink-soft hover:text-ink"
              }`}
            >
              {mode === "flythrough" ? "Fly" : mode === "orbit" ? "Orbit" : "Top"}
            </button>
          ))}
        </div>
      </div>

      <div>
        <div className="mb-2 flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-wide text-ink-soft">
            Height exaggeration
          </span>
          <span className="text-xs font-bold text-ink">
            {verticalExaggeration.toFixed(1)}x
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            aria-label="Decrease height exaggeration"
            onClick={() =>
              setVerticalExaggeration((value) =>
                Math.max(0.5, Number((value - 0.1).toFixed(1))),
              )
            }
            className="rounded-md p-1 text-ink-soft hover:bg-surface"
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
            className="w-full cursor-pointer accent-blue-deep"
          />

          <button
            type="button"
            aria-label="Increase height exaggeration"
            onClick={() =>
              setVerticalExaggeration((value) =>
                Math.min(5, Number((value + 0.1).toFixed(1))),
              )
            }
            className="rounded-md p-1 text-ink-soft hover:bg-surface"
          >
            <Plus size={14} />
          </button>
        </div>
      </div>

      {hasConfidence && (
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-soft">
            Layer
          </p>
          <div className="flex w-full items-center gap-1 rounded-xl border border-gray-100 bg-surface p-1">
            {[
              { key: "rgb", label: "Imagery" },
              { key: "confidence", label: "Confidence" },
            ].map(({ key, label }) => (
              <button
                key={key}
                type="button"
                onClick={() => setTextureMode(key)}
                className={`flex-1 rounded-lg px-3 py-2 text-xs font-semibold transition ${
                  textureMode === key
                    ? "bg-white text-ink shadow-sm"
                    : "text-ink-soft hover:text-ink"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="mt-1 flex gap-2 border-t border-gray-100 pt-4">
        <button
          type="button"
          onClick={onResetView}
          className="flex flex-1 items-center justify-center gap-2 rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm font-semibold text-ink transition hover:bg-surface"
        >
          <RotateCcw size={15} />
          Reset
        </button>

        <button
          type="button"
          onClick={handleFullscreen}
          title="Fullscreen"
          aria-label="Toggle fullscreen"
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-gray-200 bg-white text-ink transition hover:bg-surface"
        >
          <Maximize2 size={16} />
        </button>
      </div>
    </div>
  );
};

/**
 * Floating overlays that make sense ON TOP of the 3D canvas itself
 * (contextual, tied to what's currently on screen) -- confidence legend
 * and flythrough key hints. Camera/exaggeration/layer/reset controls live
 * in ViewerRailControls (the static left rail) instead.
 */
const ViewerControls = ({ cameraMode, textureMode }) => {
  return (
    <div className="pointer-events-none absolute inset-0 z-20">
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
