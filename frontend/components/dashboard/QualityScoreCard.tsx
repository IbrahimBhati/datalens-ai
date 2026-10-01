"use client";

import React from "react";

interface QualityScoreCardProps {
  score: number; // 0 - 100
  explanations?: string[];
}

export function QualityScoreCard({ score, explanations = [] }: QualityScoreCardProps) {
  // Determine tier & color styling based on real calculated score
  const { tier, colorClass, strokeColor, glowColor, bgTint } = React.useMemo(() => {
    if (score >= 85) {
      return {
        tier: "Excellent Quality",
        colorClass: "text-emerald-400",
        strokeColor: "#34d399",
        glowColor: "rgba(52, 211, 153, 0.25)",
        bgTint: "border-emerald-500/30 bg-emerald-500/[0.03]",
      };
    } else if (score >= 70) {
      return {
        tier: "Good Quality",
        colorClass: "text-indigo-400",
        strokeColor: "#818cf8",
        glowColor: "rgba(129, 140, 248, 0.25)",
        bgTint: "border-indigo-500/30 bg-indigo-500/[0.03]",
      };
    } else if (score >= 50) {
      return {
        tier: "Fair / Moderate Issues",
        colorClass: "text-amber-400",
        strokeColor: "#fbbf24",
        glowColor: "rgba(251, 191, 36, 0.25)",
        bgTint: "border-amber-500/30 bg-amber-500/[0.03]",
      };
    } else {
      return {
        tier: "Critical Quality Alert",
        colorClass: "text-rose-400",
        strokeColor: "#f87171",
        glowColor: "rgba(248, 113, 113, 0.25)",
        bgTint: "border-rose-500/30 bg-rose-500/[0.03]",
      };
    }
  }, [score]);

  // SVG Gauge calculations
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (Math.min(100, Math.max(0, score)) / 100) * circumference;

  return (
    <div className={`rounded-2xl border ${bgTint} backdrop-blur-xl p-6 shadow-xl flex flex-col justify-between h-full`}>
      <div>
        <div className="flex items-center justify-between mb-4">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Overall Quality Score
          </span>
          <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-bold ${colorClass} bg-white/[0.05] border border-white/[0.08]`}>
            {tier}
          </span>
        </div>

        {/* Circular Gauge & Score Display */}
        <div className="flex flex-col sm:flex-row items-center gap-6 my-4">
          <div className="relative flex items-center justify-center shrink-0">
            <svg className="h-36 w-36 -rotate-90 transform" viewBox="0 0 130 130">
              {/* Background Track */}
              <circle
                cx="65"
                cy="65"
                r={radius}
                className="text-white/[0.08]"
                strokeWidth="10"
                stroke="currentColor"
                fill="transparent"
              />
              {/* Progress Ring */}
              <circle
                cx="65"
                cy="65"
                r={radius}
                stroke={strokeColor}
                strokeWidth="10"
                strokeDasharray={circumference}
                strokeDashoffset={strokeDashoffset}
                strokeLinecap="round"
                fill="transparent"
                style={{
                  transition: "stroke-dashoffset 0.8s ease-in-out",
                  filter: `drop-shadow(0 0 8px ${glowColor})`,
                }}
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
              <span className={`text-4xl font-extrabold tracking-tight ${colorClass} font-mono`}>
                {Math.round(score)}
              </span>
              <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">
                out of 100
              </span>
            </div>
          </div>

          <div className="flex-1 text-center sm:text-left">
            <h3 className="text-base font-semibold text-white">
              Deterministic Quality Index
            </h3>
            <p className="mt-1 text-xs text-slate-400 leading-relaxed">
              Calculated via weighted heuristic evaluation across completeness, validity, uniqueness, and consistency. No LLM estimation.
            </p>
          </div>
        </div>
      </div>

      {/* Explanations List */}
      {explanations.length > 0 && (
        <div className="mt-5 pt-4 border-t border-white/[0.08]">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 block mb-2">
            Score Deductions & Drivers
          </span>
          <ul className="space-y-1.5 text-xs text-slate-300">
            {explanations.map((exp, idx) => (
              <li key={idx} className="flex items-start gap-2">
                <span className="text-slate-500 font-mono text-[10px] mt-0.5">•</span>
                <span className="leading-snug">{exp}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
