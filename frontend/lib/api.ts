/**
 * DataLens AI — API Client
 *
 * All communication with the FastAPI backend goes through these functions.
 * The base URL is configurable via NEXT_PUBLIC_API_URL env var.
 */

import type {
  AiInsightResponse,
  CleanDatasetResponse,
  DatasetAnalysisResponse,
  DatasetProfileResponse,
  DatasetUploadResponse,
  HealthResponse,
  QualityScoreResponse,
} from "@/types";

/**
 * Resolves the backend base URL from environment variables,
 * stripping trailing slashes to guarantee clean route concatenation.
 */
function getApiBaseUrl(): string {
  const envUrl = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (envUrl) {
    return envUrl.replace(/\/+$/, "");
  }
  return "http://localhost:8000";
}

const API_BASE = getApiBaseUrl();

export const NETWORK_ERROR_MESSAGE =
  "Unable to connect to the DataLens backend service. If hosted on a free cloud tier (such as Render), the server may take 30–60 seconds to wake up from sleep mode. Please wait a moment and try again.";

/**
 * Check backend system health status.
 * Checks /health first, falling back to /api/health.
 */
export async function checkBackendHealth(): Promise<HealthResponse> {
  try {
    const response = await fetch(`${API_BASE}/health`, {
      cache: "no-store",
      headers: {
        Accept: "application/json",
      },
    });

    if (response.ok) {
      return response.json();
    }
  } catch {
    // Retry via /api/health
  }

  const response = await fetch(`${API_BASE}/api/health`, {
    cache: "no-store",
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`Backend health check failed with status: ${response.status}`);
  }

  return response.json();
}

export interface ApiError {
  detail: string;
}

/**
 * Upload a dataset file (CSV or JSON) to POST /api/datasets/upload.
 *
 * @param file - The File object from the user's input
 * @param onProgress - Optional progress callback (0–100)
 * @returns The parsed upload response with dataset metadata: dataset_id, filename, format, size_bytes
 */
export async function uploadDatasetFile(
  file: File,
  onProgress?: (percent: number) => void
): Promise<DatasetUploadResponse> {
  return new Promise<DatasetUploadResponse>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const formData = new FormData();
    formData.append("file", file);

    xhr.open("POST", `${API_BASE}/api/datasets/upload`);

    xhr.upload.addEventListener("progress", (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    });

    xhr.addEventListener("load", () => {
      try {
        const data = JSON.parse(xhr.responseText);
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(data as DatasetUploadResponse);
        } else {
          const detail = (data as ApiError).detail ?? `Upload failed with status ${xhr.status}`;
          reject(new Error(detail));
        }
      } catch {
        reject(new Error("Failed to parse server response."));
      }
    });

    xhr.addEventListener("error", () => {
      reject(new Error(NETWORK_ERROR_MESSAGE));
    });

    xhr.addEventListener("abort", () => {
      reject(new Error("Upload was cancelled."));
    });

    xhr.send(formData);
  });
}

/**
 * Profile an uploaded dataset by ID without using an LLM.
 *
 * Calls POST /api/datasets/{dataset_id}/profile
 */
export async function profileDataset(datasetId: string): Promise<DatasetProfileResponse> {
  const response = await fetch(`${API_BASE}/api/datasets/${encodeURIComponent(datasetId)}/profile`, {
    method: "POST",
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    let errorDetail = `Profiling failed with status ${response.status}`;
    try {
      const err = await response.json();
      if (err.detail) errorDetail = err.detail;
    } catch {
      // Use fallback errorDetail
    }
    throw new Error(errorDetail);
  }

  return response.json();
}

/**
 * Execute deterministic data-quality issue detection on an uploaded dataset.
 *
 * Calls POST /api/datasets/{dataset_id}/analyze
 */
export async function analyzeDatasetQuality(datasetId: string): Promise<DatasetAnalysisResponse> {
  const response = await fetch(`${API_BASE}/api/datasets/${encodeURIComponent(datasetId)}/analyze`, {
    method: "POST",
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    let errorDetail = `Data-quality analysis failed with status ${response.status}`;
    try {
      const err = await response.json();
      if (err.detail) errorDetail = err.detail;
    } catch {
      // Use fallback errorDetail
    }
    throw new Error(errorDetail);
  }

  return response.json();
}

/**
 * Compute transparent quality score and dimension breakdown for an uploaded dataset.
 *
 * Calls POST /api/datasets/{dataset_id}/score
 */
export async function calculateQualityScore(datasetId: string): Promise<QualityScoreResponse> {
  const response = await fetch(`${API_BASE}/api/datasets/${encodeURIComponent(datasetId)}/score`, {
    method: "POST",
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    let errorDetail = `Quality scoring failed with status ${response.status}`;
    try {
      const err = await response.json();
      if (err.detail) errorDetail = err.detail;
    } catch {
      // Use fallback errorDetail
    }
    throw new Error(errorDetail);
  }

  return response.json();
}

/**
 * Request AI-driven interpretation, problem prioritization, and cleaning sequence.
 *
 * Calls POST /api/datasets/{dataset_id}/ai-insights
 */
export async function fetchAiInsights(datasetId: string): Promise<AiInsightResponse> {
  const response = await fetch(`${API_BASE}/api/datasets/${encodeURIComponent(datasetId)}/ai-insights`, {
    method: "POST",
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    let errorDetail = `AI insight generation failed with status ${response.status}`;
    try {
      const err = await response.json();
      if (err.detail) errorDetail = err.detail;
    } catch {
      // Use fallback errorDetail
    }
    throw new Error(errorDetail);
  }

  return response.json();
}

/**
 * Execute non-destructive dataset cleaning.
 *
 * Calls POST /api/datasets/{dataset_id}/clean
 */
export async function cleanDataset(datasetId: string): Promise<CleanDatasetResponse> {
  const response = await fetch(`${API_BASE}/api/datasets/${encodeURIComponent(datasetId)}/clean`, {
    method: "POST",
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    let errorDetail = `Dataset cleaning failed with status ${response.status}`;
    try {
      const err = await response.json();
      if (err.detail) errorDetail = err.detail;
    } catch {
      // Use fallback errorDetail
    }
    throw new Error(errorDetail);
  }

  return response.json();
}

/**
 * Get direct download URL for the cleaned dataset file.
 */
export function getCleanedDatasetDownloadUrl(datasetId: string): string {
  return `${API_BASE}/api/datasets/${encodeURIComponent(datasetId)}/download-cleaned`;
}

/**
 * Get URL for the printable executive HTML report.
 */
export function getDatasetHtmlReportUrl(datasetId: string): string {
  return `${API_BASE}/api/datasets/${encodeURIComponent(datasetId)}/report/html`;
}

/**
 * Get URL for direct PDF report export and download.
 */
export function getDatasetPdfReportUrl(datasetId: string): string {
  return `${API_BASE}/api/datasets/${encodeURIComponent(datasetId)}/report/pdf`;
}

/**
 * Explicitly delete an uploaded dataset and cleaned files from server storage.
 *
 * Calls DELETE /api/datasets/{dataset_id}
 */
export async function deleteDataset(datasetId: string): Promise<{ status: string; message: string; dataset_id: string }> {
  const response = await fetch(`${API_BASE}/api/datasets/${encodeURIComponent(datasetId)}`, {
    method: "DELETE",
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    let errorDetail = `Failed to delete dataset (status ${response.status})`;
    try {
      const err = await response.json();
      if (err.detail) errorDetail = err.detail;
    } catch {
      // Use fallback
    }
    throw new Error(errorDetail);
  }

  return response.json();
}


