/**
 * End-to-end integration test of frontend API contract and state transitions.
 * Runs in Node.js against live running backend (http://127.0.0.1:8000) and frontend (http://localhost:3000).
 */

import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const TEST_DATA_DIR = path.resolve(__dirname, "../../test-data");
const API_BASE = "http://127.0.0.1:8000";

async function runTests() {
  console.log("=== Starting DataLens AI Frontend & End-to-End Contract Tests ===");
  let passed = 0;
  let failed = 0;

  function assert(condition, message) {
    if (!condition) {
      console.error(`❌ FAILED: ${message}`);
      failed++;
      throw new Error(message);
    } else {
      console.log(`✅ PASSED: ${message}`);
      passed++;
    }
  }

  // 1. Health check (/health and /api/health)
  console.log("\n[1] Testing Backend Health Check (/health and /api/health)...");
  const rootHealthRes = await fetch(`${API_BASE}/health`);
  assert(rootHealthRes.status === 200, "Root /health endpoint returns 200");
  const rootHealthData = await rootHealthRes.json();
  assert(rootHealthData.status === "ok", "Root health status is ok");

  const healthRes = await fetch(`${API_BASE}/api/health`);
  assert(healthRes.status === 200, "/api/health endpoint returns 200");
  const healthData = await healthRes.json();
  assert(healthData.status === "ok", "API health status is ok");

  // 2. Upload Clean Dataset Flow
  console.log("\n[2] Testing Clean Dataset Upload & Analysis Flow...");
  const cleanCsvPath = path.join(TEST_DATA_DIR, "clean.csv");
  const cleanCsvBytes = fs.readFileSync(cleanCsvPath);
  const cleanBlob = new Blob([cleanCsvBytes], { type: "text/csv" });

  const formData = new FormData();
  formData.append("file", cleanBlob, "clean.csv");

  const uploadRes = await fetch(`${API_BASE}/api/datasets/upload`, {
    method: "POST",
    body: formData,
  });
  assert(uploadRes.status === 200, "clean.csv upload returns 200");
  const uploadData = await uploadRes.json();
  assert(uploadData.dataset_id && uploadData.dataset_id.length > 10, "Valid dataset ID returned");
  assert(uploadData.filename === "clean.csv", "Filename preserved and sanitized");
  assert(uploadData.format === "csv", "Format identified as csv");
  const cleanId = uploadData.dataset_id;

  // Profile Clean
  const profileRes = await fetch(`${API_BASE}/api/datasets/${cleanId}/profile`, { method: "POST" });
  assert(profileRes.status === 200, "Profiling clean dataset returns 200");
  const profileData = await profileRes.json();
  assert(profileData.general.row_count === 10, "Row count is 10");
  assert(profileData.general.column_count === 8, "Column count is 8");

  // Analyze Clean
  const analyzeRes = await fetch(`${API_BASE}/api/datasets/${cleanId}/analyze`, { method: "POST" });
  assert(analyzeRes.status === 200, "Analysis of clean dataset returns 200");
  const analyzeData = await analyzeRes.json();
  assert(analyzeData.total_issues === 0, "Clean dataset has 0 quality issues");

  // Score Clean
  const scoreRes = await fetch(`${API_BASE}/api/datasets/${cleanId}/score`, { method: "POST" });
  assert(scoreRes.status === 200, "Scoring clean dataset returns 200");
  const scoreData = await scoreRes.json();
  assert(scoreData.overall >= 95, `Overall quality score is near-perfect (${scoreData.overall}/100)`);
  assert(scoreData.dimensions.completeness === 100, "Completeness is 100");
  assert(scoreData.dimensions.validity === 100, "Validity is 100");

  // AI Insights Clean
  const aiRes = await fetch(`${API_BASE}/api/datasets/${cleanId}/ai-insights`, { method: "POST" });
  assert(aiRes.status === 200, "AI insights endpoint returns 200");
  const aiData = await aiRes.json();
  assert(aiData.summary && aiData.summary.length > 20, "AI summary generated");
  assert(Array.isArray(aiData.cleaning_plan), "Cleaning plan is array");

  // 3. Upload Messy Dataset & Cleaning Flow
  console.log("\n[3] Testing Messy Dataset Upload, Detection, and Cleaning Flow...");
  const messyCsvPath = path.join(TEST_DATA_DIR, "messy.csv");
  const messyCsvBytes = fs.readFileSync(messyCsvPath);
  const messyBlob = new Blob([messyCsvBytes], { type: "text/csv" });

  const messyForm = new FormData();
  messyForm.append("file", messyBlob, "messy.csv");

  const messyUpRes = await fetch(`${API_BASE}/api/datasets/upload`, {
    method: "POST",
    body: messyForm,
  });
  assert(messyUpRes.status === 200, "messy.csv upload returns 200");
  const messyUpData = await messyUpRes.json();
  const messyId = messyUpData.dataset_id;

  // Analyze Messy
  const messyAnRes = await fetch(`${API_BASE}/api/datasets/${messyId}/analyze`, { method: "POST" });
  const messyAnData = await messyAnRes.json();
  assert(messyAnData.total_issues >= 5, `Messy dataset detected ${messyAnData.total_issues} issues`);
  const issueTypes = messyAnData.issues.map((i) => i.type);
  assert(issueTypes.includes("duplicate_rows"), "Duplicate rows detected");
  assert(issueTypes.includes("empty_column"), "Empty column detected");
  assert(issueTypes.includes("invalid_email"), "Invalid email detected");

  // Clean Messy
  const cleanActionRes = await fetch(`${API_BASE}/api/datasets/${messyId}/clean`, { method: "POST" });
  assert(cleanActionRes.status === 200, "Clean endpoint returns 200");
  const cleanActionData = await cleanActionRes.json();
  assert(cleanActionData.rows_removed >= 1, `Cleaned removed ${cleanActionData.rows_removed} duplicate rows`);
  assert(cleanActionData.cells_modified >= 1, `Cleaned modified ${cleanActionData.cells_modified} whitespace cells`);

  // Download Cleaned File
  const dlRes = await fetch(`${API_BASE}/api/datasets/${messyId}/download-cleaned`);
  assert(dlRes.status === 200, "Cleaned dataset download returns 200");
  const dlText = await dlRes.text();
  assert(!dlText.includes("  Alice In Wonderland  "), "Whitespace trimmed in downloaded file");

  // Report Export (HTML & PDF)
  console.log("\n[4] Testing Report Generation Endpoints...");
  const htmlRepRes = await fetch(`${API_BASE}/api/datasets/${messyId}/report/html`);
  assert(htmlRepRes.status === 200, "HTML report returns 200");
  const htmlRepText = await htmlRepRes.text();
  assert(htmlRepText.includes("DataLens AI"), "HTML report contains branding");
  assert(htmlRepText.includes("Overall Quality Score"), "HTML report contains overall score section");
  assert(htmlRepText.includes("Dimension Scores"), "HTML report contains dimension scores section");

  const pdfRepRes = await fetch(`${API_BASE}/api/datasets/${messyId}/report/pdf`);
  assert(pdfRepRes.status === 200, "PDF report returns 200");
  const pdfContentType = pdfRepRes.headers.get("content-type");
  assert(pdfContentType.includes("application/pdf"), "PDF report content-type is application/pdf");

  // 4. Error States & Rejection
  console.log("\n[5] Testing Error & Validation Rejection States...");
  // Unsupported extension
  const badExtBlob = new Blob([Buffer.from("dummy data")], { type: "text/plain" });
  const badExtForm = new FormData();
  badExtForm.append("file", badExtBlob, "malicious.exe");
  const badExtRes = await fetch(`${API_BASE}/api/datasets/upload`, { method: "POST", body: badExtForm });
  assert(badExtRes.status === 400, "Unsupported extension returns 400");

  // Missing dataset ID (404)
  const nonExistentRes = await fetch(`${API_BASE}/api/datasets/ffffffff-ffff-ffff-ffff-ffffffffffff/profile`, {
    method: "POST",
  });
  assert(nonExistentRes.status === 404, "Non-existent dataset ID returns 404");

  // Empty file (400)
  const emptyBlob = new Blob([Buffer.from("")], { type: "text/csv" });
  const emptyForm = new FormData();
  emptyForm.append("file", emptyBlob, "empty.csv");
  const emptyRes = await fetch(`${API_BASE}/api/datasets/upload`, { method: "POST", body: emptyForm });
  assert(emptyRes.status === 400, "Empty file returns 400");

  // Explicit Deletion (Lifecycle test)
  console.log("\n[6] Testing Explicit Dataset Deletion...");
  const delRes = await fetch(`${API_BASE}/api/datasets/${cleanId}`, { method: "DELETE" });
  assert(delRes.status === 200, "Dataset deletion returns 200");
  const delRes2 = await fetch(`${API_BASE}/api/datasets/${cleanId}`, { method: "DELETE" });
  assert(delRes2.status === 404, "Subsequent deletion returns 404");

  console.log(`\n======================================================`);
  console.log(`Summary: ${passed} assertions passed, ${failed} failed.`);
  console.log(`======================================================\n`);
}

runTests().catch((err) => {
  console.error("Test execution failed:", err);
  process.exit(1);
});
