"use client";

import React from "react";
import type { AiInsightResponse } from "@/types";

interface AiInsightsSectionProps {
  insights: AiInsightResponse;
}

export function AiInsightsSection({ insights }: AiInsightsSectionProps) {
  const isLlm = insights.source === "llm";

  const getImportanceBadge = (importance: string) => {
    const imp = (importance || "").toLowerCase();
    if (imp.includes("critical") || imp.includes("high")) {
      return "border-rose-500/30 bg-rose-500/15 text-rose-300";
    }
    if (imp.includes("medium") || imp.includes("warning")) {
      return "border-amber-500/30 bg-amber-500/15 text-amber-300";
    }
    return "border-sky-500/30 bg-sky-500/15 text-sky-300";
  };

  return (
    <div className="rounded-2xl border border-indigo-500/30 bg-gradient-to-b from-[#161a2e]/90 to-[#121528]/90 backdrop-blur-xl p-5 sm:p-6 shadow-2xl shadow-indigo-500/5 mb-6">
      {/* Section Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-5 border-b border-white/[0.08]">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 text-white shadow-md shadow-indigo-500/20">
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <div>
            <h2 className="text-base font-semibold text-white tracking-tight">
              AI-Powered Quality Insights & Remediation
            </h2>
            <p className="text-xs text-slate-400">
              Executive interpretation and prioritized cleaning roadmap
            </p>
          </div>
        </div>

        {/* Source Badge */}
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-indigo-500/30 bg-indigo-500/10 px-3 py-1 text-xs font-medium text-indigo-300">
            <span className="h-1.5 w-1.5 rounded-full bg-indigo-400 animate-pulse" />
            {isLlm ? "LLM Interpretation" : "Rule Engine Fallback"}
          </span>
        </div>
      </div>

      {/* 1. Executive Summary */}
      <div className="mt-5 rounded-xl border border-white/[0.06] bg-white/[0.02] p-4 sm:p-5">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-indigo-400 mb-2 flex items-center gap-1.5">
          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          Executive Summary
        </h3>
        <p className="text-sm text-slate-200 leading-relaxed">
          {insights.summary}
        </p>
      </div>

      {/* 2. Priority Issues Grid */}
      <div className="mt-6">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3">
          Most Important Data-Quality Problems & Recommendations
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {insights.priority_issues.map((issue, idx) => (
            <div
              key={idx}
              className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-4 flex flex-col justify-between hover:border-white/[0.12] transition-colors"
            >
              <div>
                <div className="flex items-start justify-between gap-3 mb-2.5">
                  <h4 className="text-sm font-semibold text-white">
                    {issue.issue}
                  </h4>
                  <span className={`inline-flex items-center rounded-md border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider font-mono shrink-0 ${getImportanceBadge(issue.importance)}`}>
                    {issue.importance}
                  </span>
                </div>

                <div className="mb-3">
                  <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 block mb-1">
                    Why It Matters
                  </span>
                  <p className="text-xs text-slate-300 leading-relaxed">
                    {issue.explanation}
                  </p>
                </div>
              </div>

              <div className="pt-3 border-t border-white/[0.06]">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-emerald-400 block mb-1">
                  Recommended Action
                </span>
                <p className="text-xs text-slate-300 leading-relaxed">
                  {issue.recommendation}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 3. Actionable Cleaning Plan */}
      <div className="mt-6 rounded-xl border border-white/[0.06] bg-white/[0.02] p-4 sm:p-5">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-emerald-400 mb-3 flex items-center gap-1.5">
          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
          </svg>
          Suggested Cleaning Sequence & Priorities
        </h3>
        <div className="space-y-2.5">
          {insights.cleaning_plan.map((step, idx) => (
            <div key={idx} className="flex items-start gap-3 rounded-lg border border-white/[0.04] bg-white/[0.01] p-3 text-xs">
              <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-emerald-500/10 text-emerald-400 font-mono text-[10px] font-bold border border-emerald-500/20">
                {idx + 1}
              </span>
              <span className="text-slate-200 leading-relaxed">{step}</span>
            </div>
          ))}
        </div>
      </div>

      {/* 4. Text-Column Quality Observations (if applicable) */}
      {insights.text_observations && insights.text_observations.length > 0 && (
        <div className="mt-6 rounded-xl border border-white/[0.06] bg-white/[0.02] p-4 sm:p-5">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-sky-400 mb-2 flex items-center gap-1.5">
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z" />
            </svg>
            Text Column Quality Observations
          </h3>
          <ul className="space-y-1.5 text-xs text-slate-300">
            {insights.text_observations.map((obs, idx) => (
              <li key={idx} className="flex items-start gap-2">
                <span className="text-sky-400 font-mono text-xs">•</span>
                <span className="leading-snug">{obs}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
