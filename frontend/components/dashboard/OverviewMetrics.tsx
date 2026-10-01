"use client";

import React from "react";
import type { DatasetAnalysisResponse, DatasetProfileResponse } from "@/types";

interface OverviewMetricsProps {
  analysis: DatasetAnalysisResponse;
  profile: DatasetProfileResponse;
}

export function OverviewMetrics({ analysis, profile }: OverviewMetricsProps) {
  // Real numbers directly from backend response
  const totalProblems = analysis.total_issues;
  const criticalProblems = analysis.issues_by_severity?.high ?? 0;

  // Real missing values across all columns
  const totalMissingValues = React.useMemo(() => {
    return profile.columns.reduce((sum, col) => sum + (col.null_count || 0), 0);
  }, [profile.columns]);

  // Real duplicate rows count from issues
  const duplicateRows = React.useMemo(() => {
    const dupIssue = analysis.issues.find((i) => i.type === "duplicate_rows");
    return dupIssue ? dupIssue.affected_rows : 0;
  }, [analysis.issues]);

  // Real affected rows count (sum of issue affected rows, capped at total row count for realistic bounded presentation)
  const affectedRows = React.useMemo(() => {
    const rawSum = analysis.issues.reduce((sum, i) => sum + (i.affected_rows || 0), 0);
    // If multiple issues affect the same rows, cap at total rows
    return Math.min(rawSum, profile.general.row_count);
  }, [analysis.issues, profile.general.row_count]);

  const affectedPercentage = profile.general.row_count > 0
    ? ((affectedRows / profile.general.row_count) * 100).toFixed(1)
    : "0.0";

  return (
    <div className="mb-6 grid grid-cols-2 lg:grid-cols-5 gap-3.5 sm:gap-4">
      {/* 1. Total Problems */}
      <div className="rounded-2xl border border-white/[0.08] bg-[#161a2e]/80 backdrop-blur-xl p-4 sm:p-5 shadow-xl">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
            Total Problems
          </span>
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-indigo-500/10 text-indigo-400">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </span>
        </div>
        <div className="mt-3 flex items-baseline gap-2">
          <span className="text-2xl sm:text-3xl font-bold font-mono text-white">
            {totalProblems.toLocaleString()}
          </span>
          <span className="text-xs text-slate-400">issues</span>
        </div>
        <p className="mt-1 text-[11px] text-slate-400">
          Detected by deterministic checks
        </p>
      </div>

      {/* 2. Critical Problems */}
      <div className="rounded-2xl border border-white/[0.08] bg-[#161a2e]/80 backdrop-blur-xl p-4 sm:p-5 shadow-xl">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
            Critical Problems
          </span>
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-rose-500/10 text-rose-400">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </span>
        </div>
        <div className="mt-3 flex items-baseline gap-2">
          <span className={`text-2xl sm:text-3xl font-bold font-mono ${criticalProblems > 0 ? "text-rose-400" : "text-emerald-400"}`}>
            {criticalProblems.toLocaleString()}
          </span>
          <span className="text-xs text-slate-400">high severity</span>
        </div>
        <p className="mt-1 text-[11px] text-slate-400">
          Require immediate intervention
        </p>
      </div>

      {/* 3. Affected Rows */}
      <div className="rounded-2xl border border-white/[0.08] bg-[#161a2e]/80 backdrop-blur-xl p-4 sm:p-5 shadow-xl">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
            Affected Rows
          </span>
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-amber-500/10 text-amber-400">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
          </span>
        </div>
        <div className="mt-3 flex items-baseline gap-2">
          <span className="text-2xl sm:text-3xl font-bold font-mono text-white">
            {affectedRows.toLocaleString()}
          </span>
          <span className="text-xs text-amber-400 font-mono">({affectedPercentage}%)</span>
        </div>
        <p className="mt-1 text-[11px] text-slate-400">
          of {profile.general.row_count.toLocaleString()} total rows
        </p>
      </div>

      {/* 4. Missing Values */}
      <div className="rounded-2xl border border-white/[0.08] bg-[#161a2e]/80 backdrop-blur-xl p-4 sm:p-5 shadow-xl">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
            Missing Values
          </span>
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-sky-500/10 text-sky-400">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
            </svg>
          </span>
        </div>
        <div className="mt-3 flex items-baseline gap-2">
          <span className="text-2xl sm:text-3xl font-bold font-mono text-white">
            {totalMissingValues.toLocaleString()}
          </span>
          <span className="text-xs text-slate-400">cells</span>
        </div>
        <p className="mt-1 text-[11px] text-slate-400">
          Across {profile.columns.filter((c) => c.null_count > 0).length} columns
        </p>
      </div>

      {/* 5. Duplicate Rows */}
      <div className="rounded-2xl border border-white/[0.08] bg-[#161a2e]/80 backdrop-blur-xl p-4 sm:p-5 shadow-xl col-span-2 lg:col-span-1">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
            Duplicate Rows
          </span>
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-violet-500/10 text-violet-400">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
          </span>
        </div>
        <div className="mt-3 flex items-baseline gap-2">
          <span className={`text-2xl sm:text-3xl font-bold font-mono ${duplicateRows > 0 ? "text-amber-400" : "text-emerald-400"}`}>
            {duplicateRows.toLocaleString()}
          </span>
          <span className="text-xs text-slate-400">rows</span>
        </div>
        <p className="mt-1 text-[11px] text-slate-400">
          Exact row-level duplicates
        </p>
      </div>
    </div>
  );
}
