import React from "react";
import { Minimize2, Minus, Maximize2, Plus } from "lucide-react";

import { ELEVATION_STOPS } from "../utils/terrainUtils";

/**
 * Floating view-controls card -- sits directly on top of the 3D viewport
 * (top-right) instead of taking a dedicated layout column. The viewport
 * itself now goes edge-to-edge; only the right info panel is a "real"
 * sidebar. Dark/translucent to match the other overlay chrome (Input
 * type badge, legends) since it now lives over the black canvas.
 *
 * Reset was dropped (redundant, wasn't adding anything users found
 * useful). Fullscreen now swaps its icon to Minimize2 when active, since
 * a Maximize2 icon in both states gave no way to tell how to get back out.
 */
export const ViewerRailControls = ({
  cameraMode,
  setCameraMode,
  verticalExaggeration,
  setVerticalExaggeration,
  textureMode,
  setTextureMode,
  hasConfidence,
  isFullscreen,
  onToggleFullscreen,
}) => {
  return (
    <div className="pointer-events-auto absolute right-4 top-4 z-30 w-64 rounded-2xl border border-white/10 bg-gray-950/85 p-4 text-white shadow-xl backdrop-blur-md">
      <div className="mb-3 flex items-center justify-between">
        <p className="text-xs font-semibold uppercase tracking-wide text-white/50">
          View controls
        </p>
        <button
          type="button"
          onClick={onToggleFullscreen}
          title={isFullscreen ? "Exit fullscreen" : "Fullscreen"}
          aria-label={isFullscreen ? "Exit fullscreen" : "Toggle fullscreen"}
          className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-white/10 bg-white/5 text-white/80 transition hover:bg-white/10 hover:text-white"
        >
          {isFullscreen ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
        </button>
      </div>

      <div className="flex flex-col gap-4">
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-white/50">
            Camera
          </p>
          <div className="flex w-full items-center gap-1 rounded-xl border border-white/10 bg-white/5 p-1">
            {["orbit", "flythrough", "top"].map((mode) => (
              <button
                key={mode}
                type="button"
                onClick={() => setCameraMode(mode)}
                className={`flex-1 rounded-lg px-2 py-1.5 text-xs font-semibold transition ${
                  cameraMode === mode
                    ? "bg-white text-ink shadow-sm"
                    : "text-white/60 hover:text-white"
                }`}
              >
                {mode === "flythrough" ? "Fly" : mode === "orbit" ? "Orbit" : "Top"}
              </button>
            ))}
          </div>
        </div>

        <div>
          <div className="mb-2 flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wide text-white/50">
              Height exaggeration
            </span>
            <span className="text-xs font-bold text-white">
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
              className="rounded-md p-1 text-white/60 hover:bg-white/10 hover:text-white"
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
              className="w-full cursor-pointer accent-blue-400"
            />

            <button
              type="button"
              aria-label="Increase height exaggeration"
              onClick={() =>
                setVerticalExaggeration((value) =>
                  Math.min(5, Number((value + 0.1).toFixed(1))),
                )
              }
              className="rounded-md p-1 text-white/60 hover:bg-white/10 hover:text-white"
            >
              <Plus size={14} />
            </button>
          </div>
        </div>

        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-white/50">
            Layer
          </p>
          <div className="flex w-full items-center gap-1 rounded-xl border border-white/10 bg-white/5 p-1">
            {[
              { key: "elevation", label: "Elevation" },
              { key: "solid", label: "Solid" },
              ...(hasConfidence ? [{ key: "confidence", label: "Confidence" }] : []),
            ].map(({ key, label }) => (
              <button
                key={key}
                type="button"
                onClick={() => setTextureMode(key)}
                className={`flex-1 rounded-lg px-2 py-1.5 text-xs font-semibold transition ${
                  textureMode === key
                    ? "bg-white text-ink shadow-sm"
                    : "text-white/60 hover:text-white"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

const rgbCss = ([r, g, b]) =>
  `rgb(${Math.round(r * 255)}, ${Math.round(g * 255)}, ${Math.round(b * 255)})`;

// Built once from the SAME stops the 3D mesh colors vertices with
// (terrainUtils.ELEVATION_STOPS) so the legend gradient and tick values
// can never drift out of sync with what's actually on the terrain.
const ELEVATION_GRADIENT_CSS = `linear-gradient(to top, ${ELEVATION_STOPS.map(
  (stop) => `${rgbCss(stop.color)} ${(stop.t * 100).toFixed(0)}%`,
).join(", ")})`;

/**
 * Floating overlays that make sense ON TOP of the 3D canvas itself
 * (contextual, tied to what's currently on screen) -- elevation scale
 * legend, confidence legend, and flythrough key hints. Camera/
 * exaggeration/layer live in ViewerRailControls (the floating top-right
 * card) instead.
 */
const ViewerControls = ({ cameraMode, textureMode, heightMin, heightMax, heightUnits }) => {
  const min = Number.isFinite(heightMin) ? heightMin : 0;
  const max = Number.isFinite(heightMax) ? heightMax : 1;
  const unitSuffix = heightUnits === "relative" ? "" : " m";

  return (
    <div className="pointer-events-none absolute inset-0 z-20">
      {/* Elevation scale legend -- bigger bar plus a real tick per
          gradient stop (not just top/bottom labels), so the color-to-
          height mapping is actually readable, not guessed. */}
      {textureMode === "elevation" && cameraMode !== "flythrough" && (
        <div className="pointer-events-none absolute bottom-4 left-4 flex items-stretch gap-4 rounded-2xl border border-white/10 bg-gray-950/85 px-5 py-4 shadow-xl backdrop-blur-md">
          <div className="relative h-56 w-5 shrink-0">
            <div
              className="h-full w-full rounded-full"
              style={{ background: ELEVATION_GRADIENT_CSS }}
            />
            {ELEVATION_STOPS.map((stop) => (
              <div
                key={stop.t}
                className="absolute left-0 h-px w-full bg-black/25"
                style={{ bottom: `${stop.t * 100}%` }}
              />
            ))}
          </div>

          <div className="relative h-56 py-0 text-xs text-white/85">
            {ELEVATION_STOPS.map((stop) => (
              <span
                key={stop.t}
                className="absolute left-0 -translate-y-1/2 whitespace-nowrap"
                style={{ bottom: `${stop.t * 100}%` }}
              >
                {(min + stop.t * (max - min)).toFixed(1)}
                {unitSuffix}
              </span>
            ))}
          </div>

          <span className="absolute -top-6 left-5 text-[11px] font-semibold uppercase tracking-wide text-white/50">
            Elevation
          </span>
        </div>
      )}

      {/* Confidence legend -- violet/teal ramp matching the mesh texture
          exactly (textureUtils.CONFIDENCE_RAMP), deliberately a
          different hue family from the elevation rainbow above so the
          two layers are never mistaken for each other. */}
      {textureMode === "confidence" && cameraMode !== "flythrough" && (
        <div className="pointer-events-none absolute bottom-4 left-4 flex items-stretch gap-4 rounded-2xl border border-white/10 bg-gray-950/85 px-5 py-4 shadow-xl backdrop-blur-md">
          <div
            className="h-56 w-5 shrink-0 rounded-full"
            style={{
              background:
                "linear-gradient(to top, rgb(30,27,75) 0%, rgb(147,51,234) 50%, rgb(45,212,191) 100%)",
            }}
          />
          <div className="relative flex h-56 flex-col justify-between text-xs text-white/85">
            <span>High</span>
            <span className="text-white/50">Confidence</span>
            <span>Low</span>
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
