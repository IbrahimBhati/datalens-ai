"use client";

import React from "react";
import type { QualityDimensions } from "@/types";

interface DimensionScoresCardProps {
  dimensions: QualityDimensions;
}

interface DimensionConfig {
  key: keyof QualityDimensions;
  title: string;
  description: string;
  icon: React.ReactNode;
}

const DIMENSIONS: DimensionConfig[] = [
  {
    key: "completeness",
    title: "Completeness",
    description: "Evaluates missing cells, null percentages, and empty columns.",
    icon: (
      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  },
  {
    key: "validity",
    title: "Validity",
    description: "Measures adherence to schema formats, emails, phones, and ranges.",
    icon: (
      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    ),
  },
  {
    key: "uniqueness",
    title: "Uniqueness",
    description: "Detects duplicate rows and duplicate primary key identifiers.",
    icon: (
      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7v8a2 2 0 002 2h6M8 7V5a2 2 0 012-2h4.586a1 1 0 01.707.293l4.414 4.414a1 1 0 01.293.707V15a2 2 0 01-2 2h-2M8 7H6a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2v-2" />
      </svg>
    ),
  },
  {
    key: "consistency",
    title: "Consistency",
    description: "Identifies constant columns, low-variance fields, and statistical outliers.",
    icon: (
      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3" />
      </svg>
    ),
  },
];

function getScoreColor(val: number) {
  if (val >= 85) return { text: "text-emerald-400", bar: "bg-emerald-400", border: "border-emerald-500/20" };
  if (val >= 70) return { text: "text-indigo-400", bar: "bg-indigo-400", border: "border-indigo-500/20" };
  if (val >= 50) return { text: "text-amber-400", bar: "bg-amber-400", border: "border-amber-500/20" };
  return { text: "text-rose-400", bar: "bg-rose-400", border: "border-rose-500/20" };
}

export function DimensionScoresCard({ dimensions }: DimensionScoresCardProps) {
  return (
    <div className="rounded-2xl border border-white/[0.08] bg-[#161a2e]/80 backdrop-blur-xl p-6 shadow-xl flex flex-col justify-between h-full">
      <div>
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Quality Dimensions
          </h2>
          <span className="text-[11px] text-slate-400">Target: ≥ 85/100</span>
        </div>

        <div className="space-y-4">
          {DIMENSIONS.map((dim) => {
            const val = dimensions[dim.key] ?? 0;
            const colors = getScoreColor(val);

            return (
              <div key={dim.key} className="rounded-xl border border-white/[0.05] bg-white/[0.02] p-3.5">
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center gap-2">
                    <span className="text-slate-400">{dim.icon}</span>
                    <span className="text-sm font-semibold text-white">{dim.title}</span>
                  </div>
                  <span className={`text-sm font-bold font-mono ${colors.text}`}>
                    {val}
                    <span className="text-[11px] font-normal text-slate-500"> / 100</span>
                  </span>
                </div>

                <p className="text-[11px] text-slate-400 mb-2.5 leading-snug">
                  {dim.description}
                </p>

                {/* Progress Bar */}
                <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/[0.08]">
                  <div
                    className={`h-full ${colors.bar} transition-all duration-500 rounded-full`}
                    style={{ width: `${Math.min(100, Math.max(0, val))}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="mt-4 pt-3 border-t border-white/[0.06] text-right">
        <span className="text-[11px] text-slate-400">Weighted heuristic breakdown</span>
      </div>
    </div>
  );
}
