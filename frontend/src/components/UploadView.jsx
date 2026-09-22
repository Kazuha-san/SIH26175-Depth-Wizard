import React, { useEffect, useRef, useState } from "react";
import { ArrowRight, ArrowUp, Image as ImageIcon, Layers } from "lucide-react";

import ExampleGallery, { EXAMPLE_DRAG_MIME, loadExampleAsFile } from "./ExampleGallery";
import exampleImages from "../data/exampleImages";
import logo from "../assets/depthwizard-icon.png";

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
    <section className="relative flex min-h-screen items-center overflow-hidden px-6 py-8">
      <div className="relative z-10 mx-auto w-full max-w-6xl">
        {/* Hero */}
        <div className="mb-6 text-center">
          <img src={logo} alt="DepthWizard" className="mx-auto mb-2 h-24 w-auto" />

          <h1 className="font-display text-3xl font-bold tracking-tight text-ink sm:text-4xl">
            DepthWizard
          </h1>

          <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-ink-soft">
            Upload an optical RGB image or GeoTIFF and DepthWizard reconstructs
            a Digital Surface Model you can explore as an interactive 3D
            terrain.
          </p>
        </div>

        <div
          className={
            exampleImages.length > 0
              ? "grid gap-5 lg:grid-cols-[1fr_300px]"
              : "mx-auto max-w-2xl"
          }
        >
          <div>
        {/* Upload Card */}
        <div
          onDragOver={(event) => {
            event.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          className={`relative overflow-hidden rounded-3xl border-2 border-dashed p-7 text-center shadow-[0_1px_2px_rgba(11,19,36,0.04)] backdrop-blur-sm transition-all duration-200 ${
            isDragging
              ? "border-teal-400 bg-teal-50/70 shadow-[0_0_0_6px_rgba(18,184,166,0.08)]"
              : "border-blue-200/70 bg-white/90 hover:border-blue-300 hover:bg-white"
          }`}
        >
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-deep to-teal text-2xl text-white shadow-lg shadow-blue-600/20">
            <ArrowUp size={24} strokeWidth={2.5} />
          </div>

          <h3 className="mt-4 font-display text-lg font-semibold text-ink">
            Drop your image here
          </h3>

          <p className="mt-1.5 text-sm text-ink-soft">
            PNG, JPG, JPEG or GeoTIFF
          </p>

          <button
            onClick={handleBrowse}
            className="mt-5 rounded-xl bg-ink px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-deep"
          >
            Browse files
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
          <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {errorMessage}
          </div>
        )}

        {/* Selected File -- full preview so you can actually confirm what
            got uploaded before running the pipeline (not previewing the
            processed output, just the raw input) */}
        {selectedFile && (
          <div className="mt-4 rounded-3xl border border-gray-100 bg-white/95 p-4 shadow-[0_1px_2px_rgba(11,19,36,0.04)] backdrop-blur-sm">
            <div className="flex items-center justify-between gap-4">
              <div className="flex min-w-0 items-center gap-3">
                <div className="flex h-11 w-11 shrink-0 items-center justify-center overflow-hidden rounded-xl bg-surface">
                  {previewUrl ? (
                    <img
                      src={previewUrl}
                      alt="Selected upload preview"
                      className="h-full w-full object-cover"
                    />
                  ) : detectFileType(selectedFile) === "GeoTIFF" ? (
                    <Layers className="text-blue-500" size={20} />
                  ) : (
                    <ImageIcon className="text-blue-500" size={20} />
                  )}
                </div>

                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-ink">
                    {selectedFile.name}
                  </p>

                  <p className="mt-0.5 text-xs text-ink-soft">
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

            {previewUrl ? (
              <div className="mt-3 overflow-hidden rounded-2xl border border-gray-100 bg-surface">
                <img
                  src={previewUrl}
                  alt={`Full preview of ${selectedFile.name}`}
                  className="max-h-[220px] w-full object-contain"
                />
              </div>
            ) : (
              <div className="mt-3 flex items-center gap-3 rounded-2xl border border-gray-100 bg-surface p-3 text-sm text-ink-soft">
                <Layers size={18} className="shrink-0 text-blue-400" />
                GeoTIFF files can't be previewed directly in the browser (no
                native image decode) -- it will still process normally.
              </div>
            )}
          </div>
        )}

        {/* Input Information */}
        <div className="mt-5 grid gap-3 md:grid-cols-2">
          <div className="rounded-2xl border border-gray-100 bg-white/90 p-4 backdrop-blur-sm">
            <p className="text-xs font-semibold uppercase tracking-wider text-blue-500">
              Non-georeferenced
            </p>

            <h4 className="mt-1.5 font-display font-semibold text-ink">PNG / JPG</h4>

            <p className="mt-1.5 text-sm leading-5 text-ink-soft">
              Generates a relative height model for visualization.
            </p>
          </div>

          <div className="rounded-2xl border border-gray-100 bg-white/90 p-4 backdrop-blur-sm">
            <p className="text-xs font-semibold uppercase tracking-wider text-teal-600">
              Georeferenced
            </p>

            <h4 className="mt-1.5 font-display font-semibold text-ink">GeoTIFF</h4>

            <p className="mt-1.5 text-sm leading-5 text-ink-soft">
              Supports geographic metadata and metric calibration.
            </p>
          </div>
        </div>

        {/* Run */}
        <div className="mt-5 flex justify-end">
          <button
            onClick={onRunPipeline}
            disabled={!selectedFile || isUploading}
            className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-blue-deep to-teal px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-blue-600/20 transition hover:brightness-110 disabled:cursor-not-allowed disabled:bg-none disabled:bg-gray-300 disabled:shadow-none"
          >
            {isUploading ? "Uploading…" : "Run pipeline"}
            {!isUploading && <ArrowRight size={16} />}
          </button>
        </div>
          </div>

          {/* Sidebar -- preloaded example gallery */}
          {exampleImages.length > 0 && (
            <div className="flex flex-col gap-4">
              <ExampleGallery onSelectExample={handleSelectExample} disabled={isUploading} />

              {galleryError && (
                <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
                  {galleryError}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </section>
  );
};

export default UploadView;
