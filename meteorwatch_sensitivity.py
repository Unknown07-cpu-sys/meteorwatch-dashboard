"""Score-threshold sensitivity analysis for METEORWATCH.

This module does not refit Isolation Forest. It examines how the selected
records change when different contamination-style score cutoffs are applied
to the already-saved Isolation Forest decision scores. Lower scores are treated
as more unusual, matching the convention used by the dashboard's event sorter.

The outputs are descriptive sensitivity analyses, not anomaly ground truth,
model accuracy, or physical hazard assessments.
"""
from __future__ import annotations

from typing import Any, Iterable
import math

import numpy as np
import pandas as pd

from meteorwatch_agent import parse_saved_bool


DEFAULT_CONTAMINATION_LEVELS: tuple[float, ...] = (
    0.01, 0.025, 0.05, 0.075, 0.10, 0.15
)
REFERENCE_CONTAMINATION = 0.05

SUMMARY_COLUMNS = [
    "Score threshold setting (%)",
    "Score cutoff (lower = more unusual)",
    "Records flagged",
    "Actual flagged share of scored records (%)",
    "Jaccard overlap vs 5% reference (%)",
    "Additional flags vs 5% reference",
    "Flags removed vs 5% reference",
]


def _validated_levels(levels: Iterable[float]) -> list[float]:
    values = {float(level) for level in levels}
    values.add(REFERENCE_CONTAMINATION)
    for value in values:
        if not math.isfinite(value) or value <= 0 or value > 0.50:
            raise ValueError("Each threshold setting must be greater than 0 and at most 0.50 (50%).")
    return sorted(values)


def _display_flag(value: bool | None) -> str:
    if value is None:
        return "Unknown"
    return "Yes" if value else "No"


def _date_text(value: Any) -> str:
    if value is None:
        return "Unavailable"
    try:
        if pd.isna(value):
            return "Unavailable"
    except (TypeError, ValueError):
        pass
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d %H:%M:%S GMT")
    return str(value)


def build_score_threshold_sensitivity(
    frame: pd.DataFrame,
    contamination_levels: Iterable[float] = DEFAULT_CONTAMINATION_LEVELS,
) -> dict[str, Any]:
    """Build threshold-sensitivity summary and record-level comparison.

    Only rows with `ml_assessed` explicitly True and a finite saved
    `iforest_score` are included in threshold calculations. Missing or unknown
    assessment states and missing scores remain visible in the event detail
    export, but are never silently counted as unflagged.

    The threshold is computed as the requested percentile of the saved scores;
    a row is selected only when its score is strictly below the cutoff, matching
    the decision-score convention used by Isolation Forest. Tied values at the
    cutoff are therefore not all forced into the flagged set.
    """
    levels = _validated_levels(contamination_levels)
    total = len(frame)

    assessment = (
        [parse_saved_bool(value) for value in frame["ml_assessed"].tolist()]
        if "ml_assessed" in frame.columns else [None] * total
    )
    saved_flags = (
        [parse_saved_bool(value) for value in frame["iforest_flag"].tolist()]
        if "iforest_flag" in frame.columns else [None] * total
    )
    if "iforest_score" in frame.columns:
        scores_series = pd.to_numeric(frame["iforest_score"], errors="coerce")
        scores = scores_series.to_numpy(dtype=float, na_value=np.nan)
    else:
        scores = np.full(total, np.nan, dtype=float)

    finite_score = np.isfinite(scores)
    eligible = np.array([
        assessment[i] is True and finite_score[i]
        for i in range(total)
    ], dtype=bool)
    eligible_positions = np.flatnonzero(eligible)
    eligible_scores = scores[eligible]

    summary_rows: list[dict[str, Any]] = []
    scenario_masks: dict[float, np.ndarray] = {}
    cutoffs: dict[float, float] = {}

    if len(eligible_scores):
        for level in levels:
            cutoff = float(np.percentile(eligible_scores, level * 100.0))
            mask = eligible_scores < cutoff
            cutoffs[level] = cutoff
            scenario_masks[level] = mask

        reference_mask = scenario_masks[REFERENCE_CONTAMINATION]
        for level in levels:
            mask = scenario_masks[level]
            intersection = int(np.logical_and(mask, reference_mask).sum())
            union = int(np.logical_or(mask, reference_mask).sum())
            jaccard = (intersection / union * 100.0) if union else None
            summary_rows.append({
                "Score threshold setting (%)": round(level * 100.0, 3),
                "Score cutoff (lower = more unusual)": cutoffs[level],
                "Records flagged": int(mask.sum()),
                "Actual flagged share of scored records (%)": float(mask.mean() * 100.0),
                "Jaccard overlap vs 5% reference (%)": jaccard,
                "Additional flags vs 5% reference": int(np.logical_and(mask, ~reference_mask).sum()),
                "Flags removed vs 5% reference": int(np.logical_and(reference_mask, ~mask).sum()),
            })

        reference_mask = scenario_masks[REFERENCE_CONTAMINATION]
        saved_known = np.array([saved_flags[pos] is not None for pos in eligible_positions], dtype=bool)
        saved_values = np.array([
            bool(saved_flags[pos]) if saved_flags[pos] is not None else False
            for pos in eligible_positions
        ], dtype=bool)
        saved_reference_disagreements = int(
            np.logical_and(saved_known, reference_mask != saved_values).sum()
        )
        saved_flags_comparable = int(saved_known.sum())
    else:
        saved_reference_disagreements = None
        saved_flags_comparable = 0

    detail_rows: list[dict[str, Any]] = []
    for position, (_, row) in enumerate(frame.iterrows(), start=1):
        state = assessment[position - 1]
        has_score = bool(finite_score[position - 1])
        if state is False:
            eligibility = "Not assessed"
        elif state is None:
            eligibility = "Assessment status unknown"
        elif not has_score:
            eligibility = "Score unavailable"
        else:
            eligibility = "Included in threshold study"

        saved_flag = saved_flags[position - 1]
        detail: dict[str, Any] = {
            "Loaded row number": position,
            "Event date/time (GMT)": _date_text(row.get("date")),
            "Reported radiated energy (×10¹⁰ J)": row.get("energy"),
            "ML assessment status": (
                "Assessed" if state is True else "Not assessed" if state is False else "Unknown"
            ),
            "Saved Isolation Forest flag": _display_flag(saved_flag),
            "Saved Isolation Forest score": scores[position - 1] if has_score else None,
            "Threshold-study eligibility": eligibility,
        }
        if has_score:
            detail["Saved Isolation Forest score"] = float(scores[position - 1])
        for level in levels:
            label = f"Flag at {level * 100:g}% setting"
            if eligible[position - 1]:
                detail[label] = (
                    "Yes" if scenario_masks[level][int(np.searchsorted(eligible_positions, position - 1))]
                    else "No"
                )
            else:
                detail[label] = eligibility
        detail_rows.append(detail)

    summary = pd.DataFrame(summary_rows, columns=SUMMARY_COLUMNS)
    event_detail = pd.DataFrame(detail_rows)

    explicitly_assessed = sum(value is True for value in assessment)
    not_assessed = sum(value is False for value in assessment)
    assessment_unknown = sum(value is None for value in assessment)
    assessed_without_score = sum(
        assessment[i] is True and not finite_score[i] for i in range(total)
    )

    metadata = {
        "total_records": total,
        "explicitly_assessed_records": explicitly_assessed,
        "not_assessed_records": not_assessed,
        "assessment_status_unknown_records": assessment_unknown,
        "assessed_records_without_finite_score": assessed_without_score,
        "eligible_scored_records": int(eligible.sum()),
        "excluded_records": total - int(eligible.sum()),
        "saved_flags_comparable_at_reference": saved_flags_comparable,
        "reference_saved_flag_disagreements": saved_reference_disagreements,
        "reference_threshold_cutoff": cutoffs.get(REFERENCE_CONTAMINATION),
        "reference_records_flagged": int(scenario_masks[REFERENCE_CONTAMINATION].sum()) if len(eligible_scores) else 0,
        "threshold_levels_pct": [round(level * 100.0, 3) for level in levels],
        "note": (
            "Uses existing saved Isolation Forest decision scores only. It does not refit the model, "
            "change the stored flags, or establish which records are true anomalies."
        ),
    }

    return {
        "summary": summary,
        "event_detail": event_detail,
        "metadata": metadata,
    }


def build_sensitivity_summary_table(frame: pd.DataFrame) -> pd.DataFrame:
    """Return a compact metrics table suitable for Excel and documentation."""
    result = build_score_threshold_sensitivity(frame)
    meta = result["metadata"]
    rows = [
        ("Loaded records", meta["total_records"], "All rows supplied to this analysis."),
        ("ML explicitly assessed", meta["explicitly_assessed_records"], "Only records whose saved ml_assessed value is explicitly True."),
        ("ML marked not assessed", meta["not_assessed_records"], "Excluded from score-threshold calculations."),
        ("ML assessment status unknown", meta["assessment_status_unknown_records"], "Excluded; unknown is not treated as not assessed or unflagged."),
        ("Assessed records without a finite score", meta["assessed_records_without_finite_score"], "Excluded because a saved numeric Isolation Forest score is unavailable."),
        ("Eligible scored records", meta["eligible_scored_records"], "Records used for all contamination-style score thresholds."),
        ("Reference setting", "5%", "The reference threshold for relative overlap calculations; this does not alter saved labels."),
        ("Reference setting flags", meta["reference_records_flagged"], "Count below the 5th-percentile cutoff using a strict less-than comparison."),
        ("Saved flags available for reference comparison", meta["saved_flags_comparable_at_reference"], "Eligible records with a known saved Isolation Forest flag."),
        ("Reference flags differing from saved flags", meta["reference_saved_flag_disagreements"] if meta["reference_saved_flag_disagreements"] is not None else "Not available", "A consistency check between the saved 5% flags and the score-derived 5% threshold. Review differences; rounded scores or ties may contribute."),
        ("Method scope", "Threshold sensitivity only", "Uses saved decision scores; does not refit Isolation Forest or change stored detector results."),
        ("Ground-truth anomaly labels", "Unavailable", "The dataset has no independently verified anomaly labels, so these results are not accuracy, precision, or recall."),
    ]
    if result["summary"].empty:
        rows.append(("Study availability", "Not available", "No records have both explicit ML assessment and a finite saved Isolation Forest score."))
    else:
        rows.append(("Study availability", "Available", "See the sensitivity scenarios for threshold-dependent selected-record counts and overlap."))
    return pd.DataFrame(rows, columns=["Metric", "Value", "Interpretation"])
