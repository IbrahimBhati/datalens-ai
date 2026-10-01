"use client";

import { useState } from "react";

export function UploadPlaceholder() {
  const [isHovered, setIsHovered] = useState(false);

  return (
    <div className="w-full max-w-2xl mx-auto px-4 my-8">
      <div
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        className={`relative group rounded-2xl border-2 border-dashed transition-all duration-300 p-8 sm:p-12 text-center bg-gradient-to-b from-[#161a2e]/80 to-[#111427]/80 backdrop-blur-xl ${
          isHovered
            ? "border-indigo-500/80 shadow-[0_0_40px_rgba(99,102,241,0.15)] scale-[1.005]"
            : "border-white/[0.12] hover:border-white/[0.25]"
        }`}
      >
        {/* Glow ambient background */}
        <div className="absolute inset-0 -z-10 rounded-2xl bg-indigo-600/[0.04] blur-xl pointer-events-none" />

        {/* Upload Icon */}
        <div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-2xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 group-hover:scale-110 group-hover:text-indigo-300 transition-all duration-300">
          <svg
            className="h-8 w-8"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1.75}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
            />
          </svg>
        </div>

        {/* Action Title */}
        <h3 className="text-xl font-semibold text-white tracking-tight">
          Upload Dataset for Analysis
        </h3>

        {/* Description */}
        <p className="mt-2 text-sm text-slate-400 max-w-md mx-auto leading-relaxed">
          Drag and drop your dataset file here, or click to browse from your computer. Supports structured CSV and JSON data.
        </p>

        {/* Action Button Placeholder */}
        <div className="mt-6 flex flex-col sm:flex-row items-center justify-center gap-3">
          <button
            type="button"
            className="inline-flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-indigo-500 to-violet-600 px-6 py-2.5 text-sm font-semibold text-white shadow-lg shadow-indigo-500/25 hover:from-indigo-600 hover:to-violet-700 transition-all duration-200 cursor-pointer"
          >
            <svg
              className="h-4 w-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 4v16m8-8H4"
              />
            </svg>
            Select Dataset File
          </button>
        </div>

        {/* File constraints info */}
        <div className="mt-6 pt-5 border-t border-white/[0.06] flex items-center justify-center gap-4 text-xs text-slate-400">
          <span className="flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
            .csv, .json formats
          </span>
          <span className="text-white/[0.2]">•</span>
          <span>Max file size: 50 MB</span>
          <span className="text-white/[0.2]">•</span>
          <span>UTF-8 encoded</span>
        </div>
      </div>
    </div>
  );
}
