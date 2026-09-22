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
    <header className="sticky top-0 z-50 border-b border-gray-100 bg-white/90 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-[1700px] items-center justify-between px-6">
        {/* Logo */}
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-blue-deep to-teal text-sm font-bold text-white shadow-sm">
            D
          </div>

          <div>
            <h1 className="font-display text-base font-bold tracking-tight text-ink">
              DepthWizard
            </h1>

            <p className="text-[11px] font-medium text-ink-soft">
              Terrain Reconstruction
            </p>
          </div>
        </div>

        {/* Navigation */}
        <nav className="hidden items-center gap-1 rounded-xl bg-surface p-1 md:flex">
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
                      ? "bg-white text-blue-deep shadow-sm"
                      : isDisabled
                        ? "cursor-not-allowed text-gray-300"
                        : "text-ink-soft hover:bg-white/70 hover:text-ink"
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
            text-ink
            transition
            hover:border-blue-200
            hover:bg-blue-50
            hover:text-blue-deep
          "
        >
          + New Image
        </button>
      </div>
    </header>
  );
};

export default Navbar;
