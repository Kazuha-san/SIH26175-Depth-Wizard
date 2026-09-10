import React from "react";
import StatCard from "./StatCard";

const Sidebar = () => {
  return (
    <aside className="w-full space-y-4 lg:w-[320px]">
      {/* DSM Statistics */}
      <div>
        <div className="mb-3">
          <h3 className="text-sm font-bold text-gray-900">DSM Statistics</h3>

          <p className="mt-1 text-xs text-gray-500">
            Current terrain reconstruction
          </p>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <StatCard label="Minimum" value="-0.19 m" />

          <StatCard label="Maximum" value="12.04 m" />

          <StatCard label="Resolution" value="128 × 128" />

          <StatCard label="Model" value="Relative" />
        </div>
      </div>

      {/* Calibration */}
      <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold text-gray-900">Calibration</h3>

          <span className="rounded-full bg-gray-100 px-2.5 py-1 text-[10px] font-semibold text-gray-500">
            NOT APPLIED
          </span>
        </div>

        <p className="mt-3 text-sm leading-5 text-gray-500">
          No geographic metadata is available for this input. The current
          terrain is displayed using relative height values.
        </p>
      </div>

      {/* Metadata */}
      <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
        <h3 className="text-sm font-bold text-gray-900">Input Metadata</h3>

        <div className="mt-4 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-500">CRS</span>
            <span className="text-xs font-semibold text-gray-700">
              Unavailable
            </span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-500">GSD</span>
            <span className="text-xs font-semibold text-gray-700">0.33 m*</span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-500">SRTM</span>
            <span className="text-xs font-semibold text-gray-700">
              Not used
            </span>
          </div>
        </div>

        <p className="mt-4 text-[10px] leading-4 text-gray-400">
          * Assumed value because source metadata is unavailable.
        </p>
      </div>
    </aside>
  );
};

export default Sidebar;
