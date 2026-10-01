"use client";

import React from "react";
import type { FullDatasetAnalysis } from "@/types";
import { DashboardHeader } from "./DashboardHeader";
import { QualityScoreCard } from "./QualityScoreCard";
import { DimensionScoresCard } from "./DimensionScoresCard";
import { OverviewMetrics } from "./OverviewMetrics";
import { ChartsSection } from "./ChartsSection";
import { IssueTable } from "./IssueTable";
import { AiInsightsSection } from "./AiInsightsSection";
import { DatasetCleaningPanel } from "./DatasetCleaningPanel";

interface AnalysisDashboardProps {
  data: FullDatasetAnalysis;
  onNewUpload?: () => void;
}

export function AnalysisDashboard({ data, onNewUpload }: AnalysisDashboardProps) {
  return (
    <div className="w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      {/* 1. Header */}
      <DashboardHeader
        datasetId={data.datasetId}
        filename={data.filename}
        format={data.format}
        rowCount={data.profile.general.row_count}
        columnCount={data.profile.general.column_count}
        analyzedAt={data.analyzedAt}
        onNewUpload={onNewUpload}
      />

      {/* 2. Overview Metrics Cards */}
      <OverviewMetrics
        analysis={data.analysis}
        profile={data.profile}
      />

      {/* 3. Quality Score & Dimension Scores Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6 mb-6">
        <QualityScoreCard
          score={data.score.overall}
          explanations={data.score.explanation}
        />
        <DimensionScoresCard
          dimensions={data.score.dimensions}
        />
      </div>

      {/* 4. AI Insights & Remediation Section */}
      <AiInsightsSection
        insights={data.aiInsights}
      />

      {/* 5. Dataset Cleaning System (Non-Destructive) */}
      <DatasetCleaningPanel
        datasetId={data.datasetId}
        originalRowCount={data.profile.general.row_count}
      />

      {/* 6. Visual Charts Grid */}
      <ChartsSection
        profile={data.profile}
        analysis={data.analysis}
        dimensions={data.score.dimensions}
      />

      {/* 7. Issue Details Table */}
      <IssueTable
        issues={data.analysis.issues}
        totalRows={data.profile.general.row_count}
      />
    </div>
  );
}
