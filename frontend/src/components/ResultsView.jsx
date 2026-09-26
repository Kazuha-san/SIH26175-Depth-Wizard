import React, { useEffect, useRef, useState } from "react";
import { ChevronLeft, ChevronRight, ImageIcon, Layers, Mountain } from "lucide-react";

import TerrainViewer from "./TerrainViewer";
import ViewerControls, { ViewerRailControls } from "./ViewerControls";
import { renderHeightmapPreview } from "../utils/heightmapPreview";

// Grid template for the right panel's open/closed state. Listed explicitly
// (rather than built from a template string) because Tailwind's JIT
// scanner needs each class to appear literally in source to generate it --
// a dynamically-built arbitrary-value class would be silently dropped
// from the build.
const GRID_COLS = {
  true: "xl:grid-cols-[1fr_360px]",
  false: "xl:grid-cols-[1fr_0px]",
};

// One row in the info panel's key/value lists.
const InfoRow = ({ label, value }) => (
  <div className="flex items-center justify-between gap-4 border-b border-gray-100 py-2.5 last:border-0">
    <span className="text-sm text-ink-soft">{label}</span>
    <span className="text-right text-sm font-semibold text-ink">{value}</span>
  </div>
);

const InfoSection = ({ title, badge, note, children }) => (
  <div>
    <div className="flex items-center justify-between">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-ink-soft">
        {title}
      </h3>
      {badge}
    </div>
    {note && <p className="mt-1 text-xs leading-4 text-ink-soft">{note}</p>}
    <div className="mt-2">{children}</div>
  </div>
);

const ResultsView = ({ selectedFile, resultData }) => {
  const [cameraMode, setCameraMode] = useState("orbit");
  const [verticalExaggeration, setVerticalExaggeration] = useState(1);
  const [textureMode, setTextureMode] = useState("elevation");
  const [previewUrl, setPreviewUrl] = useState(null);
  const [heightmapPreviewUrl, setHeightmapPreviewUrl] = useState(null);
  const [heightmapPreviewError, setHeightmapPreviewError] = useState(false);
  const [rightPanelOpen, setRightPanelOpen] = useState(true);
  const [rightTab, setRightTab] = useState("preview");
  const [isFullscreen, setIsFullscreen] = useState(false);

  // Same "only preview what the browser can actually decode" rule as
  // UploadView -- GeoTIFF gets a labeled icon instead of a broken image.
  useEffect(() => {
    if (!selectedFile) {
      setPreviewUrl(null);
      return undefined;
    }
    const extension = selectedFile.name.split(".").pop().toLowerCase();
    if (extension === "tif" || extension === "tiff") {
      setPreviewUrl(null);
      return undefined;
    }
    const url = URL.createObjectURL(selectedFile);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [selectedFile]);

  // Re-color the backend's raw 16-bit heightmap PNG into a readable
  // hypsometric 2D preview (same ramp as the 3D "Elevation" mode) so the
  // results screen shows input RGB and output height map side by side,
  // not just the input.
  useEffect(() => {
    setHeightmapPreviewError(false);

    if (!resultData?.heightmap_png_b64) {
      setHeightmapPreviewUrl(null);
      return;
    }

    try {
      setHeightmapPreviewUrl(renderHeightmapPreview(resultData));
    } catch (error) {
      console.error("Heightmap preview rendering failed:", error);
      setHeightmapPreviewUrl(null);
      setHeightmapPreviewError(true);
    }
  }, [resultData]);

  // Tracks the real fullscreen state (not just "did we ask for it") so
  // the view-controls card can swap its icon and actually communicate
  // how to get back out -- Esc and the browser's own UI both change
  // this too, so this can't just be local toggle state.
  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(Boolean(document.fullscreenElement));
    };
    document.addEventListener("fullscreenchange", handleFullscreenChange);
    return () =>
      document.removeEventListener("fullscreenchange", handleFullscreenChange);
  }, []);

  const handleToggleFullscreen = async () => {
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

  // Safety check
  if (!resultData) {
    return (
      <div className="relative z-10 flex min-h-screen items-center justify-center px-6">
        <div className="w-full max-w-md rounded-3xl border border-gray-100 bg-white p-8 text-center shadow-[0_1px_2px_rgba(11,19,36,0.04)]">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-surface">
            <span className="text-2xl">⚠️</span>
          </div>

          <h2 className="font-display text-xl font-semibold text-ink">
            No result available
          </h2>

          <p className="mt-2 text-sm leading-6 text-ink-soft">
            Please upload an image and complete the processing pipeline first.
          </p>
        </div>
      </div>
    );
  }

  const isRelative = resultData.height_units === "relative";
  const isGeoreferenced = String(resultData.input_type || "")
    .toLowerCase()
    .includes("georeferenced") && !String(resultData.input_type || "")
    .toLowerCase()
    .includes("non");
  const srtmUsed = Boolean(resultData.metadata?.srtm_used);
  const hasConfidence = Boolean(resultData.confidence_png_b64);
  const elevationRange =
    Number(resultData.height_max ?? 0) - Number(resultData.height_min ?? 0);

  return (
    <div className="relative z-10 min-h-screen">
      {/* Main layout: full-bleed 3D viewport / right info sidebar.
          View controls now float over the viewport itself instead of
          living in a dedicated left column. */}
      <div className="mx-auto max-w-[1700px] px-6 py-6">
        <div
          className={`grid h-[calc(100vh-48px)] grid-cols-1 gap-5 ${GRID_COLS[rightPanelOpen]}`}
        >
          {/* Center -- 3D model, edge-to-edge */}
          <div
            data-terrain-viewer
            className="relative h-[calc(100vh-48px)] min-h-[560px] overflow-hidden rounded-3xl border border-gray-100 bg-gray-950 shadow-[0_1px_2px_rgba(11,19,36,0.04)] fullscreen:h-screen fullscreen:min-h-0 fullscreen:rounded-none fullscreen:border-0"
          >
            {/* Right info-panel collapse toggle -- docked to the
                viewer's own edge so it stays reachable regardless of
                panel state. */}
            <button
              type="button"
              onClick={() => setRightPanelOpen((value) => !value)}
              title={rightPanelOpen ? "Collapse info panel" : "Show info panel"}
              aria-label="Toggle right panel"
              className="absolute right-3 top-1/2 z-30 hidden h-8 w-8 -translate-y-1/2 items-center justify-center rounded-lg border border-white/10 bg-gray-950/80 text-white/80 shadow-sm backdrop-blur transition hover:text-white xl:flex"
            >
              {rightPanelOpen ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
            </button>

            <TerrainViewer
              resultData={resultData}
              verticalExaggeration={verticalExaggeration}
              cameraMode={cameraMode}
              textureMode={textureMode}
            />

            <ViewerControls
              cameraMode={cameraMode}
              textureMode={textureMode}
              heightMin={Number(resultData.height_min)}
              heightMax={Number(resultData.height_max)}
              heightUnits={resultData.height_units}
            />

            {/* Floating view-controls card -- top right, over the canvas */}
            <ViewerRailControls
              cameraMode={cameraMode}
              setCameraMode={setCameraMode}
              verticalExaggeration={verticalExaggeration}
              setVerticalExaggeration={setVerticalExaggeration}
              textureMode={textureMode}
              setTextureMode={setTextureMode}
              hasConfidence={hasConfidence}
              isFullscreen={isFullscreen}
              onToggleFullscreen={handleToggleFullscreen}
            />

            {/* Input Type badge -- moved to top-left so it doesn't
                collide with the floating view-controls card */}
            <div className="pointer-events-none absolute left-4 top-4 z-20 rounded-lg border border-white/10 bg-gray-950/80 px-3 py-2 shadow-sm backdrop-blur">
              <p className="text-xs text-white/50">Input type</p>
              <p className="mt-0.5 text-sm font-medium capitalize text-white">
                {String(resultData.input_type || "Unknown").replaceAll("_", " ")}
              </p>
            </div>
          </div>

          {/* Right sidebar -- one panel with two tabs (Preview /
              Information) that fully swap content, rather than a
              stacked previews+scrolling-stats layout. Each tab gets the
              full panel height, so previews are never cramped and
              scrolling only ever has to deal with one section at a time. */}
          <div
            className={`flex max-h-[calc(100vh-48px)] flex-col overflow-hidden rounded-3xl border border-gray-100 bg-white shadow-[0_1px_2px_rgba(11,19,36,0.04)] ${
              rightPanelOpen ? "" : "hidden xl:hidden"
            }`}
          >
            <div className="flex shrink-0 items-center gap-1 border-b border-gray-100 p-2">
              {[
                { key: "preview", label: "Preview" },
                { key: "information", label: "Information" },
              ].map(({ key, label }) => (
                <button
                  key={key}
                  type="button"
                  onClick={() => setRightTab(key)}
                  className={`flex-1 rounded-xl px-3 py-2 text-sm font-semibold transition ${
                    rightTab === key
                      ? "bg-surface text-ink"
                      : "text-ink-soft hover:text-ink"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>

            {rightTab === "preview" ? (
              <div className="flex flex-1 flex-col gap-4 overflow-y-auto p-5">
                <div className="overflow-hidden rounded-2xl border border-gray-100">
                  <div className="bg-surface px-4 py-2.5">
                    <p className="font-display text-xs font-semibold text-ink">
                      Input image
                    </p>
                  </div>

                  {previewUrl ? (
                    <img
                      src={previewUrl}
                      alt="Input imagery preview"
                      className="max-h-[45vh] w-full object-contain bg-black/5"
                    />
                  ) : (
                    <div className="flex h-40 w-full items-center justify-center bg-surface">
                      <Layers className="text-blue-400" size={28} />
                    </div>
                  )}
                </div>

                <div className="overflow-hidden rounded-2xl border border-gray-100">
                  <div className="bg-surface px-4 py-2.5">
                    <p className="font-display text-xs font-semibold text-ink">
                      Height map
                    </p>
                  </div>

                  {heightmapPreviewUrl ? (
                    <img
                      src={heightmapPreviewUrl}
                      alt="Output height map preview"
                      className="max-h-[45vh] w-full object-contain bg-black/5"
                      style={{ imageRendering: "pixelated" }}
                    />
                  ) : (
                    <div className="flex h-40 w-full items-center justify-center bg-surface">
                      <Mountain
                        className={heightmapPreviewError ? "text-red-300" : "text-blue-400"}
                        size={28}
                      />
                    </div>
                  )}
                </div>

                {selectedFile && (
                  <div className="flex shrink-0 items-center gap-2 px-1">
                    <ImageIcon size={14} className="shrink-0 text-ink-soft" />
                    <p className="truncate text-xs font-medium text-ink-soft">
                      {selectedFile.name}
                    </p>
                  </div>
                )}
              </div>
            ) : (
              /* Result details -- grouped by what it actually covers
                 (elevation output / calibration & georeferencing /
                 source & processing / confidence), replacing the old
                 Terrain statistics / Calibration / Image information
                 three-box layout. Its own scroll area, independent of
                 the Preview tab. */
              <div className="flex-1 overflow-y-auto p-5">
                <div className="flex flex-col gap-5">
                  <InfoSection
                    title="Elevation output"
                    badge={
                      isRelative && (
                        <span className="rounded-full bg-amber-50 px-2 py-0.5 text-[11px] font-semibold text-amber-700">
                          Relative units
                        </span>
                      )
                    }
                    note={
                      isRelative
                        ? "No SRTM calibration for this result — values are normalized (0–1), not real-world meters."
                        : undefined
                    }
                  >
                    <InfoRow
                      label="Minimum height"
                      value={`${Number(resultData.height_min ?? 0).toFixed(2)}${isRelative ? "" : " m"}`}
                    />
                    <InfoRow
                      label="Maximum height"
                      value={`${Number(resultData.height_max ?? 0).toFixed(2)}${isRelative ? "" : " m"}`}
                    />
                    <InfoRow
                      label="Elevation range"
                      value={`${elevationRange.toFixed(2)}${isRelative ? "" : " m"}`}
                    />
                  </InfoSection>

                  <InfoSection title="Calibration & georeferencing">
                    <InfoRow
                      label="Method"
                      value={resultData.metadata?.calibration_method || "Not available"}
                    />
                    <InfoRow label="SRTM used" value={srtmUsed ? "Yes" : "No"} />
                    <InfoRow
                      label="CRS"
                      value={resultData.metadata?.crs || "Not available"}
                    />

                    {/* Surfaces WHY it fell back, rather than leaving
                        "SRTM used: No" unexplained -- routes.py records
                        this reason specifically so this can be shown. */}
                    {!srtmUsed && resultData.metadata?.srtm_fallback_reason && (
                      <div className="mt-2 rounded-xl border border-amber-100 bg-amber-50 px-3 py-2">
                        <p className="text-xs leading-4 text-amber-800">
                          SRTM fallback reason: {resultData.metadata.srtm_fallback_reason}
                        </p>
                      </div>
                    )}
                  </InfoSection>

                  <InfoSection title="Source & processing">
                    <InfoRow
                      label="Georeferenced"
                      value={isGeoreferenced ? "Yes" : "No"}
                    />
                    <InfoRow
                      label="Target GSD"
                      value={
                        resultData.metadata?.gsd_info?.target_gsd_m != null
                          ? `${resultData.metadata.gsd_info.target_gsd_m} m`
                          : "N/A"
                      }
                    />
                    <InfoRow
                      label="Tile size"
                      value={
                        resultData.metadata?.gsd_info?.tile_side_px
                          ? `${resultData.metadata.gsd_info.tile_side_px}px`
                          : resultData.metadata?.gsd_info?.crop_side_px
                            ? `${resultData.metadata.gsd_info.crop_side_px}px`
                            : "N/A"
                      }
                    />
                    <InfoRow
                      label="Tiles processed"
                      value={resultData.metadata?.gsd_info?.n_tiles ?? "N/A"}
                    />
                    <InfoRow
                      label="Resolution"
                      value={
                        resultData.metadata?.resolution_m != null
                          ? `${resultData.metadata.resolution_m} m`
                          : "N/A"
                      }
                    />
                  </InfoSection>

                  <InfoSection title="Confidence">
                    <InfoRow
                      label="Uncertainty pass"
                      value={hasConfidence ? "Available" : "Not run"}
                    />
                  </InfoSection>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ResultsView;
