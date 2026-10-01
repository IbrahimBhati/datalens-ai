"use client";

import React from "react";

interface AnalysisLoadingStateProps {
  filename: string;
  stepMessage?: string;
}

export function AnalysisLoadingState({
  filename,
  stepMessage = "Running deep deterministic profiling and AI analysis...",
}: AnalysisLoadingStateProps) {
  return (
    <div className="w-full max-w-xl mx-auto px-4 py-16 text-center">
      <div className="rounded-2xl border border-indigo-500/30 bg-[#161a2e]/90 backdrop-blur-xl p-8 sm:p-10 shadow-2xl shadow-indigo-500/10">
        {/* Pulsing AI Spinner */}
        <div className="relative mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-indigo-500/15 border border-indigo-500/30 text-indigo-400">
          <svg
            className="h-8 w-8 animate-spin text-indigo-400"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
        </div>

        <h3 className="text-xl font-bold text-white tracking-tight">
          Analyzing Dataset
        </h3>
        <p className="mt-1 font-mono text-xs text-indigo-300 truncate max-w-sm mx-auto">
          {filename}
        </p>

        <p className="mt-4 text-xs text-slate-400 max-w-md mx-auto leading-relaxed">
          {stepMessage}
        </p>

        {/* Step Checkpoints */}
        <div className="mt-8 space-y-2.5 text-left text-xs text-slate-300 max-w-sm mx-auto">
          <div className="flex items-center gap-2.5">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            <span>Profiling schema & distributions</span>
          </div>
          <div className="flex items-center gap-2.5">
            <span className="h-2 w-2 rounded-full bg-indigo-400 animate-pulse" />
            <span>Detecting missing values, duplicates & outliers</span>
          </div>
          <div className="flex items-center gap-2.5">
            <span className="h-2 w-2 rounded-full bg-violet-400 animate-pulse" />
            <span>Computing multidimensional quality scores</span>
          </div>
          <div className="flex items-center gap-2.5">
            <span className="h-2 w-2 rounded-full bg-sky-400 animate-pulse" />
            <span>Generating privacy-preserving AI insights</span>
          </div>
        </div>
      </div>
    </div>
  );
}
