import React, { useEffect, useState } from "react";

const ProcessingView = ({ onComplete }) => {
  const steps = [
    {
      title: "Elevation Extraction",
      description: "Generating relative height from optical imagery",
    },
    {
      title: "Scale Calibration",
      description: "Checking geographic and elevation references",
    },
    {
      title: "Mesh Generation",
      description: "Preparing the terrain for 3D visualization",
    },
  ];

  const [currentStep, setCurrentStep] = useState(0);

  useEffect(() => {
    let completionTimer;

    const interval = setInterval(() => {
      setCurrentStep((previousStep) => {
        if (previousStep < steps.length - 1) {
          return previousStep + 1;
        }

        clearInterval(interval);

        completionTimer = setTimeout(() => {
          onComplete();
        }, 800);

        return previousStep;
      });
    }, 1800);

    return () => {
      clearInterval(interval);

      if (completionTimer) {
        clearTimeout(completionTimer);
      }
    };
  }, [onComplete]);

  return (
    <section className="min-h-[calc(100vh-64px)] px-6 py-12">
      <div className="mx-auto max-w-3xl">
        {/* Heading */}
        <div className="text-center">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-50 text-xl text-blue-600">
            ◌
          </div>

          <h2 className="mt-5 text-2xl font-bold text-gray-900">
            Processing your imagery
          </h2>

          <p className="mt-2 text-sm text-gray-500">
            DepthWizard is reconstructing the terrain step by step.
          </p>
        </div>

        {/* Stepper */}
        <div className="mt-10 rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
          {steps.map((step, index) => {
            const isCompleted = index < currentStep;

            const isActive = index === currentStep;

            return (
              <div key={step.title} className="flex gap-4">
                <div className="flex flex-col items-center">
                  <div
                    className={`
                      flex h-10 w-10
                      shrink-0 items-center
                      justify-center
                      rounded-full
                      text-sm font-bold

                      ${
                        isCompleted
                          ? "bg-green-100 text-green-600"
                          : isActive
                            ? "bg-blue-600 text-white"
                            : "bg-gray-100 text-gray-400"
                      }
                    `}
                  >
                    {isCompleted ? "✓" : index + 1}
                  </div>

                  {index !== steps.length - 1 && (
                    <div className="my-2 h-12 w-px bg-gray-200" />
                  )}
                </div>

                <div className="pb-8">
                  <h3
                    className={`
                      font-semibold
                      ${
                        isActive || isCompleted
                          ? "text-gray-900"
                          : "text-gray-400"
                      }
                    `}
                  >
                    {step.title}
                  </h3>

                  <p className="mt-1 text-sm text-gray-500">
                    {step.description}
                  </p>

                  {isActive && (
                    <div className="mt-3 flex items-center gap-2 text-xs font-medium text-blue-600">
                      <span className="h-2 w-2 animate-pulse rounded-full bg-blue-600" />
                      Processing...
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Status */}
        <div className="mt-5 rounded-xl border border-blue-100 bg-blue-50 px-4 py-3 text-center text-xs font-medium text-blue-700">
          Running local processing pipeline
        </div>
      </div>
    </section>
  );
};

export default ProcessingView;
