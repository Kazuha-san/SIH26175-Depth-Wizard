import React, { useEffect, useState } from "react";

import { processImage } from "../utils/api";
import TerrainScanAnimation from "./TerrainScanAnimation";

const ProcessingView = ({ imageId, onComplete, onError }) => {
  const steps = [
    {
      title: "Elevation extraction",
      description: "Generating relative height from optical imagery",
    },
    {
      title: "Scale calibration",
      description: "Checking geographic and elevation references",
    },
    {
      title: "Mesh generation",
      description: "Preparing the terrain for 3D visualization",
    },
  ];

  // The backend runs Stage1->2->3 as a single request with no incremental
  // progress events, so this stepper animates on a fixed cadence purely as
  // a "something is happening" indicator -- it does NOT reflect real
  // pipeline progress. The actual completion/failure is driven entirely by
  // the /process request below; if it resolves before the animation
  // reaches the last step, the animation is cut short by onComplete firing.
  const [currentStep, setCurrentStep] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentStep((previousStep) =>
        previousStep < steps.length - 1 ? previousStep + 1 : previousStep,
      );
    }, 1800);

    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!imageId) {
      onError?.("No image was uploaded -- please go back and select a file.");
      return;
    }

    let cancelled = false;

    processImage(imageId)
      .then((result) => {
        if (!cancelled) onComplete(result);
      })
      .catch((error) => {
        if (!cancelled) {
          onError?.(
            error instanceof Error
              ? error.message
              : "Pipeline processing failed unexpectedly.",
          );
        }
      });

    return () => {
      cancelled = true;
    };
  }, [imageId, onComplete, onError]);

  const progressPercent = ((currentStep + 1) / steps.length) * 100;
  const activeStep = steps[currentStep];

  return (
    <section className="relative flex min-h-screen items-center overflow-hidden px-6 py-12">
      <div className="relative z-10 mx-auto w-full max-w-xl">
        {/* Focal animation */}
        <div className="mx-auto h-64 w-full overflow-hidden rounded-3xl border border-gray-100 bg-white/70 shadow-[0_1px_2px_rgba(11,19,36,0.04)] backdrop-blur-sm">
          <TerrainScanAnimation />
        </div>

        {/* Heading */}
        <div className="mt-8 text-center">
          <h2 className="font-display text-2xl font-bold text-ink">
            Processing your imagery
          </h2>

          <p className="mt-2 text-sm text-ink-soft">
            DepthWizard is reconstructing the terrain.
          </p>
        </div>

        {/* Progress bar */}
        <div className="mt-8">
          <div className="h-2.5 w-full overflow-hidden rounded-full bg-white/80 shadow-inner">
            <div
              className="h-full rounded-full bg-gradient-to-r from-blue-deep to-teal transition-[width] duration-700 ease-out"
              style={{ width: `${progressPercent}%` }}
            />
          </div>

          <p className="mt-4 text-center text-sm font-medium text-ink-soft">
            {activeStep.title} — {activeStep.description}
          </p>
        </div>

        {/* Status */}
        <div className="mt-5 rounded-xl border border-blue-100 bg-blue-50/80 px-4 py-3 text-center text-xs font-medium text-blue-700 backdrop-blur-sm">
          Running local processing pipeline
        </div>
      </div>
    </section>
  );
};

export default ProcessingView;
