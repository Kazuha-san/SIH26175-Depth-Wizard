import React, { useEffect, useRef, useState } from "react";
import { ImageIcon, Layers } from "lucide-react";

import TerrainViewer from "./TerrainViewer";
import ViewerControls, { ViewerRailControls } from "./ViewerControls";

const ResultsView = ({ selectedFile, resultData }) => {
  const [cameraMode, setCameraMode] = useState("orbit");
  const [verticalExaggeration, setVerticalExaggeration] = useState(1);
  const [textureMode, setTextureMode] = useState("rgb");
  const [resetSignal, setResetSignal] = useState(0);
  const [previewUrl, setPreviewUrl] = useState(null);

  const cameraControllerRef = useRef(null);

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

  const handleReset = () => {
    setResetSignal((prev) => prev + 1);

    if (cameraControllerRef.current?.reset) {
      cameraControllerRef.current.reset();
    }
  };

  const isRelative = resultData.height_units === "relative";

  return (
    <div className="relative z-10 min-h-screen">
      {/* Main layout: left rail / center viewport / right sidebar */}
      <div className="mx-auto max-w-[1700px] px-6 py-6">
        <div className="grid h-[calc(100vh-48px)] grid-cols-1 gap-5 xl:grid-cols-[240px_1fr_320px]">
          {/* Left rail -- map control & options */}
          <div className="rounded-3xl border border-gray-100 bg-white p-5 shadow-[0_1px_2px_rgba(11,19,36,0.04)] xl:h-fit">
            <p className="mb-4 font-display text-sm font-semibold text-ink">
              View controls
            </p>
            <ViewerRailControls
              cameraMode={cameraMode}
              setCameraMode={setCameraMode}
              verticalExaggeration={verticalExaggeration}
              setVerticalExaggeration={setVerticalExaggeration}
              onResetView={handleReset}
              textureMode={textureMode}
              setTextureMode={setTextureMode}
              hasConfidence={!!resultData.confidence_png_b64}
            />
          </div>

          {/* Center -- 3D model */}
          <div
            data-terrain-viewer
            className="relative h-[calc(100vh-48px)] min-h-[560px] overflow-hidden rounded-3xl border border-gray-100 bg-gray-950 shadow-[0_1px_2px_rgba(11,19,36,0.04)] fullscreen:h-screen fullscreen:min-h-0 fullscreen:rounded-none fullscreen:border-0"
          >
            <TerrainViewer
              resultData={resultData}
              verticalExaggeration={verticalExaggeration}
              cameraMode={cameraMode}
              textureMode={textureMode}
              resetSignal={resetSignal}
              ref={cameraControllerRef}
            />

            <ViewerControls cameraMode={cameraMode} textureMode={textureMode} />

            {/* Input Type badge */}
            <div className="pointer-events-none absolute right-4 top-4 rounded-lg border border-white/10 bg-gray-950/80 px-3 py-2 shadow-sm backdrop-blur">
              <p className="text-xs text-white/50">Input type</p>
              <p className="mt-0.5 text-sm font-medium capitalize text-white">
                {String(resultData.input_type || "Unknown").replaceAll("_", " ")}
              </p>
            </div>
          </div>

          {/* Right sidebar -- input preview (top) / stats (bottom) */}
          <div className="flex max-h-[calc(100vh-48px)] flex-col gap-5">
            {/* Preview of input image */}
            <div className="shrink-0 overflow-hidden rounded-3xl border border-gray-100 bg-white shadow-[0_1px_2px_rgba(11,19,36,0.04)]">
              <div className="border-b border-gray-100 px-5 py-3">
                <p className="font-display text-sm font-semibold text-ink">
                  Input image
                </p>
              </div>

              {previewUrl ? (
                <img
                  src={previewUrl}
                  alt="Input imagery preview"
                  className="aspect-video w-full object-cover"
                />
              ) : (
                <div className="flex aspect-video w-full items-center justify-center bg-surface">
                  <Layers className="text-blue-400" size={28} />
                </div>
              )}

              {selectedFile && (
                <div className="flex items-center gap-2 px-5 py-3">
                  <ImageIcon size={14} className="shrink-0 text-ink-soft" />
                  <p className="truncate text-xs font-medium text-ink-soft">
                    {selectedFile.name}
                  </p>
                </div>
              )}
            </div>

            {/* All the height/data stats, independently scrollable */}
            <div className="flex flex-1 flex-col gap-5 overflow-y-auto pr-1">
              {/* Terrain Statistics */}
              <div className="rounded-3xl border border-gray-100 bg-white p-5 shadow-[0_1px_2px_rgba(11,19,36,0.04)]">
                <div className="flex items-center justify-between">
                  <h2 className="font-display text-sm font-semibold text-ink">
                    Terrain statistics
                  </h2>
                  {isRelative && (
                    <span className="rounded-full bg-amber-50 px-2 py-0.5 text-[11px] font-semibold text-amber-700">
                      Relative units
                    </span>
                  )}
                </div>

                {isRelative && (
                  <p className="mt-1 text-xs leading-4 text-ink-soft">
                    No SRTM calibration for this result — values below are
                    normalized (0–1), not real-world meters.
                  </p>
                )}

                <div className="mt-4 space-y-3">
                  <div className="flex items-center justify-between border-b border-gray-100 pb-3">
                    <span className="text-sm text-ink-soft">Minimum height</span>
                    <span className="text-sm font-semibold text-ink">
                      {Number(resultData.height_min ?? 0).toFixed(2)}
                      {isRelative ? "" : " m"}
                    </span>
                  </div>

                  <div className="flex items-center justify-between border-b border-gray-100 pb-3">
                    <span className="text-sm text-ink-soft">Maximum height</span>
                    <span className="text-sm font-semibold text-ink">
                      {Number(resultData.height_max ?? 0).toFixed(2)}
                      {isRelative ? "" : " m"}
                    </span>
                  </div>

                  <div className="flex items-center justify-between">
                    <span className="text-sm text-ink-soft">Elevation range</span>
                    <span className="text-sm font-semibold text-ink">
                      {(
                        Number(resultData.height_max ?? 0) -
                        Number(resultData.height_min ?? 0)
                      ).toFixed(2)}
                      {isRelative ? "" : " m"}
                    </span>
                  </div>
                </div>
              </div>

              {/* Calibration Information */}
              <div className="rounded-3xl border border-gray-100 bg-white p-5 shadow-[0_1px_2px_rgba(11,19,36,0.04)]">
                <h2 className="font-display text-sm font-semibold text-ink">
                  Calibration
                </h2>

                <div className="mt-4 space-y-3">
                  <div>
                    <p className="text-xs text-gray-400">Method</p>
                    <p className="mt-1 text-sm font-medium text-ink-soft">
                      {resultData.metadata?.calibration_method || "Not available"}
                    </p>
                  </div>

                  <div>
                    <p className="text-xs text-gray-400">SRTM used</p>
                    <p className="mt-1 text-sm font-medium text-ink-soft">
                      {resultData.metadata?.srtm_used ? "Yes" : "No"}
                    </p>
                  </div>

                  {/* Surfaces WHY it fell back, rather than leaving "SRTM
                      used: No" unexplained -- routes.py records this
                      reason specifically so this can be shown. */}
                  {!resultData.metadata?.srtm_used &&
                    resultData.metadata?.srtm_fallback_reason && (
                      <div className="rounded-xl border border-amber-100 bg-amber-50 px-3 py-2">
                        <p className="text-xs leading-4 text-amber-800">
                          SRTM fallback reason:{" "}
                          {resultData.metadata.srtm_fallback_reason}
                        </p>
                      </div>
                    )}

                  <div>
                    <p className="text-xs text-gray-400">CRS</p>
                    <p className="mt-1 break-all text-sm font-medium text-ink-soft">
                      {resultData.metadata?.crs || "Not available"}
                    </p>
                  </div>
                </div>
              </div>

              {/* Resolution / GSD */}
              <div className="rounded-3xl border border-gray-100 bg-white p-5 shadow-[0_1px_2px_rgba(11,19,36,0.04)]">
                <h2 className="font-display text-sm font-semibold text-ink">
                  Image information
                </h2>

                <div className="mt-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-ink-soft">Target GSD</span>
                    <span className="text-sm font-semibold text-ink">
                      {resultData.metadata?.gsd_info?.target_gsd_m != null
                        ? `${resultData.metadata.gsd_info.target_gsd_m} m`
                        : "N/A"}
                    </span>
                  </div>

                  <div className="flex items-center justify-between">
                    <span className="text-sm text-ink-soft">Tile size</span>
                    <span className="text-sm font-semibold text-ink">
                      {resultData.metadata?.gsd_info?.tile_side_px
                        ? `${resultData.metadata.gsd_info.tile_side_px}px`
                        : resultData.metadata?.gsd_info?.crop_side_px
                          ? `${resultData.metadata.gsd_info.crop_side_px}px`
                          : "N/A"}
                    </span>
                  </div>

                  <div className="flex items-center justify-between">
                    <span className="text-sm text-ink-soft">Tiles processed</span>
                    <span className="text-sm font-semibold text-ink">
                      {resultData.metadata?.gsd_info?.n_tiles ?? "N/A"}
                    </span>
                  </div>

                  <div className="flex items-center justify-between">
                    <span className="text-sm text-ink-soft">Resolution</span>
                    <span className="text-sm font-semibold text-ink">
                      {resultData.metadata?.resolution_m != null
                        ? `${resultData.metadata.resolution_m} m`
                        : "N/A"}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ResultsView;
