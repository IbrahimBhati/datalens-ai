"use client";

import React, { useState, useMemo } from "react";
import type { QualityIssue } from "@/types";

interface IssueTableProps {
  issues: QualityIssue[];
  totalRows: number;
}

type SeverityFilter = "all" | "high" | "medium" | "low";
type SortField = "severity" | "affected_rows" | "percentage" | "column" | "issue";
type SortDirection = "asc" | "desc";

export function IssueTable({ issues, totalRows }: IssueTableProps) {
  const [filter, setFilter] = useState<SeverityFilter>("all");
  const [searchTerm, setSearchTerm] = useState("");
  const [sortField, setSortField] = useState<SortField>("severity");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");

  // Severity counts
  const counts = useMemo(() => {
    return {
      all: issues.length,
      high: issues.filter((i) => i.severity.toLowerCase() === "high").length,
      medium: issues.filter((i) => i.severity.toLowerCase() === "medium").length,
      low: issues.filter((i) => i.severity.toLowerCase() === "low").length,
    };
  }, [issues]);

  // Filtered and Sorted Issues
  const processedIssues = useMemo(() => {
    let result = [...issues];

    // Filter by severity
    if (filter !== "all") {
      result = result.filter((i) => i.severity.toLowerCase() === filter);
    }

    // Filter by search query
    if (searchTerm.trim()) {
      const q = searchTerm.toLowerCase();
      result = result.filter(
        (i) =>
          (i.column && i.column.toLowerCase().includes(q)) ||
          i.type.toLowerCase().includes(q) ||
          i.description.toLowerCase().includes(q) ||
          i.method.toLowerCase().includes(q)
      );
    }

    // Sort
    const severityWeight: Record<string, number> = { high: 3, medium: 2, low: 1 };

    result.sort((a, b) => {
      let comparison = 0;
      switch (sortField) {
        case "severity":
          comparison = (severityWeight[a.severity.toLowerCase()] || 0) - (severityWeight[b.severity.toLowerCase()] || 0);
          break;
        case "affected_rows":
          comparison = a.affected_rows - b.affected_rows;
          break;
        case "percentage":
          comparison = a.percentage - b.percentage;
          break;
        case "column":
          comparison = (a.column || "").localeCompare(b.column || "");
          break;
        case "issue":
          comparison = a.type.localeCompare(b.type);
          break;
      }
      return sortDirection === "desc" ? -comparison : comparison;
    });

    return result;
  }, [issues, filter, searchTerm, sortField, sortDirection]);

  const toggleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortDirection("desc");
    }
  };

  const getSeverityBadge = (severity: string) => {
    const s = severity.toLowerCase();
    if (s === "high") {
      return (
        <span className="inline-flex items-center gap-1.5 rounded-md bg-rose-500/15 border border-rose-500/30 px-2 py-0.5 text-xs font-bold uppercase tracking-wider text-rose-300 font-mono">
          <span className="h-1.5 w-1.5 rounded-full bg-rose-400" />
          High
        </span>
      );
    }
    if (s === "medium") {
      return (
        <span className="inline-flex items-center gap-1.5 rounded-md bg-amber-500/15 border border-amber-500/30 px-2 py-0.5 text-xs font-bold uppercase tracking-wider text-amber-300 font-mono">
          <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
          Medium
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5 rounded-md bg-sky-500/15 border border-sky-500/30 px-2 py-0.5 text-xs font-bold uppercase tracking-wider text-sky-300 font-mono">
        <span className="h-1.5 w-1.5 rounded-full bg-sky-400" />
        Low
      </span>
    );
  };

  const formatIssueTitle = (typeStr: string) => {
    return typeStr
      .split("_")
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(" ");
  };

  return (
    <div className="rounded-2xl border border-white/[0.08] bg-[#161a2e]/80 backdrop-blur-xl p-5 sm:p-6 shadow-xl mb-6">
      {/* Header & Controls */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 mb-5 pb-5 border-b border-white/[0.08]">
        <div>
          <h2 className="text-base font-semibold text-white tracking-tight">
            Detected Data Quality Issues
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Deterministic findings categorized by severity and affected row count
          </p>
        </div>

        {/* Severity Filter Tabs & Search */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Tabs */}
          <div className="inline-flex rounded-xl bg-white/[0.04] p-1 border border-white/[0.08] text-xs">
            <button
              type="button"
              onClick={() => setFilter("all")}
              className={`rounded-lg px-3 py-1.5 font-medium transition-colors cursor-pointer ${
                filter === "all" ? "bg-indigo-600 text-white shadow" : "text-slate-400 hover:text-white"
              }`}
            >
              All ({counts.all})
            </button>
            <button
              type="button"
              onClick={() => setFilter("high")}
              className={`rounded-lg px-3 py-1.5 font-medium transition-colors cursor-pointer ${
                filter === "high" ? "bg-rose-600 text-white shadow" : "text-slate-400 hover:text-rose-300"
              }`}
            >
              Critical ({counts.high})
            </button>
            <button
              type="button"
              onClick={() => setFilter("medium")}
              className={`rounded-lg px-3 py-1.5 font-medium transition-colors cursor-pointer ${
                filter === "medium" ? "bg-amber-600 text-white shadow" : "text-slate-400 hover:text-amber-300"
              }`}
            >
              Warning ({counts.medium})
            </button>
            <button
              type="button"
              onClick={() => setFilter("low")}
              className={`rounded-lg px-3 py-1.5 font-medium transition-colors cursor-pointer ${
                filter === "low" ? "bg-sky-600 text-white shadow" : "text-slate-400 hover:text-sky-300"
              }`}
            >
              Notice ({counts.low})
            </button>
          </div>

          {/* Search Input */}
          <div className="relative">
            <input
              type="text"
              placeholder="Filter by column or issue..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-48 sm:w-64 rounded-xl border border-white/[0.1] bg-white/[0.03] px-3.5 py-1.5 text-xs text-white placeholder-slate-500 focus:border-indigo-400 focus:outline-none"
            />
            {searchTerm && (
              <button
                type="button"
                onClick={() => setSearchTerm("")}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-xs text-slate-400 hover:text-white"
              >
                ✕
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Table Container */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="border-b border-white/[0.08] text-[11px] font-semibold uppercase tracking-wider text-slate-400">
              <th
                className="pb-3 pr-4 cursor-pointer hover:text-white"
                onClick={() => toggleSort("severity")}
              >
                Severity {sortField === "severity" && (sortDirection === "asc" ? "↑" : "↓")}
              </th>
              <th
                className="pb-3 px-4 cursor-pointer hover:text-white"
                onClick={() => toggleSort("issue")}
              >
                Issue {sortField === "issue" && (sortDirection === "asc" ? "↑" : "↓")}
              </th>
              <th
                className="pb-3 px-4 cursor-pointer hover:text-white"
                onClick={() => toggleSort("column")}
              >
                Column {sortField === "column" && (sortDirection === "asc" ? "↑" : "↓")}
              </th>
              <th
                className="pb-3 px-4 cursor-pointer hover:text-white text-right"
                onClick={() => toggleSort("affected_rows")}
              >
                Affected Rows {sortField === "affected_rows" && (sortDirection === "asc" ? "↑" : "↓")}
              </th>
              <th
                className="pb-3 px-4 cursor-pointer hover:text-white text-right"
                onClick={() => toggleSort("percentage")}
              >
                Percentage {sortField === "percentage" && (sortDirection === "asc" ? "↑" : "↓")}
              </th>
              <th className="pb-3 pl-4">
                Explanation & Method
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.05]">
            {processedIssues.length > 0 ? (
              processedIssues.map((issue, idx) => (
                <tr key={`${issue.type}-${issue.column}-${idx}`} className="hover:bg-white/[0.02] transition-colors">
                  {/* Severity */}
                  <td className="py-3.5 pr-4 whitespace-nowrap">
                    {getSeverityBadge(issue.severity)}
                  </td>

                  {/* Issue */}
                  <td className="py-3.5 px-4 font-semibold text-white whitespace-nowrap">
                    {formatIssueTitle(issue.type)}
                  </td>

                  {/* Column */}
                  <td className="py-3.5 px-4 whitespace-nowrap font-mono text-slate-300">
                    {issue.column ? (
                      <span className="inline-flex items-center rounded bg-white/[0.04] border border-white/[0.08] px-2 py-0.5 text-xs text-indigo-300">
                        {issue.column}
                      </span>
                    ) : (
                      <span className="text-slate-500 italic">Entire Dataset</span>
                    )}
                  </td>

                  {/* Affected Rows */}
                  <td className="py-3.5 px-4 text-right font-mono font-bold text-white whitespace-nowrap">
                    {issue.affected_rows.toLocaleString()}
                  </td>

                  {/* Percentage */}
                  <td className="py-3.5 px-4 text-right font-mono text-slate-300 whitespace-nowrap">
                    <span className={`font-semibold ${issue.percentage > 20 ? "text-rose-400" : issue.percentage > 5 ? "text-amber-400" : "text-slate-300"}`}>
                      {issue.percentage.toFixed(1)}%
                    </span>
                  </td>

                  {/* Explanation */}
                  <td className="py-3.5 pl-4 min-w-[280px]">
                    <div className="text-slate-300 leading-snug">
                      {issue.description}
                    </div>
                    <div className="mt-1 text-[10px] text-slate-500 font-mono">
                      Method: {issue.method}
                    </div>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={6} className="py-12 text-center text-slate-400">
                  <div className="mx-auto mb-2 flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-500/10 text-emerald-400">
                    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <span className="text-sm font-medium text-white block">
                    No matching quality issues found
                  </span>
                  <span className="text-xs text-slate-500">
                    {searchTerm ? "Try clearing your search term." : "This dataset passed all corresponding checks."}
                  </span>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Footer count */}
      <div className="mt-4 pt-3 border-t border-white/[0.06] flex items-center justify-between text-[11px] text-slate-400">
        <span>Showing {processedIssues.length} of {issues.length} detected problems</span>
        <span>Based on {totalRows.toLocaleString()} rows analyzed</span>
      </div>
    </div>
  );
}
