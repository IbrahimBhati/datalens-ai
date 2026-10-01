"use client";

import React from "react";
import type { DatasetAnalysisResponse, DatasetProfileResponse, QualityDimensions } from "@/types";

interface ChartsSectionProps {
  profile: DatasetProfileResponse;
  analysis: DatasetAnalysisResponse;
  dimensions: QualityDimensions;
}

export function ChartsSection({ profile, analysis, dimensions }: ChartsSectionProps) {
  // 1. Missing Values by Column Data
  const missingByColumn = React.useMemo(() => {
    return [...profile.columns]
      .sort((a, b) => b.null_percentage - a.null_percentage)
      .slice(0, 8); // Top 8 columns for clean layout
  }, [profile.columns]);

  // 2. Data-type Distribution Data
  const typeDistribution = React.useMemo(() => {
    const counts: Record<string, number> = {};
    for (const col of profile.columns) {
      const t = col.inferred_type || "unknown";
      counts[t] = (counts[t] || 0) + 1;
    }
    const total = profile.columns.length || 1;
    const colors: Record<string, { bg: string; fill: string; stroke: string }> = {
      numeric: { bg: "bg-indigo-500", fill: "#6366f1", stroke: "#818cf8" },
      text: { bg: "bg-sky-500", fill: "#0ea5e9", stroke: "#38bdf8" },
      categorical: { bg: "bg-emerald-500", fill: "#10b981", stroke: "#34d399" },
      datetime: { bg: "bg-violet-500", fill: "#8b5cf6", stroke: "#a78bfa" },
      boolean: { bg: "bg-amber-500", fill: "#f59e0b", stroke: "#fbbf24" },
      unknown: { bg: "bg-slate-500", fill: "#64748b", stroke: "#94a3b8" },
    };

    return Object.entries(counts).map(([type, count]) => ({
      type,
      count,
      percentage: Math.round((count / total) * 100),
      color: colors[type] || colors.unknown,
    }));
  }, [profile.columns]);

  // 3. Issue Severity Data
  const severityData = React.useMemo(() => {
    const high = analysis.issues_by_severity?.high || 0;
    const medium = analysis.issues_by_severity?.medium || 0;
    const low = analysis.issues_by_severity?.low || 0;
    const total = high + medium + low || 1;

    return [
      {
        label: "High (Critical)",
        count: high,
        pct: Math.round((high / total) * 100),
        barColor: "bg-rose-500",
        fillColor: "#f87171",
        textColor: "text-rose-400",
      },
      {
        label: "Medium (Warning)",
        count: medium,
        pct: Math.round((medium / total) * 100),
        barColor: "bg-amber-500",
        fillColor: "#fbbf24",
        textColor: "text-amber-400",
      },
      {
        label: "Low (Notice)",
        count: low,
        pct: Math.round((low / total) * 100),
        barColor: "bg-sky-500",
        fillColor: "#38bdf8",
        textColor: "text-sky-400",
      },
    ];
  }, [analysis.issues_by_severity]);

  // 4. Quality Dimensions Chart Data
  const dimensionList = React.useMemo(() => {
    return [
      { name: "Completeness", score: dimensions.completeness, color: "bg-emerald-400" },
      { name: "Validity", score: dimensions.validity, color: "bg-indigo-400" },
      { name: "Uniqueness", score: dimensions.uniqueness, color: "bg-sky-400" },
      { name: "Consistency", score: dimensions.consistency, color: "bg-violet-400" },
    ];
  }, [dimensions]);

  return (
    <div className="mb-6 grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
      {/* ---------------- CHART 1: Missing Values by Column ---------------- */}
      <div className="rounded-2xl border border-white/[0.08] bg-[#161a2e]/80 backdrop-blur-xl p-5 sm:p-6 shadow-xl flex flex-col justify-between">
        <div>
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300">
                Missing Values by Column
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Columns ranked by null rate
              </p>
            </div>
            <span className="text-xs font-mono text-slate-400">
              {profile.columns.filter((c) => c.null_count > 0).length} columns with nulls
            </span>
          </div>

          <div className="space-y-3 mt-3">
            {missingByColumn.map((col) => {
              const nullPct = col.null_percentage || 0;
              const barColor =
                nullPct > 20
                  ? "bg-rose-500"
                  : nullPct > 5
                  ? "bg-amber-400"
                  : nullPct > 0
                  ? "bg-sky-400"
                  : "bg-emerald-400";

              return (
                <div key={col.name} className="text-xs">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-mono text-slate-300 truncate max-w-[180px] sm:max-w-[240px]">
                      {col.name}
                    </span>
                    <span className="font-mono text-slate-400">
                      {col.null_count.toLocaleString()} nulls ({nullPct.toFixed(1)}%)
                    </span>
                  </div>
                  <div className="h-2 w-full overflow-hidden rounded-full bg-white/[0.08]">
                    <div
                      className={`h-full ${barColor} rounded-full transition-all duration-300`}
                      style={{ width: `${Math.min(100, Math.max(nullPct > 0 ? 3 : 0, nullPct))}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="mt-4 pt-3 border-t border-white/[0.06] flex items-center justify-between text-[11px] text-slate-400">
          <span className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-rose-500 inline-block" /> &gt;20% severe
          </span>
          <span className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-amber-400 inline-block" /> 5-20% moderate
          </span>
          <span className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-emerald-400 inline-block" /> 0% clean
          </span>
        </div>
      </div>

      {/* ---------------- CHART 2: Data-Type Distribution ---------------- */}
      <div className="rounded-2xl border border-white/[0.08] bg-[#161a2e]/80 backdrop-blur-xl p-5 sm:p-6 shadow-xl flex flex-col justify-between">
        <div>
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300">
                Data-Type Distribution
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Inferred column types ({profile.columns.length} total)
              </p>
            </div>
            <span className="text-xs font-mono text-slate-400">
              {typeDistribution.length} types detected
            </span>
          </div>

          {/* Proportional Stacked Bar */}
          <div className="my-5">
            <div className="h-4 w-full overflow-hidden rounded-xl bg-white/[0.08] flex">
              {typeDistribution.map((item) => (
                <div
                  key={item.type}
                  className={`${item.color.bg} transition-all hover:opacity-90 relative group`}
                  style={{ width: `${Math.max(item.percentage, 4)}%` }}
                  title={`${item.type}: ${item.count} columns (${item.percentage}%)`}
                />
              ))}
            </div>
          </div>

          {/* Grid Legend */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 mt-4">
            {typeDistribution.map((item) => (
              <div
                key={item.type}
                className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-2.5 flex items-center gap-2.5"
              >
                <span className={`h-3 w-3 rounded-full ${item.color.bg} shrink-0`} />
                <div className="min-w-0">
                  <span className="text-xs font-medium text-white capitalize block truncate">
                    {item.type}
                  </span>
                  <span className="text-[11px] font-mono text-slate-400">
                    {item.count} cols ({item.percentage}%)
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-4 pt-3 border-t border-white/[0.06] text-right text-[11px] text-slate-400">
          Inferred via deterministic type profiling
        </div>
      </div>

      {/* ---------------- CHART 3: Quality Dimensions Visual ---------------- */}
      <div className="rounded-2xl border border-white/[0.08] bg-[#161a2e]/80 backdrop-blur-xl p-5 sm:p-6 shadow-xl flex flex-col justify-between">
        <div>
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300">
                Quality Dimensions Overview
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Side-by-side benchmark comparison
              </p>
            </div>
            <span className="inline-flex items-center rounded-md bg-white/[0.05] border border-white/[0.08] px-2 py-0.5 text-[10px] font-semibold text-slate-300">
              Benchmark: 85%
            </span>
          </div>

          <div className="space-y-4 my-3">
            {dimensionList.map((dim) => (
              <div key={dim.name}>
                <div className="flex items-center justify-between text-xs mb-1">
                  <span className="font-medium text-white">{dim.name}</span>
                  <span className="font-mono font-bold text-slate-300">
                    {dim.score}%
                  </span>
                </div>
                <div className="relative h-3 w-full rounded-full bg-white/[0.08] overflow-hidden">
                  {/* Benchmark indicator line at 85% */}
                  <div
                    className="absolute top-0 bottom-0 w-[2px] bg-white/40 z-10"
                    style={{ left: "85%" }}
                    title="Target Benchmark (85%)"
                  />
                  <div
                    className={`h-full ${dim.color} rounded-full transition-all duration-500`}
                    style={{ width: `${Math.min(100, Math.max(0, dim.score))}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-4 pt-3 border-t border-white/[0.06] flex items-center justify-between text-[11px] text-slate-400">
          <span>Target benchmark line shown at 85%</span>
          <span>4 core evaluation axes</span>
        </div>
      </div>

      {/* ---------------- CHART 4: Issue Severity Breakdown ---------------- */}
      <div className="rounded-2xl border border-white/[0.08] bg-[#161a2e]/80 backdrop-blur-xl p-5 sm:p-6 shadow-xl flex flex-col justify-between">
        <div>
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300">
                Issue Severity Breakdown
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Categorized risk distribution ({analysis.total_issues} issues)
              </p>
            </div>
            <span className="text-xs font-mono text-slate-400">
              {analysis.total_issues} total
            </span>
          </div>

          {/* Stacked Proportional Bar */}
          <div className="my-5">
            <div className="h-4 w-full overflow-hidden rounded-xl bg-white/[0.08] flex">
              {severityData.map((item) => (
                <div
                  key={item.label}
                  className={`${item.barColor} transition-all hover:opacity-90`}
                  style={{ width: `${analysis.total_issues > 0 ? Math.max(item.pct, item.count > 0 ? 5 : 0) : 0}%` }}
                  title={`${item.label}: ${item.count} issues (${item.pct}%)`}
                />
              ))}
            </div>
          </div>

          {/* Metrics List */}
          <div className="space-y-3 mt-4">
            {severityData.map((item) => (
              <div
                key={item.label}
                className="flex items-center justify-between rounded-xl border border-white/[0.05] bg-white/[0.02] p-3 text-xs"
              >
                <div className="flex items-center gap-2">
                  <span className={`h-2.5 w-2.5 rounded-full ${item.barColor}`} />
                  <span className="font-medium text-white">{item.label}</span>
                </div>
                <div className="flex items-center gap-3 font-mono">
                  <span className={`font-bold ${item.textColor}`}>
                    {item.count} issues
                  </span>
                  <span className="text-slate-500">
                    ({item.pct}%)
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-4 pt-3 border-t border-white/[0.06] text-right text-[11px] text-slate-400">
          Ranked by remediation urgency
        </div>
      </div>
    </div>
  );
}
