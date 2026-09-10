import React from "react";

const Navbar = ({
  currentView,
  setCurrentView,
  onNewImage,
  hasUploadedImage = false,
  hasResult = false,
}) => {
  const navItems = [
    {
      id: "upload",
      label: "Upload",
      enabled: true,
    },
    {
      id: "processing",
      label: "Processing",
      enabled: hasUploadedImage,
    },
    {
      id: "results",
      label: "Results",
      enabled: hasResult,
    },
  ];

  const handleNavigation = (item) => {
    if (!item.enabled) return;

    setCurrentView(item.id);
  };

  return (
    <header className="sticky top-0 z-50 border-b border-gray-200 bg-white/95 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-[1600px] items-center justify-between px-6">
        {/* Logo */}
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-blue-600 text-sm font-bold text-white shadow-sm">
            D
          </div>

          <div>
            <h1 className="text-base font-bold tracking-tight text-gray-900">
              DepthWizard
            </h1>

            <p className="text-[11px] font-medium text-gray-500">
              Terrain Reconstruction
            </p>
          </div>
        </div>

        {/* Navigation */}
        <nav className="hidden items-center gap-1 rounded-xl bg-gray-100 p-1 md:flex">
          {navItems.map((item) => {
            const isActive = currentView === item.id;

            const isDisabled = !item.enabled;

            return (
              <button
                key={item.id}
                type="button"
                disabled={isDisabled}
                onClick={() => handleNavigation(item)}
                className={`
                  rounded-lg px-4 py-2
                  text-sm font-medium
                  transition-all duration-200

                  ${
                    isActive
                      ? "bg-white text-blue-600 shadow-sm"
                      : isDisabled
                        ? "cursor-not-allowed text-gray-300"
                        : "text-gray-500 hover:bg-white/70 hover:text-gray-900"
                  }
                `}
              >
                {item.label}

                {isDisabled && item.id !== "upload" && (
                  <span className="ml-1 text-[9px] opacity-70">🔒</span>
                )}
              </button>
            );
          })}
        </nav>

        {/* New Image */}
        <button
          type="button"
          onClick={onNewImage}
          className="
            rounded-lg
            border border-gray-200
            bg-white
            px-4 py-2
            text-sm font-semibold
            text-gray-700
            transition
            hover:border-blue-200
            hover:bg-blue-50
            hover:text-blue-600
          "
        >
          + New Image
        </button>
      </div>
    </header>
  );
};

export default Navbar;
