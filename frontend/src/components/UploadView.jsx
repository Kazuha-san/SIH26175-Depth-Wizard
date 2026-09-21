import React, { useEffect, useRef, useState } from "react";
import { Image as ImageIcon, Layers } from "lucide-react";

import ExampleGallery, { EXAMPLE_DRAG_MIME, loadExampleAsFile } from "./ExampleGallery";
import exampleImages from "../data/exampleImages";

const UploadView = ({
  selectedFile,
  onFileSelect,
  onRunPipeline,
  onRemoveFile,
  errorMessage,
  isUploading,
}) => {
  const fileInputRef = useRef(null);
  const [isDragging, setIsDragging] = useState(false);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [galleryError, setGalleryError] = useState(null);

  // Object-URL preview -- only for formats the browser can actually decode
  // (PNG/JPG). GeoTIFF has no native <img> support, so we show a labeled
  // icon instead of a broken image rather than pretending to preview it.
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

  const detectFileType = (file) => {
    const extension = file.name.split(".").pop().toLowerCase();

    if (extension === "tif" || extension === "tiff") {
      return "GeoTIFF";
    }

    return "Image";
  };

  const handleFile = (file) => {
    if (!file) return;

    const extension = file.name.split(".").pop().toLowerCase();
    const allowedExtensions = ["png", "jpg", "jpeg", "tif", "tiff"];

    if (!allowedExtensions.includes(extension)) {
      alert("Please select a PNG, JPG or GeoTIFF file.");
      return;
    }

    onFileSelect(file);
  };

  const handleDrop = (event) => {
    event.preventDefault();
    setIsDragging(false);

    // A gallery item being dragged in carries our custom MIME type instead
    // of real files -- check that first, otherwise fall through to a
    // normal OS file drop.
    const exampleId = event.dataTransfer.getData(EXAMPLE_DRAG_MIME);
    if (exampleId) {
      const example = exampleImages.find((item) => item.id === exampleId);
      if (example) {
        handleSelectExample(example);
      }
      return;
    }

    const file = event.dataTransfer.files[0];
    handleFile(file);
  };

  const handleSelectExample = async (example) => {
    setGalleryError(null);
    try {
      const file = await loadExampleAsFile(example);
      handleFile(file);
    } catch (error) {
      setGalleryError(
        error instanceof Error ? error.message : "Could not load that example image.",
      );
    }
  };

  const handleBrowse = () => {
    fileInputRef.current?.click();
  };

  return (
    <section className="min-h-[calc(100vh-64px)] px-6 py-10">
      <div className="mx-auto max-w-6xl">
        {/* Heading */}
        <div className="mb-8">
          <div className="mb-3 inline-flex items-center rounded-full border border-blue-100 bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-600">
            STEP 01 · INPUT
          </div>

          <h2 className="text-3xl font-bold tracking-tight text-gray-900">
            Upload satellite imagery
          </h2>

          <p className="mt-2 max-w-2xl text-sm leading-6 text-gray-500">
            Upload an optical RGB image to generate a Digital Surface Model and
            explore the reconstructed terrain in 3D.
          </p>
        </div>

        <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
          <div>
        {/* Upload Card */}
        <div
          onDragOver={(event) => {
            event.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          className={`rounded-2xl border-2 border-dashed p-10 text-center transition ${
            isDragging
              ? "border-blue-500 bg-blue-50"
              : "border-gray-300 bg-white hover:border-blue-300"
          }`}
        >
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-blue-50 text-2xl">
            ↑
          </div>

          <h3 className="mt-5 text-lg font-semibold text-gray-900">
            Drop your image here
          </h3>

          <p className="mt-2 text-sm text-gray-500">
            PNG, JPG, JPEG or GeoTIFF
          </p>

          <button
            onClick={handleBrowse}
            className="mt-6 rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700"
          >
            Browse Files
          </button>

          <input
            ref={fileInputRef}
            type="file"
            accept=".png,.jpg,.jpeg,.tif,.tiff"
            className="hidden"
            onChange={(event) => handleFile(event.target.files[0])}
          />
        </div>

        {/* Error */}
        {errorMessage && (
          <div className="mt-5 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {errorMessage}
          </div>
        )}

        {/* Selected File */}
        {selectedFile && (
          <div className="mt-5 rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between gap-4">
              <div className="flex min-w-0 items-center gap-4">
                <div className="flex h-14 w-14 shrink-0 items-center justify-center overflow-hidden rounded-xl bg-gray-100">
                  {previewUrl ? (
                    <img
                      src={previewUrl}
                      alt="Selected upload preview"
                      className="h-full w-full object-cover"
                    />
                  ) : detectFileType(selectedFile) === "GeoTIFF" ? (
                    <Layers className="text-gray-400" size={22} />
                  ) : (
                    <ImageIcon className="text-gray-400" size={22} />
                  )}
                </div>

                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-gray-900">
                    {selectedFile.name}
                  </p>

                  <p className="mt-1 text-xs text-gray-500">
                    {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                    {" · "}
                    {detectFileType(selectedFile)}
                  </p>
                </div>
              </div>

              <button
                onClick={onRemoveFile}
                className="shrink-0 text-sm font-medium text-gray-400 hover:text-red-500"
              >
                Remove
              </button>
            </div>
          </div>
        )}

        {/* Input Information */}
        <div className="mt-6 grid gap-4 md:grid-cols-2">
          <div className="rounded-2xl border border-gray-200 bg-white p-5">
            <p className="text-xs font-semibold uppercase tracking-wider text-gray-400">
              Non-georeferenced
            </p>

            <h4 className="mt-2 font-semibold text-gray-900">PNG / JPG</h4>

            <p className="mt-2 text-sm leading-5 text-gray-500">
              Generates a relative height model for visualization.
            </p>
          </div>

          <div className="rounded-2xl border border-gray-200 bg-white p-5">
            <p className="text-xs font-semibold uppercase tracking-wider text-gray-400">
              Georeferenced
            </p>

            <h4 className="mt-2 font-semibold text-gray-900">GeoTIFF</h4>

            <p className="mt-2 text-sm leading-5 text-gray-500">
              Supports geographic metadata and metric calibration.
            </p>
          </div>
        </div>

        {/* Run */}
        <div className="mt-8 flex justify-end">
          <button
            onClick={onRunPipeline}
            disabled={!selectedFile || isUploading}
            className="rounded-xl bg-blue-600 px-6 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-gray-300"
          >
            {isUploading ? "Uploading…" : "Run Pipeline →"}
          </button>
        </div>
          </div>

          {/* Sidebar -- preloaded example gallery */}
          <div className="flex flex-col gap-4">
            <ExampleGallery onSelectExample={handleSelectExample} disabled={isUploading} />

            {galleryError && (
              <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
                {galleryError}
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
};

export default UploadView;
