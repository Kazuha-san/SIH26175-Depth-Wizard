import React from "react";
import { Layers, MapPin } from "lucide-react";

import exampleImages from "../data/exampleImages";

// Custom MIME type used to identify an internal gallery drag vs a real
// OS file drag -- UploadView's onDrop checks for this before falling
// back to event.dataTransfer.files.
export const EXAMPLE_DRAG_MIME = "application/x-depthwizard-example";

const assetUrl = (filename) => `/example-images/${filename}`;

/**
 * Fetches a preloaded static asset and turns it into a real File object,
 * so it flows through the exact same onFileSelect/upload path as a real
 * OS file drop or browse -- no special-casing needed downstream.
 */
export const loadExampleAsFile = async (example) => {
  const response = await fetch(assetUrl(example.filename));
  if (!response.ok) {
    throw new Error(`Could not load example image: ${example.filename}`);
  }
  const blob = await response.blob();
  return new File([blob], example.filename, { type: blob.type });
};

const ExampleGallery = ({ onSelectExample, disabled }) => {
  if (exampleImages.length === 0) {
    return null;
  }

  const handleDragStart = (event, example) => {
    event.dataTransfer.setData(EXAMPLE_DRAG_MIME, example.id);
    event.dataTransfer.setData("text/plain", example.id);
    event.dataTransfer.effectAllowed = "copy";
  };

  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
      <div className="mb-1 text-sm font-semibold text-gray-900">
        Try a sample image
      </div>
      <p className="mb-4 text-xs leading-5 text-gray-500">
        Real satellite imagery the model has never trained on. Drag one
        into the upload area, or click to use it directly.
      </p>

      <div className="grid grid-cols-2 gap-3">
        {exampleImages.map((example) => (
          <button
            key={example.id}
            type="button"
            draggable={!disabled}
            disabled={disabled}
            onDragStart={(event) => handleDragStart(event, example)}
            onClick={() => onSelectExample(example)}
            className="group relative overflow-hidden rounded-xl border border-gray-200 text-left transition hover:border-blue-300 hover:shadow-md disabled:cursor-not-allowed disabled:opacity-50"
          >
            <div className="aspect-square w-full overflow-hidden bg-gray-100">
              {example.type === "tif" ? (
                <div className="flex h-full w-full items-center justify-center">
                  <Layers className="text-gray-400" size={28} />
                </div>
              ) : (
                <img
                  src={assetUrl(example.filename)}
                  alt={example.label}
                  draggable={false}
                  className="h-full w-full object-cover transition group-hover:scale-105"
                />
              )}
            </div>

            {example.georeferenced && (
              <div className="absolute right-1.5 top-1.5 flex items-center gap-1 rounded-full bg-white/90 px-1.5 py-0.5 text-[10px] font-semibold text-blue-700 shadow-sm backdrop-blur">
                <MapPin size={10} />
                Geo
              </div>
            )}

            <div className="bg-white p-2">
              <p className="truncate text-xs font-semibold text-gray-900">
                {example.label}
              </p>
              <p className="truncate text-[11px] text-gray-500">
                {example.source}
              </p>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
};

export default ExampleGallery;
