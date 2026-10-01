/**
 * DataLens AI — Core TypeScript Type Definitions
 */

export interface HealthResponse {
  status: "ok" | "healthy" | string;
}

export interface DatasetUploadResponse {
  dataset_id: string;
  filename: string;
  format: string;
  size_bytes: number;
}

export interface NumericStats {
  min: number | null;
  max: number | null;
  mean: number | null;
  median: number | null;
  std: number | null;
  q25: number | null;
  q50: number | null;
  q75: number | null;
}

export interface TextStats {
  min_length: number | null;
  max_length: number | null;
  avg_length: number | null;
}

export interface CategoricalValueFrequency {
  value: string;
  count: number;
  percentage: number;
}

export interface CategoricalStats {
  top_values: CategoricalValueFrequency[];
}

export interface DateStats {
  is_date: boolean;
  confidence: number;
  detected_format: string | null;
  earliest: string | null;
  latest: string | null;
}

export interface ColumnProfile {
  name: string;
  inferred_type: "numeric" | "text" | "categorical" | "datetime" | "boolean" | string;
  original_dtype: string;
  non_null_count: number;
  null_count: number;
  null_percentage: number;
  unique_count: number;
  unique_percentage: number;
  numeric_stats: NumericStats | null;
  text_stats: TextStats | null;
  categorical_stats: CategoricalStats | null;
  date_stats: DateStats | null;
}

export interface GeneralProfile {
  dataset_id: string;
  row_count: number;
  column_count: number;
  file_format: string;
  memory_usage_bytes: number;
  memory_usage_human: string;
}

export interface DatasetProfileResponse {
  general: GeneralProfile;
  columns: ColumnProfile[];
}

export interface QualityIssue {
  type: string;
  severity: "high" | "medium" | "low" | string;
  column: string | null;
  affected_rows: number;
  percentage: number;
  description: string;
  method: string;
}

export interface DatasetAnalysisResponse {
  dataset_id: string;
  total_issues: number;
  issues_by_severity: {
    high: number;
    medium: number;
    low: number;
    [key: string]: number;
  };
  issues: QualityIssue[];
  analyzed_rows: number;
  analyzed_columns: number;
}

export interface QualityDimensions {
  completeness: number;
  validity: number;
  uniqueness: number;
  consistency: number;
}

export interface QualityScoreResponse {
  overall: number;
  dimensions: QualityDimensions;
  explanation: string[];
}

export interface PriorityIssue {
  issue: string;
  importance: string;
  explanation: string;
  recommendation: string;
}

export interface AiInsightResponse {
  dataset_id: string;
  summary: string;
  priority_issues: PriorityIssue[];
  cleaning_plan: string[];
  text_observations?: string[] | null;
  source: "llm" | "deterministic_fallback" | string;
}

export interface FeatureCard {
  title: string;
  description: string;
  tag: string;
  iconName: "chart" | "shield" | "sparkles" | "cpu";
}

export type UploadState =
  | { status: "idle" }
  | { status: "dragging" }
  | { status: "uploading"; progress: number; filename: string }
  | { status: "success"; data: DatasetUploadResponse }
  | { status: "error"; message: string };

export interface FullDatasetAnalysis {
  datasetId: string;
  filename: string;
  format: string;
  sizeBytes: number;
  analyzedAt: string;
  profile: DatasetProfileResponse;
  analysis: DatasetAnalysisResponse;
  score: QualityScoreResponse;
  aiInsights: AiInsightResponse;
}

export interface TransformationRecord {
  type: string;
  description: string;
  affected_rows: number;
  cells_modified: number;
  affected_columns: string[] | null;
}

export interface CleanDatasetResponse {
  dataset_id: string;
  cleaned_filename: string;
  download_url: string;
  original_rows: number;
  cleaned_rows: number;
  rows_removed: number;
  cells_modified: number;
  transformations_performed: TransformationRecord[];
  warnings: string[];
}


