"use client";

import { useState, useRef, useCallback } from "react";
import { uploadDatasetFile } from "@/lib/api";
import type { UploadState, DatasetUploadResponse } from "@/types";

const ACCEPTED_EXTENSIONS = [".csv", ".json"];
const MAX_FILE_SIZE_MB = 50;
const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;

function formatBytes(bytes: number, decimals = 2): string {
  if (bytes === 0) return "0 Bytes";
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
}

interface DatasetUploaderProps {
  onAnalyze?: (uploadData: DatasetUploadResponse) => void;
}

export function DatasetUploader({ onAnalyze }: DatasetUploaderProps = {}) {
  const [state, setState] = useState<UploadState>({ status: "idle" });
  const [copiedId, setCopiedId] = useState(false);
  const [analysisRequested, setAnalysisRequested] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Client-side quick validation
  const validateFile = useCallback((file: File): string | null => {
    const ext = "." + file.name.split(".").pop()?.toLowerCase();
    if (!ACCEPTED_EXTENSIONS.includes(ext)) {
      return `Unsupported file extension "${ext}". Only .csv and .json files are supported.`;
    }
    if (file.size === 0) {
      return "The selected file is empty (0 bytes). Please upload a valid dataset.";
    }
    if (file.size > MAX_FILE_SIZE_BYTES) {
      return `File exceeds maximum allowed size of ${MAX_FILE_SIZE_MB} MB (selected file is ${(file.size / (1024 * 1024)).toFixed(1)} MB).`;
    }
    return null;
  }, []);

  const handleUpload = useCallback(
    async (file: File) => {
      const validationError = validateFile(file);
      if (validationError) {
        setState({ status: "error", message: validationError });
        return;
      }

      setState({ status: "uploading", progress: 0, filename: file.name });
      setAnalysisRequested(false);

      try {
        const result = await uploadDatasetFile(file, (percent) => {
          setState((prev) =>
            prev.status === "uploading" ? { ...prev, progress: percent } : prev
          );
        });
        setState({ status: "success", data: result });
      } catch (err) {
        setState({
          status: "error",
          message: err instanceof Error ? err.message : "An unexpected upload error occurred.",
        });
      }
    },
    [validateFile]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setState((prev) => (prev.status === "uploading" ? prev : { status: "dragging" }));
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setState((prev) => (prev.status === "dragging" ? { status: "idle" } : prev));
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      const files = e.dataTransfer.files;
      if (files && files.length > 0) {
        handleUpload(files[0]);
      } else {
        setState({ status: "idle" });
      }
    },
    [handleUpload]
  );

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files;
      if (files && files.length > 0) {
        handleUpload(files[0]);
      }
      e.target.value = "";
    },
    [handleUpload]
  );

  const handleCopyDatasetId = useCallback((id: string) => {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(id);
      setCopiedId(true);
      setTimeout(() => setCopiedId(false), 2000);
    }
  }, []);

  const resetUpload = useCallback(() => {
    setState({ status: "idle" });
    setAnalysisRequested(false);
  }, []);

  return (
    <div className="w-full max-w-2xl mx-auto px-4 my-6">
      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".csv,.json"
        className="hidden"
        onChange={handleFileChange}
      />

      {/* -------------------- STATE: IDLE OR DRAGGING -------------------- */}
      {(state.status === "idle" || state.status === "dragging") && (
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`relative group rounded-2xl border-2 border-dashed transition-all duration-300 p-8 sm:p-12 text-center bg-gradient-to-b from-[#161a2e]/90 to-[#111427]/90 backdrop-blur-xl cursor-pointer ${
            state.status === "dragging"
              ? "border-indigo-400 bg-indigo-500/[0.08] shadow-[0_0_40px_rgba(99,102,241,0.25)] scale-[1.01]"
              : "border-white/[0.15] hover:border-indigo-400/60 hover:shadow-[0_0_30px_rgba(99,102,241,0.12)]"
          }`}
        >
          {/* Ambient Glow */}
          <div className="absolute inset-0 -z-10 rounded-2xl bg-indigo-600/[0.04] blur-xl pointer-events-none" />

          {/* Cloud Upload Icon */}
          <div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-2xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 group-hover:scale-110 group-hover:text-indigo-300 transition-all duration-300 shadow-inner">
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

          <h3 className="text-xl font-semibold text-white tracking-tight">
            {state.status === "dragging" ? "Drop dataset file here" : "Upload Dataset"}
          </h3>

          <p className="mt-2 text-sm text-slate-300 max-w-md mx-auto leading-relaxed">
            Drag and drop your dataset here, or click to browse files.
          </p>

          <div className="mt-6 flex items-center justify-center">
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                fileInputRef.current?.click();
              }}
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-indigo-500 to-violet-600 px-6 py-2.5 text-sm font-semibold text-white shadow-lg shadow-indigo-500/25 hover:from-indigo-600 hover:to-violet-700 transition-all duration-200 cursor-pointer"
            >
              <svg
                className="h-4 w-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
              </svg>
              Select CSV or JSON File
            </button>
          </div>

          {/* Format Constraints */}
          <div className="mt-6 pt-5 border-t border-white/[0.06] flex flex-wrap items-center justify-center gap-3 text-xs text-slate-400">
            <span className="flex items-center gap-1.5 font-medium text-slate-300">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
              CSV (.csv) & JSON (.json)
            </span>
            <span className="text-white/[0.2] hidden sm:inline">•</span>
            <span>Max 50 MB</span>
            <span className="text-white/[0.2] hidden sm:inline">•</span>
            <span>MIME validated</span>
          </div>
        </div>
      )}

      {/* -------------------- STATE: UPLOADING / PROGRESS -------------------- */}
      {state.status === "uploading" && (
        <div className="rounded-2xl border border-indigo-500/30 bg-[#161a2e] p-8 text-center backdrop-blur-xl shadow-2xl shadow-indigo-500/10">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
            <svg
              className="h-7 w-7 animate-spin text-indigo-400"
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

          <h4 className="text-lg font-semibold text-white">Uploading Dataset...</h4>
          <p className="mt-1 font-mono text-xs text-slate-400 truncate max-w-sm mx-auto">
            {state.filename}
          </p>

          {/* Progress Bar */}
          <div className="mt-6 w-full max-w-md mx-auto">
            <div className="flex justify-between text-xs text-slate-400 mb-1.5 font-mono">
              <span>Transferring to temporary storage</span>
              <span>{state.progress}%</span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-white/[0.08]">
              <div
                className="h-full bg-gradient-to-r from-indigo-500 to-violet-500 transition-all duration-200 ease-out rounded-full"
                style={{ width: `${Math.max(state.progress, 5)}%` }}
              />
            </div>
          </div>
        </div>
      )}

      {/* -------------------- STATE: SUCCESS -------------------- */}
      {state.status === "success" && (
        <div className="rounded-2xl border border-emerald-500/30 bg-[#161a2e]/90 p-6 sm:p-8 backdrop-blur-xl shadow-2xl shadow-emerald-500/5 transition-all duration-300">
          {/* Header Banner */}
          <div className="flex items-center gap-3 pb-5 border-b border-white/[0.08]">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <div>
              <h4 className="text-base font-semibold text-white">Dataset Uploaded Successfully</h4>
              <p className="text-xs text-slate-400">
                Validated and stored safely in temporary session storage.
              </p>
            </div>
          </div>

          {/* Metadata Display Grid */}
          <div className="mt-5 grid grid-cols-1 sm:grid-cols-2 gap-3.5">
            {/* Filename */}
            <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3.5">
              <span className="text-[11px] font-medium uppercase tracking-wider text-slate-400 block mb-1">
                Filename
              </span>
              <span className="text-sm font-semibold text-white font-mono truncate block" title={state.data.filename}>
                {state.data.filename}
              </span>
            </div>

            {/* Format */}
            <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3.5">
              <span className="text-[11px] font-medium uppercase tracking-wider text-slate-400 block mb-1">
                Format
              </span>
              <div className="flex items-center gap-2">
                <span className="inline-flex items-center rounded-md bg-indigo-500/15 border border-indigo-500/30 px-2 py-0.5 text-xs font-bold uppercase text-indigo-300 font-mono">
                  {state.data.format}
                </span>
                <span className="text-xs text-slate-400">Validated</span>
              </div>
            </div>

            {/* File Size */}
            <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3.5">
              <span className="text-[11px] font-medium uppercase tracking-wider text-slate-400 block mb-1">
                File Size
              </span>
              <div className="flex items-baseline gap-2">
                <span className="text-sm font-semibold text-white font-mono">
                  {formatBytes(state.data.size_bytes)}
                </span>
                <span className="text-[11px] text-slate-400">
                  ({state.data.size_bytes.toLocaleString()} bytes)
                </span>
              </div>
            </div>

            {/* Dataset ID */}
            <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3.5">
              <div className="flex items-center justify-between mb-1">
                <span className="text-[11px] font-medium uppercase tracking-wider text-slate-400">
                  Dataset ID
                </span>
                <button
                  type="button"
                  onClick={() => handleCopyDatasetId(state.data.dataset_id)}
                  className="text-[10px] text-indigo-400 hover:text-indigo-300 cursor-pointer font-mono"
                >
                  {copiedId ? "Copied!" : "Copy"}
                </button>
              </div>
              <span className="text-xs font-mono text-slate-300 truncate block" title={state.data.dataset_id}>
                {state.data.dataset_id}
              </span>
            </div>
          </div>

          {/* Action Row */}
          <div className="mt-6 pt-5 border-t border-white/[0.08] flex flex-col sm:flex-row items-center justify-between gap-3">
            <button
              type="button"
              onClick={resetUpload}
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-xl border border-white/[0.1] bg-white/[0.03] px-4 py-2 text-xs font-medium text-slate-300 hover:bg-white/[0.07] hover:text-white transition-colors cursor-pointer"
            >
              Upload Another Dataset
            </button>

            {/* Required "Analyze Dataset" button */}
            <button
              type="button"
              onClick={() => {
                if (onAnalyze) {
                  onAnalyze(state.data);
                } else {
                  setAnalysisRequested(true);
                }
              }}
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-indigo-500 to-violet-600 px-6 py-2.5 text-sm font-semibold text-white shadow-lg shadow-indigo-500/25 hover:from-indigo-600 hover:to-violet-700 transition-all duration-200 cursor-pointer"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              Analyze Dataset
            </button>
          </div>

          {/* Notification when "Analyze Dataset" is clicked (without pretending analysis ran) */}
          {analysisRequested && (
            <div className="mt-4 rounded-xl border border-indigo-500/30 bg-indigo-500/10 p-3.5 text-xs text-indigo-200 flex items-start gap-2.5 animate-fadeIn">
              <svg className="h-4 w-4 shrink-0 text-indigo-400 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div>
                <span className="font-semibold text-white">Dataset Ready for Analysis: </span>
                Dataset ID <span className="font-mono text-indigo-300">{state.data.dataset_id}</span> is staged in temporary storage. Deep quality profiling and scoring engine will process this dataset in the analysis step.
              </div>
            </div>
          )}
        </div>
      )}

      {/* -------------------- STATE: ERROR -------------------- */}
      {state.status === "error" && (
        <div className="rounded-2xl border border-rose-500/30 bg-rose-500/[0.06] p-6 text-center backdrop-blur-xl shadow-xl shadow-rose-500/5">
          <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-rose-500/15 border border-rose-500/30 text-rose-400">
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <h4 className="text-base font-semibold text-white">Upload Failed</h4>
          <p className="mt-1 text-sm text-rose-300 max-w-md mx-auto leading-relaxed">
            {state.message}
          </p>
          <div className="mt-5 flex items-center justify-center gap-3">
            <button
              type="button"
              onClick={resetUpload}
              className="inline-flex items-center justify-center rounded-xl bg-white/[0.08] hover:bg-white/[0.12] border border-white/[0.1] px-4 py-2 text-xs font-medium text-white transition-colors cursor-pointer"
            >
              Try Again
            </button>
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="inline-flex items-center justify-center rounded-xl bg-gradient-to-r from-indigo-500 to-violet-600 px-4 py-2 text-xs font-semibold text-white shadow hover:from-indigo-600 hover:to-violet-700 transition-all cursor-pointer"
            >
              Choose Another File
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
