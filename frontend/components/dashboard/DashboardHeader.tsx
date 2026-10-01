"use client";

import React from "react";
import { getDatasetPdfReportUrl, getDatasetHtmlReportUrl } from "@/lib/api";

interface DashboardHeaderProps {
  datasetId: string;
  filename: string;
  format: string;
  rowCount: number;
  columnCount: number;
  analyzedAt: string;
  onNewUpload?: () => void;
}

export function DashboardHeader({
  datasetId,
  filename,
  format,
  rowCount,
  columnCount,
  analyzedAt,
  onNewUpload,
}: DashboardHeaderProps) {
  const formattedDate = React.useMemo(() => {
    try {
      const d = new Date(analyzedAt);
      if (isNaN(d.getTime())) return analyzedAt;
      return d.toLocaleString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
        hour: "numeric",
        minute: "2-digit",
        hour12: true,
      });
    } catch {
      return analyzedAt;
    }
  }, [analyzedAt]);

  const handleDownloadPdf = () => {
    const url = getDatasetPdfReportUrl(datasetId);
    window.open(url, "_blank");
  };

  const handleViewHtmlReport = () => {
    const url = getDatasetHtmlReportUrl(datasetId);
    window.open(url, "_blank");
  };

  return (
    <header className="rounded-2xl border border-white/[0.08] bg-[#161a2e]/80 backdrop-blur-xl p-5 sm:p-6 shadow-xl mb-6">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-5">
        {/* Dataset Info */}
        <div className="flex items-start sm:items-center gap-4">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 shadow-inner">
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2.5">
              <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white font-mono break-all">
                {filename}
              </h1>
              <span className="inline-flex items-center rounded-md bg-indigo-500/15 border border-indigo-500/30 px-2.5 py-0.5 text-xs font-bold uppercase tracking-wider text-indigo-300 font-mono">
                {format}
              </span>
            </div>
            <p className="mt-1 text-xs text-slate-400 flex items-center gap-2">
              <span className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-400" />
              Analyzed on <span className="text-slate-300 font-medium">{formattedDate}</span>
            </p>
          </div>
        </div>

        {/* Stats Pill & Actions */}
        <div className="flex flex-wrap items-center gap-2.5 sm:gap-3">
          <div className="flex items-center divide-x divide-white/[0.08] rounded-xl border border-white/[0.08] bg-white/[0.02] px-4 py-2 text-xs">
            <div className="pr-4">
              <span className="text-slate-400 block text-[10px] uppercase tracking-wider font-semibold">Rows</span>
              <span className="text-sm font-bold text-white font-mono">{rowCount.toLocaleString()}</span>
            </div>
            <div className="pl-4">
              <span className="text-slate-400 block text-[10px] uppercase tracking-wider font-semibold">Columns</span>
              <span className="text-sm font-bold text-white font-mono">{columnCount.toLocaleString()}</span>
            </div>
          </div>

          {/* Export PDF Button */}
          <button
            type="button"
            onClick={handleDownloadPdf}
            className="inline-flex items-center gap-1.5 rounded-xl bg-gradient-to-r from-indigo-500 to-violet-600 px-3.5 py-2 text-xs font-semibold text-white shadow-md shadow-indigo-500/20 hover:from-indigo-600 hover:to-violet-700 transition-all cursor-pointer"
            title="Download executive PDF dataset quality report"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            Export PDF
          </button>

          {/* View Print-Ready HTML Report Button */}
          <button
            type="button"
            onClick={handleViewHtmlReport}
            className="inline-flex items-center gap-1.5 rounded-xl border border-white/[0.1] bg-white/[0.05] hover:bg-white/[0.1] px-3.5 py-2 text-xs font-semibold text-slate-200 hover:text-white transition-all cursor-pointer"
            title="Open printable HTML report in a new tab"
          >
            <svg className="h-4 w-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
            </svg>
            Print Report
          </button>

          {onNewUpload && (
            <button
              type="button"
              onClick={onNewUpload}
              className="inline-flex items-center gap-1.5 rounded-xl border border-white/[0.1] bg-white/[0.03] hover:bg-white/[0.08] px-3 py-2 text-xs font-medium text-slate-400 hover:text-white transition-all cursor-pointer"
              title="Upload another dataset"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
              </svg>
              Upload New
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
