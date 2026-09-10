import React, { useState } from "react";

import Navbar from "./components/Navbar";
import UploadView from "./components/UploadView";
import ProcessingView from "./components/ProcessingView";
import ResultsView from "./components/ResultsView";

import FixtureResponse from "./data/FixtureResponse.json";

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
  // File Selection
  // ==========================================================

  const handleFileSelect = (file) => {
    if (!file) return;

    setSelectedFile(file);
  };

  // ==========================================================
  // Run Pipeline
  // ==========================================================

  const handleRunPipeline = () => {
    // No image = cannot process
    if (!selectedFile) {
      return;
    }

    setCurrentView("processing");
  };

  // ==========================================================
  // Processing Complete
  //
  // CURRENTLY:
  // We use FixtureResponse because backend isn't integrated yet.
  //
  // LATER:
  // Replace FixtureResponse with backend response.
  // ==========================================================

  const handleProcessingComplete = () => {
    if (!selectedFile) {
      return;
    }

    // Mock result for now
    setResultData(FixtureResponse);

    // Open Results
    setCurrentView("results");
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

    // DO NOT DO:
    // setResultData(null);

    setCurrentView("upload");
  };

  // ==========================================================
  // Remove current file
  // ==========================================================

  const handleRemoveFile = () => {
    setSelectedFile(null);
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
    <div className="min-h-screen bg-[#F6F7F9] text-gray-900">
      {/* ======================================================
          NAVBAR
      ====================================================== */}

      <Navbar
        currentView={currentView}
        setCurrentView={handleViewChange}
        onNewImage={handleNewImage}
        hasUploadedImage={!!selectedFile}
        hasResult={!!resultData}
      />

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
          />
        )}

        {/* ====================================================
            PROCESSING
        ==================================================== */}

        {currentView === "processing" && (
          <ProcessingView onComplete={handleProcessingComplete} />
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
