"use client";

import React, { useState, useCallback } from "react";
import { Header } from "@/components/Header";
import { HeroSection } from "@/components/HeroSection";
import { DatasetUploader } from "@/components/DatasetUploader";
import { FeatureGrid } from "@/components/FeatureGrid";
import { Footer } from "@/components/Footer";
import { AnalysisDashboard } from "@/components/dashboard/AnalysisDashboard";
import { AnalysisLoadingState } from "@/components/dashboard/AnalysisLoadingState";
import {
  profileDataset,
  analyzeDatasetQuality,
  calculateQualityScore,
  fetchAiInsights,
} from "@/lib/api";
import type { DatasetUploadResponse, FullDatasetAnalysis } from "@/types";

export default function HomePage() {
  const [analysisData, setAnalysisData] = useState<FullDatasetAnalysis | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analyzingFilename, setAnalyzingFilename] = useState("");
  const [stepMessage, setStepMessage] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const runAnalysis = useCallback(async (uploadData: DatasetUploadResponse) => {
    setIsAnalyzing(true);
    setAnalyzingFilename(uploadData.filename);
    setErrorMessage(null);
    setStepMessage("1/4: Profiling schema, types, and column distributions...");

    try {
      // 1. Profile dataset
      const profile = await profileDataset(uploadData.dataset_id);
      setStepMessage("2/4: Detecting quality issues, missingness, and outliers...");

      // 2. Analyze quality issues
      const analysis = await analyzeDatasetQuality(uploadData.dataset_id);
      setStepMessage("3/4: Calculating multidimensional quality scores...");

      // 3. Quality scoring
      const score = await calculateQualityScore(uploadData.dataset_id);
      setStepMessage("4/4: Synthesizing AI executive insights & recommendations...");

      // 4. AI Insights (with graceful fallback handled server-side)
      let aiInsights;
      try {
        aiInsights = await fetchAiInsights(uploadData.dataset_id);
      } catch (aiErr) {
        console.warn("AI insight endpoint error, generating client fallback:", aiErr);
        aiInsights = {
          dataset_id: uploadData.dataset_id,
          summary: `The dataset contains ${profile.general.row_count.toLocaleString()} rows and ${profile.general.column_count} columns with an overall quality score of ${score.overall}/100. ${analysis.total_issues} data quality issues were identified.`,
          priority_issues: analysis.issues.slice(0, 3).map((iss) => ({
            issue: iss.type.replace(/_/g, " "),
            importance: iss.severity === "high" ? "Critical" : "Medium",
            explanation: iss.description,
            recommendation: `Remediate ${iss.affected_rows} affected rows in column ${iss.column || "dataset"}.`,
          })),
          cleaning_plan: [
            "Step 1: Inspect and resolve high-severity issues identified in the quality report.",
            "Step 2: Clean invalid and out-of-range values.",
            "Step 3: Handle null and missing values appropriately.",
          ],
          text_observations: [],
          source: "deterministic_fallback",
        };
      }

      const fullAnalysis: FullDatasetAnalysis = {
        datasetId: uploadData.dataset_id,
        filename: uploadData.filename,
        format: uploadData.format,
        sizeBytes: uploadData.size_bytes,
        analyzedAt: new Date().toISOString(),
        profile,
        analysis,
        score,
        aiInsights,
      };

      setAnalysisData(fullAnalysis);
    } catch (err) {
      console.error("Analysis failed:", err);
      setErrorMessage(
        err instanceof Error
          ? err.message
          : "An unexpected error occurred during dataset analysis. Please verify the backend is running."
      );
    } finally {
      setIsAnalyzing(false);
    }
  }, []);

  const handleNewUpload = useCallback(() => {
    setAnalysisData(null);
    setErrorMessage(null);
    setIsAnalyzing(false);
  }, []);

  return (
    <div className="flex min-h-screen flex-col bg-[#0b0d17] text-[#f1f5f9]">
      <Header />
      <main className="flex-1 flex flex-col justify-center py-6">
        {/* State 1: Currently Analyzing */}
        {isAnalyzing && (
          <AnalysisLoadingState
            filename={analyzingFilename}
            stepMessage={stepMessage}
          />
        )}

        {/* State 2: Analysis Completed -> Show Dashboard */}
        {!isAnalyzing && analysisData && (
          <AnalysisDashboard
            data={analysisData}
            onNewUpload={handleNewUpload}
          />
        )}

        {/* State 3: Analysis Error */}
        {!isAnalyzing && errorMessage && !analysisData && (
          <div className="w-full max-w-xl mx-auto px-4 py-8 text-center">
            <div className="rounded-2xl border border-rose-500/30 bg-rose-500/[0.06] p-6 backdrop-blur-xl shadow-xl">
              <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-rose-500/15 border border-rose-500/30 text-rose-400">
                <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
              <h3 className="text-base font-semibold text-white">Analysis Failed</h3>
              <p className="mt-1 text-sm text-rose-300 leading-relaxed">
                {errorMessage}
              </p>
              <div className="mt-5">
                <button
                  type="button"
                  onClick={handleNewUpload}
                  className="inline-flex items-center justify-center rounded-xl bg-gradient-to-r from-indigo-500 to-violet-600 px-5 py-2 text-xs font-semibold text-white shadow hover:from-indigo-600 hover:to-violet-700 transition-all cursor-pointer"
                >
                  Return to Upload
                </button>
              </div>
            </div>
          </div>
        )}

        {/* State 4: Default Landing View */}
        {!isAnalyzing && !analysisData && !errorMessage && (
          <>
            <HeroSection />
            <DatasetUploader onAnalyze={runAnalysis} />
            <FeatureGrid />
          </>
        )}
      </main>
      <Footer />
    </div>
  );
}
