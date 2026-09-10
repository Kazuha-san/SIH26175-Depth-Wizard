import React, { useRef, useState } from "react";

import TerrainViewer from "./TerrainViewer";
import ViewerControls from "./ViewerControls";
import { downloadJsonFile } from "../utils/downloadUtils";

const ResultsView = ({ selectedFile, resultData }) => {
  const [cameraMode, setCameraMode] = useState("orbit");
  const [verticalExaggeration, setVerticalExaggeration] = useState(1);
  const [resetSignal, setResetSignal] = useState(0);

  const cameraControllerRef = useRef(null);

  // Safety check
  if (!resultData) {
    return (
      <div className="min-h-[calc(100vh-64px)] flex items-center justify-center bg-[#F6F7F9] px-6">
        <div className="w-full max-w-md rounded-2xl border border-gray-200 bg-white p-8 text-center shadow-sm">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-gray-100">
            <span className="text-2xl">⚠️</span>
          </div>

          <h2 className="text-xl font-semibold text-gray-900">
            No Result Available
          </h2>

          <p className="mt-2 text-sm leading-6 text-gray-500">
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

  const handleExport = () => {
    downloadJsonFile(
      {
        image_id: resultData.image_id,
        input_type: resultData.input_type,
        height_min: resultData.height_min,
        height_max: resultData.height_max,
        metadata: resultData.metadata,
      },
      `${resultData.image_id || "depthwizard-result"}.json`,
    );
  };

  return (
    <div className="min-h-[calc(100vh-64px)] bg-[#F6F7F9]">
      {/* Header */}
      <div className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-[1600px] items-center justify-between px-6 py-4">
          <div>
            <h1 className="text-xl font-semibold text-gray-900">
              3D Terrain Results
            </h1>

            <p className="mt-1 text-sm text-gray-500">
              Explore the generated terrain model and elevation data.
            </p>
          </div>

          <div className="flex items-center gap-3">
            {selectedFile && (
              <div className="hidden rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-600 md:block">
                {selectedFile.name}
              </div>
            )}

            <button
              type="button"
              onClick={handleExport}
              className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 transition hover:bg-gray-50"
            >
              Export JSON
            </button>
          </div>
        </div>
      </div>

      {/* Main Viewer Area */}
      <div className="mx-auto max-w-[1600px] px-6 py-6">
        <div className="grid min-h-[calc(100vh-180px)] grid-cols-1 gap-6 xl:grid-cols-[1fr_320px]">
          {/* Terrain Viewer */}
          <div
            data-terrain-viewer
            className="relative h-[calc(100vh-180px)] min-h-[620px] overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm fullscreen:h-screen fullscreen:min-h-0 fullscreen:rounded-none fullscreen:border-0"
          >
            <TerrainViewer
              resultData={resultData}
              verticalExaggeration={verticalExaggeration}
              cameraMode={cameraMode}
              resetSignal={resetSignal}
              ref={cameraControllerRef}
            />

            <ViewerControls
              cameraMode={cameraMode}
              setCameraMode={setCameraMode}
              verticalExaggeration={verticalExaggeration}
              setVerticalExaggeration={setVerticalExaggeration}
              onResetView={handleReset}
            />

            {/* Viewer Status */}
            <div className="pointer-events-none absolute right-4 top-4 rounded-lg border border-white/50 bg-white/90 px-3 py-2 shadow-sm backdrop-blur">
              <div className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-green-500" />

                <span className="text-xs font-medium text-gray-700">
                  Terrain Model Ready
                </span>
              </div>
            </div>

            {/* Input Type */}
            <div className="pointer-events-none absolute right-4 top-20 rounded-lg border border-white/50 bg-white/90 px-3 py-2 shadow-sm backdrop-blur">
              <p className="text-xs text-gray-500">Input Type</p>

              <p className="mt-0.5 text-sm font-medium capitalize text-gray-800">
                {String(resultData.input_type || "Unknown").replaceAll(
                  "_",
                  " ",
                )}
              </p>
            </div>
          </div>

          {/* Controls / Information */}
          <div className="flex flex-col gap-6">
            {/* Terrain Statistics */}
            <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
              <h2 className="text-sm font-semibold text-gray-900">
                Terrain Statistics
              </h2>

              <div className="mt-4 space-y-3">
                <div className="flex items-center justify-between border-b border-gray-100 pb-3">
                  <span className="text-sm text-gray-500">Minimum Height</span>

                  <span className="text-sm font-semibold text-gray-900">
                    {Number(resultData.height_min ?? 0).toFixed(2)} m
                  </span>
                </div>

                <div className="flex items-center justify-between border-b border-gray-100 pb-3">
                  <span className="text-sm text-gray-500">Maximum Height</span>

                  <span className="text-sm font-semibold text-gray-900">
                    {Number(resultData.height_max ?? 0).toFixed(2)} m
                  </span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-500">Elevation Range</span>

                  <span className="text-sm font-semibold text-gray-900">
                    {(
                      Number(resultData.height_max ?? 0) -
                      Number(resultData.height_min ?? 0)
                    ).toFixed(2)}{" "}
                    m
                  </span>
                </div>
              </div>
            </div>

            {/* Calibration Information */}
            <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
              <h2 className="text-sm font-semibold text-gray-900">
                Calibration
              </h2>

              <div className="mt-4 space-y-3">
                <div>
                  <p className="text-xs text-gray-400">Method</p>

                  <p className="mt-1 text-sm font-medium text-gray-700">
                    {resultData.metadata?.calibration_method || "Not available"}
                  </p>
                </div>

                <div>
                  <p className="text-xs text-gray-400">SRTM Used</p>

                  <p className="mt-1 text-sm font-medium text-gray-700">
                    {resultData.metadata?.srtm_used ? "Yes" : "No"}
                  </p>
                </div>

                <div>
                  <p className="text-xs text-gray-400">CRS</p>

                  <p className="mt-1 break-all text-sm font-medium text-gray-700">
                    {resultData.metadata?.crs || "Not available"}
                  </p>
                </div>
              </div>
            </div>

            {/* Resolution / GSD */}
            <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
              <h2 className="text-sm font-semibold text-gray-900">
                Image Information
              </h2>

              <div className="mt-4 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-500">Target GSD</span>

                  <span className="text-sm font-semibold text-gray-900">
                    {resultData.metadata?.gsd_info?.target_gsd_m != null
                      ? `${resultData.metadata.gsd_info.target_gsd_m} m`
                      : "N/A"}
                  </span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-500">Crop Size</span>

                  <span className="text-sm font-semibold text-gray-900">
                    {resultData.metadata?.gsd_info?.crop_side_px
                      ? `${resultData.metadata.gsd_info.crop_side_px}px`
                      : "N/A"}
                  </span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-500">Resolution</span>

                  <span className="text-sm font-semibold text-gray-900">
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
  );
};

export default ResultsView;
