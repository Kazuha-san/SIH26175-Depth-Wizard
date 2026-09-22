import React, { useState } from "react";

import AnimatedBackground from "./components/AnimatedBackground";
import UploadView from "./components/UploadView";
import ProcessingView from "./components/ProcessingView";
import ResultsView from "./components/ResultsView";

import { uploadImage } from "./utils/api";

const App = () => {
  // ==========================================================
  // Navigation
  // ==========================================================

  const [currentView, setCurrentView] = useState("upload");

  // ==========================================================
  // Current uploaded image
  // ==========================================================

  const [selectedFile, setSelectedFile] = useState(null);

  // ==========================================================
  // Last successfully generated result
  //
  // IMPORTANT:
  // This is intentionally separate from selectedFile.
  //
  // New Image will NOT delete this.
  // ==========================================================

  const [resultData, setResultData] = useState(null);

  // ==========================================================
  // The uploaded image's backend id, set once /upload succeeds.
  // ProcessingView uses this to kick off /process.
  // ==========================================================

  const [imageId, setImageId] = useState(null);

  // ==========================================================
  // Upload error (shown on the upload view if /upload itself fails,
  // e.g. backend not running, unreadable file)
  // ==========================================================

  const [uploadError, setUploadError] = useState(null);
  const [isUploading, setIsUploading] = useState(false);

  // ==========================================================
  // File Selection
  // ==========================================================

  const handleFileSelect = (file) => {
    if (!file) return;

    setUploadError(null);
    setSelectedFile(file);
  };

  // ==========================================================
  // Run Pipeline
  //
  // Uploads the file to get an image_id, then hands off to
  // ProcessingView, which runs the actual (slow) /process call.
  // ==========================================================

  const handleRunPipeline = async () => {
    if (!selectedFile) {
      return;
    }

    setUploadError(null);
    setIsUploading(true);

    try {
      const { image_id } = await uploadImage(selectedFile);
      setImageId(image_id);
      setCurrentView("processing");
    } catch (error) {
      setUploadError(
        error instanceof Error ? error.message : "Upload failed. Is the backend running?",
      );
    } finally {
      setIsUploading(false);
    }
  };

  // ==========================================================
  // Processing Complete
  //
  // ProcessingView calls this with the REAL backend result once
  // /process/{image_id} resolves.
  // ==========================================================

  const handleProcessingComplete = (backendResult) => {
    setResultData(backendResult);
    setCurrentView("results");
  };

  // ==========================================================
  // Processing Failed
  //
  // Sends the user back to Upload with an error message rather than
  // stranding them on a dead processing screen.
  // ==========================================================

  const handleProcessingError = (message) => {
    setUploadError(message);
    setCurrentView("upload");
  };

  // ==========================================================
  // New Image
  //
  // IMPORTANT:
  // DO NOT clear resultData.
  //
  // This preserves the previous result.
  // ==========================================================

  const handleNewImage = () => {
    setSelectedFile(null);
    setImageId(null);
    setUploadError(null);

    // DO NOT DO:
    // setResultData(null);

    setCurrentView("upload");
  };

  // ==========================================================
  // Remove current file
  // ==========================================================

  const handleRemoveFile = () => {
    setSelectedFile(null);
    setImageId(null);
    setUploadError(null);
  };

  // ==========================================================
  // Safe Navigation
  //
  // Processing requires an uploaded image.
  // Results requires an existing result.
  // ==========================================================

  const handleViewChange = (view) => {
    if (view === "processing") {
      if (!selectedFile) {
        return;
      }
    }

    if (view === "results") {
      if (!resultData) {
        return;
      }
    }

    setCurrentView(view);
  };

  return (
    <div className="min-h-screen text-ink">
      <AnimatedBackground />

      {/* ======================================================
          MAIN CONTENT
      ====================================================== */}

      <main>
        {/* ====================================================
            UPLOAD
        ==================================================== */}

        {currentView === "upload" && (
          <UploadView
            selectedFile={selectedFile}
            onFileSelect={handleFileSelect}
            onRunPipeline={handleRunPipeline}
            onRemoveFile={handleRemoveFile}
            errorMessage={uploadError}
            isUploading={isUploading}
          />
        )}

        {/* ====================================================
            PROCESSING
        ==================================================== */}

        {currentView === "processing" && (
          <ProcessingView
            imageId={imageId}
            onComplete={handleProcessingComplete}
            onError={handleProcessingError}
          />
        )}

        {/* ====================================================
            RESULTS
        ==================================================== */}

        {currentView === "results" && (
          <ResultsView selectedFile={selectedFile} resultData={resultData} />
        )}
      </main>
    </div>
  );
};

export default App;
