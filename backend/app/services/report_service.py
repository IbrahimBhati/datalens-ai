"""
Dataset Quality Report Generation Service.

Generates a comprehensive 12-section dataset quality report:
1. Dataset overview
2. Overall quality score
3. Dimension scores (Completeness, Validity, Uniqueness, Consistency)
4. Column profile
5. Missing-value analysis
6. Duplicate analysis
7. Validation problems
8. Outliers
9. Text-quality findings
10. AI-generated executive summary
11. Priority recommendations
12. Cleaning summary if cleaning was performed

Provides both:
- Print-friendly, high-fidelity standalone HTML report with @media print CSS
- Native binary PDF generation using ReportLab Platypus
- Strictly safe: never exposes internal prompts, API keys, or raw confidential rows
"""

import html
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import HTTPException, status
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.analyzers.analyzer import analyze_dataset_quality
from app.analyzers.profiler import locate_dataset_file, profile_dataset
from app.config import UPLOAD_DIR
from app.models.cleaning import CleanDatasetResponse
from app.services.ai_insight_service import generate_ai_insights
from app.services.scoring_service import compute_dataset_quality_score


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically compute and print total page counts."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))

        # Header running line
        self.drawString(
            54,
            11 * inch - 36,
            "DataLens AI — Comprehensive Dataset Quality & Hygiene Audit",
        )
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.5)
        self.line(54, 11 * inch - 42, 8.5 * inch - 54, 11 * inch - 42)

        # Footer running line
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(8.5 * inch - 54, 36, page_text)
        self.drawString(54, 36, "Confidential Quality Report • DataLens AI")
        self.line(54, 48, 8.5 * inch - 54, 48)
        self.restoreState()


async def gather_report_data(dataset_id: str) -> Dict[str, Any]:
    """
    Gather and normalize all 12 sections from actual analysis, profiling, scoring,
    insights, and cleaning audit data.
    """
    file_path, fmt = locate_dataset_file(dataset_id)
    profile = profile_dataset(dataset_id)
    analysis = analyze_dataset_quality(dataset_id)
    score_resp = compute_dataset_quality_score(dataset_id)
    ai_insights = await generate_ai_insights(dataset_id)

    # Check for optional cleaning audit
    upload_dir = Path(UPLOAD_DIR).resolve()
    cleaning_audit_path = upload_dir / f"{dataset_id}_cleaning_audit.json"
    cleaning_data: Optional[Dict[str, Any]] = None
    if cleaning_audit_path.exists() and cleaning_audit_path.is_file():
        try:
            with open(cleaning_audit_path, "r", encoding="utf-8") as f:
                cleaning_data = json.load(f)
        except Exception:
            cleaning_data = None

    # Aggregations for sections
    total_missing = sum(c.null_count for c in profile.columns)
    total_cells = profile.general.row_count * profile.general.column_count
    missing_pct = (total_missing / total_cells * 100) if total_cells > 0 else 0.0

    duplicate_issues = [i for i in analysis.issues if "duplicate" in i.type.lower()]
    validation_issues = [
        i for i in analysis.issues
        if any(k in i.type.lower() for k in ["invalid", "constant", "low_variance", "negative"])
    ]
    outlier_issues = [i for i in analysis.issues if "outlier" in i.type.lower()]
    text_columns = [c for c in profile.columns if c.inferred_type == "text" or c.text_stats is not None]

    report_timestamp = datetime.now(timezone.utc).strftime("%B %d, %Y at %H:%M UTC")

    return {
        "dataset_id": dataset_id,
        "filename": file_path.name,
        "format": fmt.upper(),
        "timestamp": report_timestamp,
        "profile": profile,
        "analysis": analysis,
        "score": score_resp,
        "ai_insights": ai_insights,
        "cleaning": cleaning_data,
        "total_missing": total_missing,
        "total_cells": total_cells,
        "missing_pct": missing_pct,
        "duplicate_issues": duplicate_issues,
        "validation_issues": validation_issues,
        "outlier_issues": outlier_issues,
        "text_columns": text_columns,
    }


async def generate_html_report(dataset_id: str) -> str:
    """
    Generate a standalone, print-friendly, executive HTML dataset quality report.
    """
    data = await gather_report_data(dataset_id)
    profile = data["profile"]
    analysis = data["analysis"]
    score = data["score"]
    ai = data["ai_insights"]
    cleaning = data["cleaning"]

    score_val = score.overall
    score_tier = "Excellent Quality" if score_val >= 85 else "Good Quality" if score_val >= 70 else "Moderate Risk" if score_val >= 50 else "Critical Degradation"
    tier_color = "#10b981" if score_val >= 85 else "#6366f1" if score_val >= 70 else "#f59e0b" if score_val >= 50 else "#ef4444"

    def escape(s: Any) -> str:
        return html.escape(str(s) if s is not None else "")

    # Build column profile rows
    column_rows_html = ""
    for col in profile.columns:
        stat_detail = "—"
        if col.numeric_stats and col.numeric_stats.mean is not None:
            stat_detail = f"Min: {col.numeric_stats.min:.1f} • Mean: {col.numeric_stats.mean:.1f} • Max: {col.numeric_stats.max:.1f}"
        elif col.text_stats and col.text_stats.avg_length is not None:
            stat_detail = f"Len min: {col.text_stats.min_length} • avg: {col.text_stats.avg_length:.1f} • max: {col.text_stats.max_length}"
        elif col.categorical_stats and col.categorical_stats.top_values:
            top_val = col.categorical_stats.top_values[0]
            stat_detail = f"Top: '{escape(top_val.value)}' ({top_val.percentage:.1f}%)"

        column_rows_html += f"""
        <tr>
            <td class="font-mono font-bold">{escape(col.name)}</td>
            <td><span class="badge badge-type">{escape(col.inferred_type)}</span></td>
            <td>{col.non_null_count:,}</td>
            <td>{col.null_count:,} ({col.null_percentage:.1f}%)</td>
            <td>{col.unique_count:,} ({col.unique_percentage:.1f}%)</td>
            <td class="text-muted text-sm">{escape(stat_detail)}</td>
        </tr>
        """

    # Build issues rows for validation
    validation_rows_html = ""
    if data["validation_issues"]:
        for iss in data["validation_issues"]:
            validation_rows_html += f"""
            <tr>
                <td><span class="badge badge-{escape(iss.severity)}">{escape(iss.severity.upper())}</span></td>
                <td class="font-bold">{escape(iss.type.replace('_', ' ').title())}</td>
                <td class="font-mono">{escape(iss.column or 'Entire Dataset')}</td>
                <td>{iss.affected_rows:,} ({iss.percentage:.1f}%)</td>
                <td>{escape(iss.description)}</td>
            </tr>
            """
    else:
        validation_rows_html = "<tr><td colspan='5' class='text-center text-muted py-3'>No structural validation violations detected.</td></tr>"

    # Outliers HTML
    outliers_html = ""
    if data["outlier_issues"]:
        for out in data["outlier_issues"]:
            outliers_html += f"""
            <div class="card mb-2">
                <div class="flex justify-between">
                    <span class="font-mono font-bold">{escape(out.column)}</span>
                    <span class="badge badge-warning">{out.affected_rows} outliers ({out.percentage:.1f}%)</span>
                </div>
                <p class="text-sm mt-1">{escape(out.description)}</p>
                <div class="text-xs text-muted mt-1">Method: {escape(out.method)}</div>
            </div>
            """
    else:
        outliers_html = "<p class='text-muted'>No statistical outliers detected beyond standard IQR / z-score thresholds.</p>"

    # Priority recommendations
    recommendations_html = ""
    for rec in ai.priority_issues:
        recommendations_html += f"""
        <div class="card mb-3">
            <div class="flex justify-between items-center mb-1">
                <span class="font-bold text-base">{escape(rec.issue)}</span>
                <span class="badge badge-high">{escape(rec.importance.upper())}</span>
            </div>
            <div class="text-sm text-slate-700 mb-1"><strong>Why it matters:</strong> {escape(rec.explanation)}</div>
            <div class="text-sm text-emerald-800"><strong>Recommendation:</strong> {escape(rec.recommendation)}</div>
        </div>
        """

    # Cleaning sequence
    cleaning_plan_html = ""
    for idx, step in enumerate(ai.cleaning_plan):
        cleaning_plan_html += f"""
        <li class="mb-1 text-sm"><strong>Step {idx + 1}:</strong> {escape(step)}</li>
        """

    # Cleaning Summary if performed
    cleaning_summary_html = ""
    if cleaning:
        trans_rows = ""
        for t in cleaning.get("transformations_performed", []):
            trans_rows += f"""
            <tr>
                <td class="font-bold">{escape(t.get('type', '').replace('_', ' ').title())}</td>
                <td>{escape(t.get('description', ''))}</td>
                <td>{t.get('affected_rows', 0):,}</td>
                <td>{t.get('cells_modified', 0):,}</td>
            </tr>
            """
        warnings_items = "".join(f"<li>{escape(w)}</li>" for w in cleaning.get("warnings", []))

        cleaning_summary_html = f"""
        <div class="grid grid-4 gap-2 mb-3">
            <div class="stat-box">
                <div class="stat-label">Original Rows</div>
                <div class="stat-value">{cleaning.get('original_rows', 0):,}</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">Cleaned Rows</div>
                <div class="stat-value text-emerald">{cleaning.get('cleaned_rows', 0):,}</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">Rows Removed</div>
                <div class="stat-value text-amber">{cleaning.get('rows_removed', 0):,}</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">Cells Modified</div>
                <div class="stat-value">{cleaning.get('cells_modified', 0):,}</div>
            </div>
        </div>

        <table class="data-table mb-3">
            <thead>
                <tr>
                    <th>Transformation</th>
                    <th>Description</th>
                    <th>Affected Rows</th>
                    <th>Cells Modified</th>
                </tr>
            </thead>
            <tbody>
                {trans_rows}
            </tbody>
        </table>

        {f'<div class="callout callout-warning mt-2"><strong>Preserved Non-Destructively (Advisories):</strong><ul>{warnings_items}</ul></div>' if warnings_items else ''}
        """
    else:
        cleaning_summary_html = """
        <div class="callout callout-info">
            <strong>Optional Cleaning Not Yet Executed:</strong>
            Dataset cleaning has not yet been executed on this session. Non-destructive cleaning (deduplication, whitespace normalization, and placeholder standardization) is available on-demand via the DataLens AI dashboard.
        </div>
        """

    # Score explanations
    explanations_html = "".join(f"<li>{escape(e)}</li>" for e in score.explanation)

    # HTML Document with print stylesheet
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dataset Quality Audit Report — {escape(data['filename'])}</title>
    <style>
        :root {{
            --primary: #4f46e5;
            --slate-900: #0f172a;
            --slate-800: #1e293b;
            --slate-600: #475569;
            --slate-100: #f1f5f9;
            --slate-50: #f8fafc;
            --emerald: #059669;
            --rose: #e11d48;
            --amber: #d97706;
            --border: #e2e8f0;
        }}
        * {{ box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            color: var(--slate-900);
            background: #ffffff;
            margin: 0;
            padding: 24px;
            line-height: 1.5;
            font-size: 13px;
        }}
        .container {{
            max-width: 960px;
            margin: 0 auto;
        }}
        header.report-header {{
            border-bottom: 2px solid var(--primary);
            padding-bottom: 16px;
            margin-bottom: 24px;
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
        }}
        .title-area h1 {{
            margin: 0 0 4px 0;
            font-size: 24px;
            font-weight: 800;
            color: var(--slate-900);
        }}
        .title-area p {{
            margin: 0;
            color: var(--slate-600);
            font-size: 12px;
        }}
        .btn-print {{
            background: var(--primary);
            color: #ffffff;
            border: none;
            border-radius: 8px;
            padding: 8px 16px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .btn-print:hover {{ background: #4338ca; }}
        h2.section-title {{
            font-size: 15px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--slate-800);
            border-bottom: 1px solid var(--border);
            padding-bottom: 6px;
            margin-top: 28px;
            margin-bottom: 14px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .section-num {{
            background: var(--primary);
            color: white;
            border-radius: 4px;
            padding: 1px 6px;
            font-size: 11px;
        }}
        .grid {{ display: grid; gap: 12px; }}
        .grid-2 {{ grid-template-columns: 1fr 1fr; }}
        .grid-4 {{ grid-template-columns: repeat(4, 1fr); }}
        .card {{
            border: 1px solid var(--border);
            border-radius: 8px;
            background: var(--slate-50);
            padding: 12px 14px;
        }}
        .stat-box {{
            border: 1px solid var(--border);
            border-radius: 8px;
            background: #ffffff;
            padding: 10px 12px;
            text-align: center;
        }}
        .stat-label {{
            font-size: 10px;
            text-transform: uppercase;
            color: var(--slate-600);
            font-weight: 600;
            letter-spacing: 0.05em;
        }}
        .stat-value {{
            font-size: 18px;
            font-weight: 800;
            font-family: monospace;
            color: var(--slate-900);
            margin-top: 2px;
        }}
        .score-banner {{
            display: flex;
            align-items: center;
            gap: 24px;
            background: #f8fafc;
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 16px 20px;
        }}
        .score-circle {{
            width: 72px;
            height: 72px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 26px;
            font-weight: 800;
            font-family: monospace;
            color: #ffffff;
            background: {tier_color};
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
            flex-shrink: 0;
        }}
        .data-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
            margin-top: 8px;
        }}
        .data-table th {{
            background: var(--slate-100);
            color: var(--slate-800);
            font-weight: 600;
            text-align: left;
            padding: 8px 10px;
            border: 1px solid var(--border);
            font-size: 11px;
            text-transform: uppercase;
        }}
        .data-table td {{
            padding: 7px 10px;
            border: 1px solid var(--border);
            color: var(--slate-800);
        }}
        .data-table tbody tr:nth-child(even) {{ background: #fbfcfe; }}
        .badge {{
            display: inline-block;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 10px;
            font-weight: 700;
            font-family: monospace;
            text-transform: uppercase;
        }}
        .badge-type {{ background: #e0e7ff; color: #3730a3; }}
        .badge-high {{ background: #ffe4e6; color: #9f1239; }}
        .badge-medium {{ background: #fef3c7; color: #92400e; }}
        .badge-low {{ background: #e0f2fe; color: #075985; }}
        .badge-warning {{ background: #fef3c7; color: #92400e; }}
        .callout {{
            border-left: 4px solid var(--primary);
            background: #f8fafc;
            padding: 10px 14px;
            border-radius: 0 6px 6px 0;
            font-size: 12px;
        }}
        .callout-info {{ border-color: #3b82f6; background: #eff6ff; }}
        .callout-warning {{ border-color: #f59e0b; background: #fffbeb; }}
        .font-mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }}
        .font-bold {{ font-weight: 700; }}
        .text-muted {{ color: var(--slate-600); }}
        .text-emerald {{ color: var(--emerald); }}
        .text-amber {{ color: var(--amber); }}
        .text-rose {{ color: var(--rose); }}
        .flex {{ display: flex; }}
        .justify-between {{ justify-content: space-between; }}
        .items-center {{ align-items: center; }}
        .mb-1 {{ margin-bottom: 4px; }}
        .mb-2 {{ margin-bottom: 8px; }}
        .mb-3 {{ margin-bottom: 12px; }}
        .mt-1 {{ margin-top: 4px; }}
        .mt-2 {{ margin-top: 8px; }}
        .py-3 {{ padding-top: 12px; padding-bottom: 12px; }}
        .text-center {{ text-align: center; }}

        /* --- PRINT STYLESHEET (PAGE BREAKS & VECTOR OUTPUT) --- */
        @media print {{
            body {{
                padding: 0;
                font-size: 11px;
                color: #000000;
            }}
            .no-print {{ display: none !important; }}
            .container {{ max-width: 100%; }}
            .card, .stat-box, .score-banner {{
                box-shadow: none !important;
                border: 1px solid #cbd5e1 !important;
            }}
            .page-break-before {{ page-break-before: always; break-before: page; }}
            .avoid-break {{ page-break-inside: avoid; break-inside: avoid; }}
            @page {{
                size: A4 portrait;
                margin: 12mm;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Top Banner / Print Button -->
        <header class="report-header">
            <div class="title-area">
                <h1>DataLens AI Dataset Quality Report</h1>
                <p>Audited: <strong>{escape(data['filename'])}</strong> ({escape(data['format'])}) • Generated on {escape(data['timestamp'])}</p>
            </div>
            <div class="no-print">
                <button type="button" class="btn-print" onclick="window.print()">
                    🖨️ Print / Save as PDF
                </button>
            </div>
        </header>

        <!-- SECTION 1: DATASET OVERVIEW -->
        <h2 class="section-title"><span class="section-num">1</span> Dataset Overview</h2>
        <div class="grid grid-4 mb-3">
            <div class="stat-box">
                <div class="stat-label">Total Rows</div>
                <div class="stat-value">{profile.general.row_count:,}</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">Total Columns</div>
                <div class="stat-value">{profile.general.column_count}</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">Memory Footprint</div>
                <div class="stat-value">{escape(profile.general.memory_usage_human)}</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">Format</div>
                <div class="stat-value">{escape(data['format'])}</div>
            </div>
        </div>

        <!-- SECTION 2: OVERALL QUALITY SCORE -->
        <h2 class="section-title"><span class="section-num">2</span> Overall Quality Score</h2>
        <div class="score-banner mb-3 avoid-break">
            <div class="score-circle">
                {score.overall}
            </div>
            <div>
                <h3 style="margin:0 0 4px 0; font-size:16px;">{escape(score_tier)} ({score.overall} / 100)</h3>
                <p class="text-muted" style="margin:0 0 6px 0;">
                    Deterministic, weighted quality index derived across 4 structural dimensions.
                </p>
                <ul class="text-sm" style="margin:0; padding-left:18px;">
                    {explanations_html}
                </ul>
            </div>
        </div>

        <!-- SECTION 3: DIMENSION SCORES -->
        <h2 class="section-title"><span class="section-num">3</span> Dimension Scores</h2>
        <div class="grid grid-4 mb-3 avoid-break">
            <div class="stat-box">
                <div class="stat-label">Completeness</div>
                <div class="stat-value">{score.dimensions.completeness}%</div>
                <span class="text-muted text-xs">Missing value rate</span>
            </div>
            <div class="stat-box">
                <div class="stat-label">Validity</div>
                <div class="stat-value">{score.dimensions.validity}%</div>
                <span class="text-muted text-xs">Format & bounds</span>
            </div>
            <div class="stat-box">
                <div class="stat-label">Uniqueness</div>
                <div class="stat-value">{score.dimensions.uniqueness}%</div>
                <span class="text-muted text-xs">Row/ID duplicates</span>
            </div>
            <div class="stat-box">
                <div class="stat-label">Consistency</div>
                <div class="stat-value">{score.dimensions.consistency}%</div>
                <span class="text-muted text-xs">Variance & outliers</span>
            </div>
        </div>

        <!-- SECTION 4: COLUMN PROFILE -->
        <h2 class="section-title page-break-before"><span class="section-num">4</span> Column Profile & Schema Distribution</h2>
        <table class="data-table mb-3">
            <thead>
                <tr>
                    <th>Column Name</th>
                    <th>Inferred Type</th>
                    <th>Non-Null</th>
                    <th>Null Count (%)</th>
                    <th>Unique Count (%)</th>
                    <th>Summary Stats / Top Values</th>
                </tr>
            </thead>
            <tbody>
                {column_rows_html}
            </tbody>
        </table>

        <!-- SECTION 5: MISSING-VALUE ANALYSIS -->
        <h2 class="section-title avoid-break"><span class="section-num">5</span> Missing-Value Analysis</h2>
        <div class="grid grid-2 mb-3 avoid-break">
            <div class="stat-box">
                <div class="stat-label">Total Missing Cells</div>
                <div class="stat-value text-amber">{data['total_missing']:,}</div>
                <span class="text-muted text-xs">{data['missing_pct']:.2f}% of all cells across dataset</span>
            </div>
            <div class="stat-box">
                <div class="stat-label">Columns with Missing Data</div>
                <div class="stat-value">{len([c for c in profile.columns if c.null_count > 0])} of {profile.general.column_count}</div>
                <span class="text-muted text-xs">Requires imputation or column dropping</span>
            </div>
        </div>

        <!-- SECTION 6: DUPLICATE ANALYSIS -->
        <h2 class="section-title avoid-break"><span class="section-num">6</span> Duplicate Analysis</h2>
        <div class="card mb-3 avoid-break">
            {f"<p><strong>Exact Duplicate Rows:</strong> {data['duplicate_issues'][0].affected_rows} rows ({data['duplicate_issues'][0].percentage:.1f}% of dataset). {escape(data['duplicate_issues'][0].description)}</p>" if data['duplicate_issues'] else "<p class='text-muted'>Zero exact duplicate rows detected in this dataset.</p>"}
        </div>

        <!-- SECTION 7: VALIDATION PROBLEMS -->
        <h2 class="section-title avoid-break"><span class="section-num">7</span> Validation & Integrity Problems</h2>
        <table class="data-table mb-3 avoid-break">
            <thead>
                <tr>
                    <th>Severity</th>
                    <th>Issue Type</th>
                    <th>Target Column</th>
                    <th>Affected</th>
                    <th>Explanation</th>
                </tr>
            </thead>
            <tbody>
                {validation_rows_html}
            </tbody>
        </table>

        <!-- SECTION 8: OUTLIERS -->
        <h2 class="section-title avoid-break"><span class="section-num">8</span> Statistical Outlier Detection</h2>
        <div class="avoid-break">
            {outliers_html}
        </div>

        <!-- SECTION 9: TEXT-QUALITY FINDINGS -->
        <h2 class="section-title page-break-before"><span class="section-num">9</span> Text-Quality Findings & Hygiene</h2>
        <div class="card mb-3">
            {f"<ul style='margin:0; padding-left:18px;'>{''.join(f'<li><strong>{escape(col.name)}</strong>: min len {col.text_stats.min_length}, avg len {col.text_stats.avg_length:.1f}, max len {col.text_stats.max_length}</li>' for col in data['text_columns'] if col.text_stats)}</ul>" if data['text_columns'] else "<p class='text-muted'>No text-inferred columns in this dataset.</p>"}
            {f"<div class='mt-2'><strong>Text Hygiene Observations:</strong><ul>{''.join(f'<li>{escape(o)}</li>' for o in ai.text_observations)}</ul></div>" if ai.text_observations else ""}
        </div>

        <!-- SECTION 10: AI-GENERATED EXECUTIVE SUMMARY -->
        <h2 class="section-title avoid-break"><span class="section-num">10</span> AI Executive Summary</h2>
        <div class="callout callout-info mb-3 avoid-break">
            <p style="margin:0; font-size:13px; line-height:1.6;">
                {escape(ai.summary)}
            </p>
        </div>

        <!-- SECTION 11: PRIORITY RECOMMENDATIONS -->
        <h2 class="section-title avoid-break"><span class="section-num">11</span> Priority Remediation Roadmap</h2>
        <div class="avoid-break mb-3">
            {recommendations_html}
            <div class="card mt-2">
                <h4 style="margin:0 0 6px 0; font-size:12px; text-transform:uppercase;">Suggested Cleaning Sequence:</h4>
                <ol style="margin:0; padding-left:18px;">
                    {cleaning_plan_html}
                </ol>
            </div>
        </div>

        <!-- SECTION 12: CLEANING SUMMARY -->
        <h2 class="section-title avoid-break"><span class="section-num">12</span> Cleaning Summary (Non-Destructive Operations)</h2>
        <div class="avoid-break">
            {cleaning_summary_html}
        </div>

        <!-- Footer -->
        <footer style="margin-top:36px; padding-top:16px; border-top:1px solid var(--border); text-align:center; color:var(--slate-600); font-size:11px;">
            Generated by <strong>DataLens AI</strong> • Deterministic Quality Profiler & Secure AI Insights Layer • Confidential Document
        </footer>
    </div>
</body>
</html>
    """
    return html_content


async def generate_pdf_report(dataset_id: str) -> bytes:
    """
    Generate a clean, high-fidelity binary PDF dataset quality report using ReportLab.
    """
    data = await gather_report_data(dataset_id)
    profile = data["profile"]
    analysis = data["analysis"]
    score = data["score"]
    ai = data["ai_insights"]
    cleaning = data["cleaning"]

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0f172a"),
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#64748b"),
    )
    h2_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#1e293b"),
        spaceBefore=14,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "BodyDark",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#1e293b"),
    )
    body_bold = ParagraphStyle(
        "BodyBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#0f172a"),
    )
    bullet_style = ParagraphStyle(
        "BulletText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#334155"),
        leftIndent=12,
    )
    callout_style = ParagraphStyle(
        "CalloutText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#1e293b"),
    )

    elements: List[Any] = []

    # Title Banner
    elements.append(Paragraph("DataLens AI — Dataset Quality Report", title_style))
    elements.append(
        Paragraph(
            f"Dataset: <b>{html.escape(data['filename'])}</b> ({data['format']}) • Generated {data['timestamp']}",
            subtitle_style,
        )
    )
    elements.append(Spacer(1, 10))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#4f46e5"), spaceAfter=14))

    # 1. Dataset Overview Table
    elements.append(Paragraph("1. Dataset Overview", h2_style))
    overview_table_data = [
        ["Total Rows", f"{profile.general.row_count:,}", "Format", data["format"]],
        ["Total Columns", str(profile.general.column_count), "Memory Footprint", profile.general.memory_usage_human],
        ["Total Cells", f"{data['total_cells']:,}", "Missing Cell Rate", f"{data['missing_pct']:.2f}%"],
    ]
    t_overview = Table(overview_table_data, colWidths=[100, 150, 100, 150])
    t_overview.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#0f172a")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(t_overview)
    elements.append(Spacer(1, 12))

    # 2 & 3. Quality Score & Dimension Scores
    elements.append(Paragraph("2. Overall Quality Score & Dimension Breakdown", h2_style))
    score_table_data = [
        ["Overall Quality Score", f"{score.overall} / 100", "Target Benchmark", "≥ 85 / 100"],
        ["Completeness", f"{score.dimensions.completeness}%", "Validity", f"{score.dimensions.validity}%"],
        ["Uniqueness", f"{score.dimensions.uniqueness}%", "Consistency", f"{score.dimensions.consistency}%"],
    ]
    t_score = Table(score_table_data, colWidths=[130, 120, 120, 130])
    t_score.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e0e7ff")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
        ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 1), (2, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(t_score)

    if score.explanation:
        elements.append(Spacer(1, 6))
        for exp in score.explanation:
            elements.append(Paragraph(f"• {html.escape(exp)}", bullet_style))
    elements.append(Spacer(1, 12))

    # 4. Column Profile Table
    elements.append(Paragraph("4. Column Profile Summary", h2_style))
    col_table_data = [["Column", "Type", "Non-Null", "Null %", "Unique %", "Profile Summary"]]
    for col in profile.columns:
        summary_txt = "—"
        if col.numeric_stats and col.numeric_stats.mean is not None:
            summary_txt = f"[{col.numeric_stats.min:.1f}, {col.numeric_stats.max:.1f}] μ={col.numeric_stats.mean:.1f}"
        elif col.text_stats and col.text_stats.avg_length is not None:
            summary_txt = f"len avg={col.text_stats.avg_length:.1f} (max {col.text_stats.max_length})"
        elif col.categorical_stats and col.categorical_stats.top_values:
            top_val = col.categorical_stats.top_values[0]
            summary_txt = f"top: '{top_val.value[:10]}' ({top_val.percentage:.0f}%)"

        col_table_data.append([
            col.name[:18],
            col.inferred_type,
            f"{col.non_null_count:,}",
            f"{col.null_percentage:.1f}%",
            f"{col.unique_percentage:.1f}%",
            summary_txt[:32],
        ])

    t_cols = Table(col_table_data, colWidths=[90, 60, 60, 50, 50, 190])
    t_cols.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    elements.append(t_cols)
    elements.append(Spacer(1, 14))

    # 5, 6, 7. Missing Values, Duplicates & Validation Problems
    elements.append(Paragraph("5 & 6. Missing Values & Duplicate Records", h2_style))
    dup_str = f"{data['duplicate_issues'][0].affected_rows} duplicate rows ({data['duplicate_issues'][0].percentage:.1f}%)" if data["duplicate_issues"] else "0 duplicates detected"
    elements.append(Paragraph(
        f"<b>Missing Values:</b> {data['total_missing']:,} total null cells ({data['missing_pct']:.2f}%).<br/>"
        f"<b>Duplicate Rows:</b> {dup_str}.",
        body_style,
    ))
    elements.append(Spacer(1, 8))

    elements.append(Paragraph("7. Integrity & Validation Problems", h2_style))
    if data["validation_issues"]:
        val_table_data = [["Severity", "Issue", "Column", "Rows", "Explanation"]]
        for iss in data["validation_issues"][:8]:  # Top 8
            val_table_data.append([
                iss.severity.upper(),
                iss.type.replace("_", " ").title()[:18],
                (iss.column or "Dataset")[:14],
                f"{iss.affected_rows:,}",
                iss.description[:60],
            ])
        t_val = Table(val_table_data, colWidths=[55, 95, 80, 50, 220])
        t_val.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        elements.append(t_val)
    else:
        elements.append(Paragraph("No validation problems detected.", body_style))
    elements.append(Spacer(1, 14))

    # 8 & 9. Outliers & Text Findings
    elements.append(Paragraph("8 & 9. Outliers & Text-Quality Findings", h2_style))
    outlier_text = f"{len(data['outlier_issues'])} numeric outlier anomaly rules triggered." if data["outlier_issues"] else "No significant statistical outliers detected."
    text_text = f"{len(data['text_columns'])} text columns identified." if data["text_columns"] else "No text columns identified."
    elements.append(Paragraph(f"<b>Outliers:</b> {outlier_text} • <b>Text Quality:</b> {text_text}", body_style))
    elements.append(Spacer(1, 14))

    # 10. AI Executive Summary
    elements.append(Paragraph("10. AI-Generated Executive Summary", h2_style))
    summary_box_data = [[Paragraph(html.escape(ai.summary), callout_style)]]
    t_summary = Table(summary_box_data, colWidths=[500])
    t_summary.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eff6ff")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#93c5fd")),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    elements.append(t_summary)
    elements.append(Spacer(1, 14))

    # 11. Priority Recommendations & Cleaning Plan
    elements.append(Paragraph("11. Priority Recommendations", h2_style))
    for rec in ai.priority_issues[:4]:
        elements.append(Paragraph(f"• <b>{html.escape(rec.issue)}</b> ({rec.importance}): {html.escape(rec.recommendation)}", bullet_style))
    elements.append(Spacer(1, 14))

    # 12. Cleaning Summary if performed
    elements.append(Paragraph("12. Dataset Cleaning Summary", h2_style))
    if cleaning:
        clean_info = (
            f"<b>Cleaning Executed:</b> Removed {cleaning.get('rows_removed', 0):,} rows, "
            f"modified {cleaning.get('cells_modified', 0):,} cells. "
            f"Cleaned dataset: {cleaning.get('cleaned_rows', 0):,} rows (original: {cleaning.get('original_rows', 0):,})."
        )
        elements.append(Paragraph(clean_info, body_style))
    else:
        elements.append(Paragraph(
            "<i>Dataset cleaning has not yet been executed on this session. "
            "Safe, non-destructive cleaning can be performed anytime via the DataLens AI dashboard.</i>",
            body_style,
        ))

    # Build PDF with dynamic page numbering
    doc.build(elements, canvasmaker=NumberedCanvas)
    return buffer.getvalue()
