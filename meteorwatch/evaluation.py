"""Coverage and inter-method agreement summaries for METEORWATCH.

This module evaluates the availability and agreement of saved detector outputs.
It does not estimate detector accuracy because the catalogue has no independently
verified anomaly labels. Agreement between two methods is not evidence that either
method is scientifically correct.
"""
from __future__ import annotations

from typing import Any
import math

import pandas as pd

from meteorwatch.agent import parse_saved_bool


OUTCOME_ORDER = [
    "Flagged by both methods",
    "IQR baseline only",
    "Isolation Forest only",
    "Neither method flagged",
]


def _read_flags(frame: pd.DataFrame, column: str) -> list[bool | None]:
    """Parse saved booleans conservatively: unknown values remain None."""
    if column not in frame.columns:
        return [None] * len(frame)
    return [parse_saved_bool(value) for value in frame[column].tolist()]


def _percent(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return numerator / denominator * 100.0


def build_detector_evaluation(frame: pd.DataFrame) -> dict[str, Any]:
    """Summarize detector coverage, paired outcomes, and agreement statistics.

    A record is comparable only when the baseline flag is known, the saved ML
    assessment is explicitly True, and the Isolation Forest flag is known.
    Missing assessment states are not inferred from a flag value.
    """
    baseline_flags = _read_flags(frame, "baseline_flag")
    assessed_values = _read_flags(frame, "ml_assessed")
    forest_flags = _read_flags(frame, "iforest_flag")
    total = len(frame)

    baseline_known = [value is not None for value in baseline_flags]
    baseline_flagged = [value is True for value in baseline_flags]
    ml_assessed = [value is True for value in assessed_values]
    ml_not_assessed = [value is False for value in assessed_values]
    ml_assessment_unknown = [value is None for value in assessed_values]
    forest_flag_known = [value is not None for value in forest_flags]

    paired_indices = [
        i for i in range(total)
        if assessed_values[i] is True
        and baseline_flags[i] is not None
        and forest_flags[i] is not None
    ]

    outcome_counts = {name: 0 for name in OUTCOME_ORDER}
    paired_baseline: list[bool] = []
    paired_forest: list[bool] = []
    for i in paired_indices:
        baseline = bool(baseline_flags[i])
        forest = bool(forest_flags[i])
        paired_baseline.append(baseline)
        paired_forest.append(forest)
        if baseline and forest:
            outcome_counts["Flagged by both methods"] += 1
        elif baseline:
            outcome_counts["IQR baseline only"] += 1
        elif forest:
            outcome_counts["Isolation Forest only"] += 1
        else:
            outcome_counts["Neither method flagged"] += 1

    comparable = len(paired_indices)
    both = outcome_counts["Flagged by both methods"]
    baseline_only = outcome_counts["IQR baseline only"]
    forest_only = outcome_counts["Isolation Forest only"]
    neither = outcome_counts["Neither method flagged"]
    agreements = both + neither
    observed_agreement = agreements / comparable if comparable else None

    if comparable:
        baseline_yes = both + baseline_only
        baseline_no = forest_only + neither
        forest_yes = both + forest_only
        forest_no = baseline_only + neither
        expected_agreement = (
            (baseline_yes / comparable) * (forest_yes / comparable)
            + (baseline_no / comparable) * (forest_no / comparable)
        )
        if math.isclose(1.0 - expected_agreement, 0.0, abs_tol=1e-12):
            cohen_kappa = None
        else:
            cohen_kappa = (observed_agreement - expected_agreement) / (1.0 - expected_agreement)
        flagged_union = both + baseline_only + forest_only
        jaccard_flag_overlap = both / flagged_union if flagged_union else None
    else:
        expected_agreement = None
        cohen_kappa = None
        jaccard_flag_overlap = None

    ml_flag_without_assessment = sum(
        assessed_values[i] is False and forest_flags[i] is not None
        for i in range(total)
    )
    ml_flag_assessment_unknown = sum(
        assessed_values[i] is None and forest_flags[i] is not None
        for i in range(total)
    )
    ml_assessed_but_flag_missing = sum(
        assessed_values[i] is True and forest_flags[i] is None
        for i in range(total)
    )

    ml_result_available = sum(
        assessed_values[i] is True and forest_flags[i] is not None
        for i in range(total)
    )
    ml_flagged = sum(
        assessed_values[i] is True and forest_flags[i] is True
        for i in range(total)
    )

    return {
        "total_records": total,
        "baseline_results_available": sum(baseline_known),
        "baseline_flagged_total": sum(baseline_flagged),
        "baseline_coverage_pct": _percent(sum(baseline_known), total),
        "ml_explicitly_assessed": sum(ml_assessed),
        "ml_assessed_pct": _percent(sum(ml_assessed), total),
        "ml_explicitly_not_assessed": sum(ml_not_assessed),
        "ml_assessment_unknown": sum(ml_assessment_unknown),
        "iforest_result_available_among_assessed": ml_result_available,
        "iforest_flagged_among_available_results": ml_flagged,
        "comparable_pairs": comparable,
        "comparable_pct_of_loaded_records": _percent(comparable, total),
        "outcome_counts": outcome_counts,
        "agreement_count": agreements,
        "observed_agreement_pct": _percent(agreements, comparable),
        "cohen_kappa": cohen_kappa,
        "jaccard_flag_overlap_pct": (jaccard_flag_overlap * 100.0) if jaccard_flag_overlap is not None else None,
        "ml_marked_not_assessed_but_flag_exists": ml_flag_without_assessment,
        "ml_assessment_unknown_but_flag_exists": ml_flag_assessment_unknown,
        "ml_marked_assessed_but_flag_missing": ml_assessed_but_flag_missing,
    }


def build_detector_evaluation_table(frame: pd.DataFrame) -> pd.DataFrame:
    """Return a readable two-column metrics table suitable for CSV/XLSX."""
    metrics = build_detector_evaluation(frame)
    outcome_counts = metrics["outcome_counts"]

    def format_pct(value: float | None) -> str:
        return "Not defined" if value is None else f"{value:.2f}%"

    def format_number(value: float | None) -> str:
        return "Not defined" if value is None else f"{value:.4f}"

    rows = [
        ("Loaded records", metrics["total_records"], "All rows in the report supplied to this evaluation."),
        ("Baseline results available", metrics["baseline_results_available"], "Rows with a saved True/False baseline flag."),
        ("Baseline coverage", format_pct(metrics["baseline_coverage_pct"]), "Baseline-result availability divided by loaded rows."),
        ("Baseline flagged", metrics["baseline_flagged_total"], "Count of saved True baseline flags among rows."),
        ("ML explicitly assessed", metrics["ml_explicitly_assessed"], "Rows where ml_assessed is explicitly True."),
        ("ML assessed coverage", format_pct(metrics["ml_assessed_pct"]), "Explicitly assessed rows divided by loaded rows."),
        ("ML assessment status unknown", metrics["ml_assessment_unknown"], "Rows whose saved ML assessment status is missing or unrecognised."),
        ("Isolation Forest results available among assessed rows", metrics["iforest_result_available_among_assessed"], "Rows explicitly assessed and having a saved True/False model flag."),
        ("Isolation Forest flagged among available assessed results", metrics["iforest_flagged_among_available_results"], "Count of saved True Isolation Forest flags among available assessed results."),
        ("Comparable detector pairs", metrics["comparable_pairs"], "Both detector flags are known and ML assessment is explicitly True."),
        ("Comparable pairs as share of loaded rows", format_pct(metrics["comparable_pct_of_loaded_records"]), "Pairwise comparison coverage; this is not a model-performance score."),
        ("Both methods flagged", outcome_counts["Flagged by both methods"], "Pairwise outcome count."),
        ("IQR baseline only", outcome_counts["IQR baseline only"], "Pairwise outcome count."),
        ("Isolation Forest only", outcome_counts["Isolation Forest only"], "Pairwise outcome count."),
        ("Neither method flagged", outcome_counts["Neither method flagged"], "Pairwise outcome count; this is not proof of safety."),
        ("Observed inter-method agreement", format_pct(metrics["observed_agreement_pct"]), "Share of comparable pairs where both methods agreed; not accuracy."),
        ("Cohen's kappa", format_number(metrics["cohen_kappa"]), "Chance-adjusted agreement between methods; not accuracy, and may be undefined for degenerate results."),
        ("Jaccard overlap of flagged records", format_pct(metrics["jaccard_flag_overlap_pct"]), "Intersection divided by union of flagged records among comparable pairs; not accuracy."),
        ("ML marked not assessed but flag exists", metrics["ml_marked_not_assessed_but_flag_exists"], "Saved-field inconsistency count; inspect these rows."),
        ("ML assessment unknown but flag exists", metrics["ml_assessment_unknown_but_flag_exists"], "Saved model flag exists while assessment status is unknown."),
        ("ML marked assessed but flag missing", metrics["ml_marked_assessed_but_flag_missing"], "Saved-field inconsistency or incomplete export; inspect these rows."),
        ("Ground-truth labels available", "No", "The project currently has no independently verified anomaly labels; precision, recall and accuracy are not estimated."),
    ]
    return pd.DataFrame(rows, columns=["Metric", "Value", "Interpretation"])


def build_event_level_comparison(frame: pd.DataFrame) -> pd.DataFrame:
    """Return a per-record comparison report, explicitly marking non-comparable rows."""
    baselines = _read_flags(frame, "baseline_flag")
    assessed_values = _read_flags(frame, "ml_assessed")
    forest_flags = _read_flags(frame, "iforest_flag")

    records: list[dict[str, Any]] = []
    for position, (index, row) in enumerate(frame.iterrows(), start=1):
        baseline = baselines[position - 1]
        assessed = assessed_values[position - 1]
        forest = forest_flags[position - 1]

        if assessed is False and forest is not None:
            outcome = "Inconsistent saved fields: ML not assessed but flag exists"
        elif assessed is False:
            outcome = "Not comparable: ML not assessed"
        elif assessed is None and forest is not None:
            outcome = "Not comparable: ML assessment status unknown"
        elif assessed is None:
            outcome = "Not comparable: ML assessment status unknown"
        elif baseline is None:
            outcome = "Not comparable: baseline flag unavailable"
        elif forest is None:
            outcome = "Not comparable: Isolation Forest flag unavailable"
        elif baseline and forest:
            outcome = "Flagged by both methods"
        elif baseline:
            outcome = "IQR baseline only"
        elif forest:
            outcome = "Isolation Forest only"
        else:
            outcome = "Neither method flagged"

        date_value = row.get("date")
        if pd.isna(date_value):
            date_text = "Unavailable"
        elif isinstance(date_value, pd.Timestamp):
            date_text = date_value.strftime("%Y-%m-%d %H:%M:%S GMT")
        else:
            date_text = str(date_value)

        energy_value = row.get("energy")
        if pd.isna(energy_value):
            energy_value = None

        def flag_text(value: bool | None) -> str:
            if value is None:
                return "Unknown"
            return "Yes" if value else "No"

        if assessed is False:
            forest_text = "Not assessed" if forest is None else ("Flag saved despite not assessed" if forest else "No flag saved despite not assessed")
        elif assessed is None and forest is None:
            forest_text = "Assessment status unknown"
        else:
            forest_text = flag_text(forest)

        records.append({
            "Loaded row number": position,
            "Event date/time (GMT)": date_text,
            "Reported radiated energy (×10¹⁰ J)": energy_value,
            "Saved review status": row.get("review_status", "Unavailable"),
            "IQR baseline flagged": flag_text(baseline),
            "ML assessed": flag_text(assessed),
            "Isolation Forest flagged": forest_text,
            "Pairwise comparison outcome": outcome,
            "Isolation Forest score": row.get("iforest_score"),
        })

    comparison = pd.DataFrame(records)
    if not comparison.empty:
        priorities = {
            "Flagged by both methods": 0,
            "Isolation Forest only": 1,
            "IQR baseline only": 2,
            "Inconsistent saved fields: ML not assessed but flag exists": 3,
            "Not comparable: baseline flag unavailable": 4,
            "Not comparable: Isolation Forest flag unavailable": 5,
            "Not comparable: ML assessment status unknown": 6,
            "Not comparable: ML not assessed": 7,
            "Neither method flagged": 8,
        }
        comparison["_sort"] = comparison["Pairwise comparison outcome"].map(priorities).fillna(9)
        comparison = comparison.sort_values(["_sort", "Loaded row number"], kind="stable").drop(columns="_sort")
        comparison = comparison.reset_index(drop=True)
    return comparison
