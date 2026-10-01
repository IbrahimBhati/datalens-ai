"use client";

import React, { useState, useCallback } from "react";
import { cleanDataset, getCleanedDatasetDownloadUrl } from "@/lib/api";
import type { CleanDatasetResponse } from "@/types";

interface DatasetCleaningPanelProps {
  datasetId: string;
  originalRowCount: number;
}

export function DatasetCleaningPanel({ datasetId, originalRowCount }: DatasetCleaningPanelProps) {
  const [isCleaning, setIsCleaning] = useState(false);
  const [cleaningResult, setCleaningResult] = useState<CleanDatasetResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [showChangesModal, setShowChangesModal] = useState(false);

  const handleCleanDataset = useCallback(async () => {
    setIsCleaning(true);
    setErrorMessage(null);

    try {
      const result = await cleanDataset(datasetId);
      setCleaningResult(result);
    } catch (err) {
      setErrorMessage(
        err instanceof Error
          ? err.message
          : "Failed to clean dataset. Please verify server connection."
      );
    } finally {
      setIsCleaning(false);
    }
  }, [datasetId]);

  const handleDownload = useCallback(() => {
    const url = getCleanedDatasetDownloadUrl(datasetId);
    window.open(url, "_blank");
  }, [datasetId]);

  const getTransformationBadge = (type: string) => {
    const t = type.toLowerCase();
    if (t.includes("duplicate")) {
      return "border-rose-500/30 bg-rose-500/10 text-rose-300";
    }
    if (t.includes("missing")) {
      return "border-sky-500/30 bg-sky-500/10 text-sky-300";
    }
    if (t.includes("email")) {
      return "border-violet-500/30 bg-violet-500/10 text-violet-300";
    }
    return "border-indigo-500/30 bg-indigo-500/10 text-indigo-300";
  };

  return (
    <div className="rounded-2xl border border-emerald-500/30 bg-gradient-to-b from-[#161a2e]/90 to-[#101426]/90 backdrop-blur-xl p-5 sm:p-6 shadow-2xl shadow-emerald-500/5 mb-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-white/[0.08]">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
          </div>
          <div>
            <h2 className="text-base font-semibold text-white tracking-tight">
              Non-Destructive Dataset Cleaning
            </h2>
            <p className="text-xs text-slate-400">
              Applies confident, safe normalizations without overwriting your original dataset ({originalRowCount.toLocaleString()} baseline rows)
            </p>
          </div>
        </div>

        {/* Action Button: Trigger Cleaning */}
        {!cleaningResult && (
          <button
            type="button"
            onClick={handleCleanDataset}
            disabled={isCleaning}
            className="inline-flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 px-5 py-2.5 text-xs font-semibold text-white shadow-lg shadow-emerald-500/20 hover:from-emerald-600 hover:to-teal-700 transition-all cursor-pointer disabled:opacity-50"
          >
            {isCleaning ? (
              <>
                <svg className="h-4 w-4 animate-spin text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Cleaning Dataset...
              </>
            ) : (
              <>
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                </svg>
                Clean Dataset
              </>
            )}
          </button>
        )}
      </div>

      {/* Safety Policy Banner */}
      <div className="mt-4 rounded-xl border border-white/[0.06] bg-white/[0.02] p-3 text-xs text-slate-300 flex items-start gap-2.5">
        <svg className="h-4 w-4 shrink-0 text-emerald-400 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <div>
          <span className="font-semibold text-white">Strict Non-Destructive Policy: </span>
          Original dataset is preserved unaltered. Only safe operations are applied (exact deduplication, whitespace trimming, placeholder standardization). Ambiguous values (outliers, non-standard emails, sign discrepancies) are preserved with advisories.
        </div>
      </div>

      {/* Error Notice */}
      {errorMessage && (
        <div className="mt-4 rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-300">
          {errorMessage}
        </div>
      )}

      {/* ----------------- CLEANING SUCCESS RESULTS ----------------- */}
      {cleaningResult && (
        <div className="mt-5 space-y-4">
          {/* Summary Stat Pills */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3">
              <span className="text-[10px] uppercase font-semibold text-slate-400 block mb-0.5">Original Rows</span>
              <span className="text-lg font-bold font-mono text-white">{cleaningResult.original_rows.toLocaleString()}</span>
            </div>

            <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3">
              <span className="text-[10px] uppercase font-semibold text-slate-400 block mb-0.5">Cleaned Rows</span>
              <span className="text-lg font-bold font-mono text-emerald-400">{cleaningResult.cleaned_rows.toLocaleString()}</span>
            </div>

            <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3">
              <span className="text-[10px] uppercase font-semibold text-slate-400 block mb-0.5">Rows Removed</span>
              <span className="text-lg font-bold font-mono text-amber-400">{cleaningResult.rows_removed.toLocaleString()}</span>
            </div>

            <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3">
              <span className="text-[10px] uppercase font-semibold text-slate-400 block mb-0.5">Cells Modified</span>
              <span className="text-lg font-bold font-mono text-indigo-400">{cleaningResult.cells_modified.toLocaleString()}</span>
            </div>
          </div>

          {/* Action Row: Download Cleaned Dataset & View Changes */}
          <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
            <div className="flex flex-wrap items-center gap-2.5">
              {/* Primary Download Button */}
              <button
                type="button"
                onClick={handleDownload}
                className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 px-5 py-2.5 text-xs font-semibold text-white shadow-lg shadow-emerald-500/20 hover:from-emerald-600 hover:to-teal-700 transition-all cursor-pointer"
              >
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                Download Cleaned Dataset
              </button>

              {/* View Changes Button */}
              <button
                type="button"
                onClick={() => setShowChangesModal((prev) => !prev)}
                className="inline-flex items-center gap-2 rounded-xl border border-white/[0.12] bg-white/[0.04] px-4 py-2.5 text-xs font-semibold text-slate-200 hover:bg-white/[0.08] hover:text-white transition-all cursor-pointer"
              >
                <svg className="h-4 w-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
                {showChangesModal ? "Hide Changes" : "View Changes"} ({cleaningResult.transformations_performed.length})
              </button>
            </div>

            <span className="text-[11px] text-slate-400 font-mono truncate max-w-xs">
              File: {cleaningResult.cleaned_filename}
            </span>
          </div>

          {/* ----------------- VIEW CHANGES EXPANDABLE SECTION ----------------- */}
          {showChangesModal && (
            <div className="mt-4 rounded-xl border border-white/[0.08] bg-white/[0.02] p-4 text-xs animate-fadeIn">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300 mb-3 flex items-center justify-between">
                <span>Executed Transformations Audit Trail</span>
                <span className="text-[11px] text-slate-500 font-normal">
                  {cleaningResult.transformations_performed.length} operations
                </span>
              </h3>

              {cleaningResult.transformations_performed.length > 0 ? (
                <div className="space-y-2.5">
                  {cleaningResult.transformations_performed.map((t, idx) => (
                    <div key={idx} className="rounded-lg border border-white/[0.05] bg-white/[0.02] p-3">
                      <div className="flex items-center justify-between gap-2 mb-1.5">
                        <span className={`inline-flex items-center rounded px-2 py-0.5 text-[10px] font-bold uppercase font-mono border ${getTransformationBadge(t.type)}`}>
                          {t.type.replace(/_/g, " ")}
                        </span>
                        <div className="flex items-center gap-3 font-mono text-[11px] text-slate-400">
                          {t.affected_rows > 0 && <span>{t.affected_rows} rows</span>}
                          {t.cells_modified > 0 && <span>{t.cells_modified} cells</span>}
                        </div>
                      </div>
                      <p className="text-slate-200 leading-snug">{t.description}</p>
                      {t.affected_columns && t.affected_columns.length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-1">
                          {t.affected_columns.map((c) => (
                            <span key={c} className="rounded bg-white/[0.04] px-1.5 py-0.5 text-[10px] font-mono text-slate-400">
                              {c}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-slate-400 italic">No modifications were required; the dataset was already normalized.</p>
              )}

              {/* Warnings / Preserved Ambiguities */}
              {cleaningResult.warnings.length > 0 && (
                <div className="mt-4 pt-4 border-t border-white/[0.06]">
                  <h4 className="text-[11px] font-semibold uppercase tracking-wider text-amber-400 mb-2 flex items-center gap-1.5">
                    <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                    Preserved Without Automatic Modification (Recommendations)
                  </h4>
                  <ul className="space-y-1.5 text-slate-300">
                    {cleaningResult.warnings.map((w, idx) => (
                      <li key={idx} className="flex items-start gap-2">
                        <span className="text-amber-400 font-mono text-xs">•</span>
                        <span className="leading-snug">{w}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
