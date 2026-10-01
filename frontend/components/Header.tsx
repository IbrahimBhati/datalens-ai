"use client";

import { useEffect, useState } from "react";
import { checkBackendHealth } from "@/lib/api";

export function Header() {
  const [backendStatus, setBackendStatus] = useState<"checking" | "online" | "offline">("checking");

  useEffect(() => {
    let isMounted = true;

    const queryHealth = () => {
      checkBackendHealth()
        .then((res) => {
          if (isMounted) {
            setBackendStatus(res.status === "ok" ? "online" : "offline");
          }
        })
        .catch(() => {
          if (isMounted) {
            setBackendStatus("offline");
          }
        });
    };

    queryHealth();

    // Poll every 12 seconds to automatically detect when a cloud instance (e.g. Render) wakes up
    const interval = setInterval(queryHealth, 12000);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  return (
    <header className="sticky top-0 z-50 w-full border-b border-white/[0.08] bg-[#0b0d17]/80 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-500 shadow-md shadow-indigo-500/20">
            <svg
              className="h-5 w-5 text-white"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
              />
            </svg>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-lg font-bold tracking-tight text-white">
              DataLens <span className="text-indigo-400">AI</span>
            </span>
            <span className="rounded-full bg-indigo-500/10 px-2 py-0.5 text-[10px] font-semibold tracking-wide text-indigo-400 border border-indigo-500/20">
              v0.1.0
            </span>
          </div>
        </div>

        {/* Status & Navigation */}
        <div className="flex items-center gap-4">
          <div
            className="flex items-center gap-2 rounded-full border border-white/[0.08] bg-white/[0.02] px-3 py-1 text-xs text-slate-300"
            title="Backend Service Status (GET /api/health)"
          >
            <span
              className={`h-2 w-2 rounded-full ${
                backendStatus === "online"
                  ? "bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)]"
                  : backendStatus === "checking"
                  ? "bg-amber-400 animate-pulse"
                  : "bg-rose-400 shadow-[0_0_8px_rgba(244,63,94,0.8)]"
              }`}
            />
            <span className="font-mono text-[11px] text-slate-400">
              API: {backendStatus === "online" ? "Active (ok)" : backendStatus === "checking" ? "Verifying..." : "Offline"}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
}
