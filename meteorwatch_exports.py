"""Structured workbook export helpers for METEORWATCH.

Workbook sheets are intended for human review and reproducibility. They do not
establish a physical hazard rating or validate source measurements.
"""
from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from typing import Any

import pandas as pd

from meteorwatch_agent import build_structured_review_export, run_agent_self_tests
from meteorwatch_evaluation import build_detector_evaluation_table
from meteorwatch_sensitivity import build_sensitivity_summary_table


QUALITY_FIELDS: dict[str, str] = {
    "date": "Event date/time (GMT)",
    "energy": "Reported radiated energy (×10¹⁰ J)",
    "impact-e": "Estimated impact energy (kt)",
    "lat": "Latitude magnitude",
    "lon": "Longitude magnitude",
    "alt": "Altitude at peak brightness (km)",
    "vel": "Reported scalar velocity (km/s)",
    "vx": "Velocity component vx (km/s)",
    "vy": "Velocity component vy (km/s)",
    "vz": "Velocity component vz (km/s)",
    "component_speed": "Speed calculated from vx/vy/vz (km/s)",
    "map_latitude": "Valid signed map latitude",
    "map_longitude": "Valid signed map longitude",
}


def _build_quality_table(frame: pd.DataFrame) -> pd.DataFrame:
    total = len(frame)
    rows: list[dict[str, Any]] = []
    for column, label in QUALITY_FIELDS.items():
        if column not in frame.columns:
            continue
        missing = int(frame[column].isna().sum())
        rows.append({
            "Field": label,
            "Source field": column,
            "Available values": total - missing,
            "Missing values": missing,
            "Missing (%)": round(missing / total * 100, 2) if total else 0.0,
        })
    return pd.DataFrame(rows, columns=[
        "Field", "Source field", "Available values", "Missing values", "Missing (%)"
    ])


def _build_status_summary(frame: pd.DataFrame) -> pd.DataFrame:
    if "review_status" not in frame.columns:
        return pd.DataFrame(columns=["Review status", "Records", "Share of filtered rows (%)"])
    counts = (
        frame["review_status"].fillna("Status unavailable")
        .astype(str).value_counts(dropna=False)
        .rename_axis("Review status").reset_index(name="Records")
    )
    total = len(frame)
    counts["Share of filtered rows (%)"] = (
        (counts["Records"] / total * 100).round(2) if total else 0.0
    )
    return counts


def _style_workbook(writer: pd.ExcelWriter, frame_map: dict[str, pd.DataFrame]) -> None:
    workbook = writer.book
    header_format = workbook.add_format({
        "bold": True,
        "text_wrap": True,
        "valign": "vcenter",
        "bg_color": "#16324F",
        "font_color": "#FFFFFF",
        "border": 0,
    })
    wrapped_format = workbook.add_format({"text_wrap": True, "valign": "top"})
    percent_format = workbook.add_format({"num_format": "0.00"})

    for sheet_name, frame in frame_map.items():
        worksheet = writer.sheets[sheet_name]
        worksheet.freeze_panes(1, 0)
        worksheet.hide_gridlines(2)
        if len(frame.columns):
            worksheet.autofilter(0, 0, max(0, len(frame)), len(frame.columns) - 1)
            for col_index, column in enumerate(frame.columns):
                worksheet.write(0, col_index, str(column), header_format)
                sample_values = [str(column)]
                if not frame.empty:
                    sample_values.extend(frame[column].dropna().astype(str).head(60).tolist())
                natural_width = max((len(value) for value in sample_values), default=10) + 2
                width = min(max(natural_width, 12), 46)
                column_lower = str(column).lower()
                is_long_text = any(word in column_lower for word in (
                    "explanation", "interpretation", "missing", "quality", "action",
                    "purpose", "details", "limitation", "warning", "note", "meaning",
                ))
                if is_long_text:
                    width = max(width, 32)
                    worksheet.set_column(col_index, col_index, width, wrapped_format)
                elif "%" in str(column):
                    worksheet.set_column(col_index, col_index, width, percent_format)
                else:
                    worksheet.set_column(col_index, col_index, width)
            worksheet.set_row(0, 34)
        else:
            worksheet.set_column(0, 0, 24)
        if sheet_name == "Event Review" and len(frame.columns) > 5:
            worksheet.freeze_panes(1, 3)


def build_review_workbook(filtered_df: pd.DataFrame, full_df: pd.DataFrame | None = None) -> bytes:
    """Create a formatted multi-sheet Excel workbook for the current filtered view.

    Sheets: Start Here, Event Review, Technical Data, Data Quality, Review Status,
    Detector Evaluation, Sensitivity Study, and Agent Tests. `full_df` supplies the
    catalogue-wide row count and sensitivity analysis; other data sheets use the filtered view.
    """
    filtered = filtered_df.copy()
    full = full_df if full_df is not None else filtered_df

    review = build_structured_review_export(filtered)
    technical = filtered.drop(columns=["map_latitude", "map_longitude"], errors="ignore").copy()
    quality = _build_quality_table(filtered)
    status_summary = _build_status_summary(filtered)
    agent_tests = run_agent_self_tests()
    detector_evaluation = build_detector_evaluation_table(filtered)
    # Keep this catalogue-wide so it matches the Agent Test Lab, which evaluates the full report.
    sensitivity_study = build_sensitivity_summary_table(full)

    generated_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    start_here = pd.DataFrame([
        {"Item": "Project", "Details": "METEORWATCH — historical fireball event analysis and review assistant."},
        {"Item": "Purpose", "Details": "Organise recorded events, explain saved detector results, and help a human reviewer inspect records."},
        {"Item": "Workbook generated", "Details": generated_utc},
        {"Item": "Loaded catalogue rows", "Details": int(len(full))},
        {"Item": "Rows in current filtered view", "Details": int(len(filtered))},
        {"Item": "Event Review sheet", "Details": "Readable event-level review report with method flags, explanations, missing fields, and suggested review action."},
        {"Item": "Technical Data sheet", "Details": "Filtered source/technical fields retained for analysis. Derived map coordinates are omitted to match the technical CSV export."},
        {"Item": "Data Quality sheet", "Details": "Missing-value counts and percentages for available key fields in the current filtered view."},
        {"Item": "Review Status sheet", "Details": "Count and share of each saved review status in the current filtered view."},
        {"Item": "Detector Evaluation sheet", "Details": "Coverage and inter-method agreement among comparable saved flags. Agreement is not accuracy; no independently verified anomaly labels are available."},
        {"Item": "Sensitivity Study sheet", "Details": "Catalogue-wide threshold sensitivity using existing saved Isolation Forest decision scores. It does not refit the model or change stored flags."},
        {"Item": "Agent Tests sheet", "Details": "Synthetic software logic tests. These are not ground-truth event labels or detector-accuracy measurements."},
        {"Item": "Interpretation boundary", "Details": "A flag is a prompt for human review, not proof of danger. An unflagged event is not proven safe. METEORWATCH does not predict future impacts."},
        {"Item": "Location note", "Details": "Reported coordinates correspond to peak-brightness location where available, not necessarily a ground impact site."},
        {"Item": "Model coverage note", "Details": "Not assessed is different from not flagged. Missing values are not replaced with zero in these reports."},
        {"Item": "Data source", "Details": "NASA/JPL Fireball Data API: https://ssd-api.jpl.nasa.gov/doc/fireball.html"},
    ])

    sheets = {
        "Start Here": start_here,
        "Event Review": review,
        "Technical Data": technical,
        "Data Quality": quality,
        "Review Status": status_summary,
        "Detector Evaluation": detector_evaluation,
        "Sensitivity Study": sensitivity_study,
        "Agent Tests": agent_tests,
    }

    output = BytesIO()
    with pd.ExcelWriter(
        output,
        engine="xlsxwriter",
        datetime_format="yyyy-mm-dd hh:mm:ss",
        date_format="yyyy-mm-dd",
    ) as writer:
        for sheet_name, frame in sheets.items():
            frame.to_excel(writer, sheet_name=sheet_name, index=False, na_rep="")
        _style_workbook(writer, sheets)

    return output.getvalue()
