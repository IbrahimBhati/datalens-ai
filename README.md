# DataLens AI — Intelligent Dataset Quality Analyzer

DataLens AI is a modern, production-grade dataset profiling, quality auditing, and remediation platform. It deterministically analyzes tabular files (CSV and JSON), detects anomalies across four structural dimensions (**Completeness**, **Validity**, **Uniqueness**, and **Consistency**), generates transparent 0–100 quality scores, offers non-destructive dataset cleaning, produces print-friendly HTML and vector PDF reports, and delivers AI-guided executive insights with guaranteed deterministic fallback.

---

## Features

- **Multi-Format Ingestion:** Drag-and-drop or file-picker upload for CSV, JSON arrays, and JSON Lines (up to 50 MB).
- **Deterministic Profiling:** Instant computation of row/column dimensions, memory footprint, inferred types, null counts, distinct values, numerical statistics (min, max, mean, median, quartiles), and categorical distributions without invoking an LLM.
- **Automated Anomaly Detection:** Rule-based detection of missing values, empty columns, exact duplicate records, identifier collisions, malformed emails, malformed phone numbers, out-of-range metrics, impossible percentages, constant columns, and statistical outliers (1.5x IQR).
- **Transparent 0–100 Quality Scoring:** Explainable weighted scoring across Completeness, Validity, Uniqueness, and Consistency with explicit deduction breakdowns.
- **AI-Powered Insights:** Contextual executive summaries, prioritized quality risks, and recommended cleaning plans powered by Google Gemini or OpenAI with guaranteed local deterministic fallbacks.
- **Non-Destructive Cleaning Engine:** Automated duplicate removal, whitespace trimming, and placeholder standardization that saves a separate cleaned file without altering the original.
- **Executive Export:** Standalone printable HTML report and downloadable multi-page vector PDF report generated via ReportLab.
- **Security & Privacy-First:** Automatic 24-hour temporary file pruning, user-initiated purge API, in-memory sliding-window rate limiting, and zero raw dataset transmission to AI providers (PII regex scrubbing).

---

## Architecture

DataLens AI uses a decoupled client-server architecture:

```
User Device (Phone, Tablet, Laptop)
   │
   ▼ HTTPS
┌───────────────────────────────────────────┐
│     DataLens AI Frontend (Next.js 16)     │
│             Hosted on Vercel              │
└─────────────────────┬─────────────────────┘
                      │ REST API / JSON (CORS)
                      ▼ HTTPS
┌───────────────────────────────────────────┐
│      DataLens AI Backend (FastAPI)        │
│             Hosted on Render              │
│  ┌─────────────────────────────────────┐  │
│  │ Security & Rate Limiting Middleware │  │
│  └──────────────────┬──────────────────┘  │
│                     │                     │
│         ┌───────────┴───────────┐         │
│         ▼                       ▼         │
│  ┌──────────────┐       ┌──────────────┐  │
│  │ Profiling &  │       │  AI Insight  │  │
│  │ Rule Engine  │       │  Layer & PII │  │
│  │   (Pandas)   │       │   Scrubber   │  │
│  └──────────────┘       └───────┬──────┘  │
└─────────────────────────────────┼─────────┘
                                  │ HTTPS (Prompt Isolated)
                                  ▼
                     ┌────────────────────────┐
                     │ Google Gemini / OpenAI │
                     │   (Optional / Safe)    │
                     └────────────────────────┘
```

---

## Tech Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | Next.js 16 (App Router), React 19, TypeScript 5, Tailwind CSS 4, Turbopack |
| **Backend** | Python 3.10+, FastAPI, Uvicorn (ASGI), Pandas, NumPy, Pydantic v2, ReportLab |
| **Testing** | Pytest, pytest-asyncio, AnyIO, Node.js Contract Runner, pip-audit, ESLint |
| **Hosting** | Vercel (Frontend), Render (Backend Web Service) |

---

## Local Development

### 1. Backend Setup
```bash
# Navigate to backend
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Verify the backend is live by opening `http://localhost:8000/health` (returns `{"status": "ok"}`).

### 2. Frontend Setup
```bash
# Open a separate terminal in frontend
cd frontend

# Install dependencies
npm install

# Start Next.js development server
npm run dev
```
Open `http://localhost:3000` in your web browser.

---

## Environment Variables

### Backend Configuration (`backend/.env`)

| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `PORT` | `8000` | Port for the ASGI server to bind (set automatically by Render). |
| `HOST` | `0.0.0.0` | Network interface to bind. |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated list of allowed frontend origins. |
| `CORS_ORIGIN_REGEX` | `^https:\/\/.*\.vercel\.app$` | Regex allowing all Vercel deployment preview URLs. |
| `MAX_UPLOAD_SIZE` | `52428800` | Maximum file size in bytes (50 MB). |
| `UPLOAD_DIR` | System Tempdir | Directory for temporary dataset storage. |
| `LLM_API_KEY` | *(empty)* | Optional API key for Google Gemini or OpenAI. Fallback engine works if empty. |
| `LLM_PROVIDER` | `gemini` | `gemini` or `openai`. |
| `LLM_MODEL` | `gemini-2.5-flash` | Target LLM model identifier. |
| `DATASET_RETENTION_HOURS` | `24` | Hours to retain temporary files before automated cleanup. |
| `RATE_LIMIT_REQUESTS_PER_MINUTE` | `120` | In-memory sliding-window request limit per client IP. |

### Frontend Configuration (`frontend/.env.local`)

| Variable | Example Value | Purpose |
| :--- | :--- | :--- |
| `NEXT_PUBLIC_API_URL` | `https://datalens-api.onrender.com` | Base URL of deployed backend (no trailing slash). |

---

## Step-by-Step Deployment Guide (Vercel + Render)

Follow these steps to deploy DataLens AI so you can access it from any phone, tablet, or computer even when your laptop is turned off.

### Step 1: Push Project to GitHub
1. Initialize Git in the project root:
   ```bash
   git init
   git add .
   git commit -m "feat: complete production-ready DataLens AI"
   ```
2. Create a new private or public repository on [GitHub](https://github.com).
3. Push your repository:
   ```bash
   git remote add origin https://github.com/YOUR_USERNAME/datalens-ai.git
   git branch -M main
   git push -u origin main
   ```

### Step 2: Deploy Backend to Render (Free Tier)
1. Go to [Render.com](https://render.com) and create an account / sign in.
2. Click **New +** $\rightarrow$ **Web Service**.
3. Select **Build and deploy from a Git repository** and connect your GitHub repo.
4. Configure the service settings:
   - **Name:** `datalens-backend`
   - **Region:** Any region close to you (e.g., Oregon, Frankfurt)
   - **Branch:** `main`
   - **Root Directory:** *(leave blank, or set to `backend`)*
   - **Runtime:** `Python 3`
   - **Build Command:** `cd backend && pip install -r requirements.txt`
   - **Start Command:** `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Plan:** `Free`
5. In **Advanced** $\rightarrow$ **Health Check Path**, enter: `/health`
6. Add Environment Variables in the Render dashboard:
   - `CORS_ORIGINS`: `http://localhost:3000` *(you will add your Vercel URL in Step 4)*
   - `CORS_ORIGIN_REGEX`: `^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?$|^https:\/\/.*\.vercel\.app$`
   - `LLM_PROVIDER`: `gemini` *(or openai)*
   - `LLM_MODEL`: `gemini-2.5-flash`
   - `LLM_API_KEY`: *(Optional: paste your Google Gemini API key here)*
7. Click **Create Web Service**. Wait 2–3 minutes for deployment.
8. Copy your Render URL (e.g. `https://datalens-backend.onrender.com`).
9. Verify health in your browser: `https://datalens-backend.onrender.com/health` (should display `{"status": "ok"}`).

### Step 3: Deploy Frontend to Vercel (Free Tier)
1. Go to [Vercel.com](https://vercel.com) and sign in with GitHub.
2. Click **Add New...** $\rightarrow$ **Project**.
3. Select your `datalens-ai` repository.
4. In the Project Configuration screen:
   - **Framework Preset:** `Next.js`
   - **Root Directory:** Click Edit and select `frontend`
5. Expand **Environment Variables** and add:
   - **Key:** `NEXT_PUBLIC_API_URL`
   - **Value:** `https://datalens-backend.onrender.com` *(your Render backend URL from Step 2, without a trailing slash)*
6. Click **Deploy**. Vercel will build and assign you a live domain (e.g. `https://datalens-ai.vercel.app`).

### Step 4: Update Backend CORS Whitelist
1. Return to your [Render Dashboard](https://dashboard.render.com) for `datalens-backend`.
2. Go to **Environment** $\rightarrow$ Edit `CORS_ORIGINS`.
3. Set value to:
   ```
   http://localhost:3000,https://datalens-ai.vercel.app
   ```
   *(Replace with your actual Vercel URL)*.
4. Save Changes. Render will automatically apply the changes.

### Step 5: Test the Deployed System End-to-End
1. Open your Vercel URL on your mobile phone or laptop browser: `https://datalens-ai.vercel.app`.
2. Observe the header status badge: it should turn green: **API: Active (ok)**.
   *(Note: On Render's free tier, inactive services sleep after 15 minutes. The frontend header will display "Offline" while waking up, and automatically transitions to "Active" within 30–50s).*
3. Upload `test-data/clean.csv` or `test-data/messy.csv`.
4. Click **Analyze Dataset** to test profiling, anomaly detection, scoring, and AI insights.
5. In the cleaning panel, click **Clean Dataset Safely** and verify **Download Cleaned Dataset**.
6. In the header, click **Export PDF Report** to test report generation.

---

## API Reference

All functional endpoints are prefixed with `/api`. A root `/health` endpoint is provided for cloud load balancers.

| Method | Route | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Cloud platform health check (returns `{"status": "ok"}`). |
| `GET` | `/api/health` | Legacy API health check. |
| `POST` | `/api/datasets/upload` | Uploads and validates CSV/JSON dataset. Returns `dataset_id`. |
| `POST` | `/api/datasets/{id}/profile` | Computes column stats, distributions, and null metrics. |
| `POST` | `/api/datasets/{id}/analyze` | Detects data quality anomalies (duplicates, outliers, etc.). |
| `POST` | `/api/datasets/{id}/score` | Calculates transparent 0–100 quality score and explanations. |
| `POST` | `/api/datasets/{id}/ai-insights` | Generates executive summary and cleaning plan. |
| `POST` | `/api/datasets/{id}/clean` | Executes safe, non-destructive cleaning transformations. |
| `GET` | `/api/datasets/{id}/download-cleaned` | Streams cleaned dataset file attachment. |
| `GET` | `/api/datasets/{id}/report/html` | Serves printable executive HTML audit report. |
| `GET` | `/api/datasets/{id}/report/pdf` | Streams downloadable vector PDF report (ReportLab). |
| `DELETE`| `/api/datasets/{id}` | Explicitly deletes temporary dataset files from server disk. |

---

## Security & Data Privacy

1. **Stateless Processing:** Dataset files are treated as ephemeral processing jobs. Datasets are saved with random UUIDs (`{id}.csv`) and are never written to a permanent database.
2. **Automated Pruning (TTL):** Files older than `DATASET_RETENTION_HOURS` (24h) are deleted automatically on startup and periodic maintenance. Users can purge files immediately via `DELETE /api/datasets/{id}`.
3. **No Raw Data to LLMs:** Complete raw datasets are **never** transmitted to AI providers. Only high-level column metrics and up to 2 regex-sanitized text samples are sent.
4. **PII Scrubbing:** Samples pass through `redact_pii_text()`, masking emails (`[EMAIL_REDACTED]`), phone numbers (`[PHONE_REDACTED]`), and SSNs (`[SSN_REDACTED]`).
5. **Zero Secret Leakage:** AI API keys remain server-side. For Google Gemini, keys are sent via the `x-goog-api-key` HTTP header rather than URL query parameters to avoid proxy log exposure.
6. **Rate Limiting & Exception Shielding:** In-memory sliding-window rate limiting (120 req/min) prevents burst abuse. Server exceptions return generic 500 error messages without stack traces.

---

## Dataset Handling & Testing

Realistic sample files are provided in [`test-data/`](file:///f:/DATASET%20QUALITY%20CHECKER/test-data):
- **`clean.csv`**: Flawless tabular dataset (100/100 score).
- **`messy.csv`**: Demonstrates duplicates, negative spend, bad emails, empty columns, and IQR outliers.
- **`duplicates.csv`**: Tests exact row deduplication and primary key collisions.
- **`missing_values.csv`**: Demonstrates high null percentages and empty columns.
- **`invalid_values.csv`**: Tests range violations, bad dates, and impossible percentages.

### Running Test Suites
```bash
# Backend pytest suite (80 tests)
cd backend
python -m pytest -v

# Frontend lint & type checking
cd frontend
npm run lint
npx tsc --noEmit

# Frontend end-to-end contract suite (41 assertions)
cd frontend
npm test

# Production build test
cd frontend
npm run build
```

---

## Troubleshooting

- **Frontend displays "API: Offline":** If hosted on Render's free tier, the backend sleeps after 15 minutes of inactivity. Allow 30–50 seconds for the instance to wake up; the frontend polls automatically every 12 seconds and will reconnect without a page refresh.
- **CORS Error in Browser Console:** Verify that your Vercel URL is added to `CORS_ORIGINS` in your Render dashboard, or verify that `CORS_ORIGIN_REGEX` is enabled.
- **AI Insights Timeout:** If the AI provider is slow or an invalid API key is provided, DataLens AI automatically falls back to its deterministic rule engine to generate quality summaries without crashing.
