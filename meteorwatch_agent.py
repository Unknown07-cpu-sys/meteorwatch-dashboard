"""Transparent decision and explanation logic for the METEORWATCH prototype.

This module interprets saved detector flags. It does not train a detector, predict
future impacts, or decide whether a physical event is dangerous.
"""
from __future__ import annotations

from typing import Any, Mapping
import math

import numpy as np
import pandas as pd


_COMPLETE_DECISIONS = {
    "Flagged by both methods",
    "IQR baseline only",
    "Isolation Forest only",
    "Neither method flagged",
}


def _get(row: Any, key: str, default: Any = None) -> Any:
    """Read a value from a dict-like record or pandas Series."""
    try:
        return row.get(key, default)
    except AttributeError:
        try:
            return row[key]
        except (KeyError, TypeError, IndexError):
            return default


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    try:
        result = pd.isna(value)
        if isinstance(result, (bool, np.bool_)):
            return bool(result)
    except (TypeError, ValueError):
        pass
    return False


def parse_saved_bool(value: Any) -> bool | None:
    """Parse a saved boolean. Missing/unknown values stay None, never False."""
    if _is_missing(value):
        return None
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n"}:
        return False
    return None


def _display(value: Any, digits: int = 3) -> str:
    if _is_missing(value):
        return "Unavailable in this record"
    if isinstance(value, (int, float, np.integer, np.floating)):
        numeric = float(value)
        if not math.isfinite(numeric):
            return "Unavailable in this record"
        return f"{numeric:,.{digits}f}"
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d %H:%M:%S GMT")
    return str(value)


def assess_event(row: Any) -> dict[str, Any]:
    """Interpret saved rule/model flags without treating missing as negative."""
    baseline = parse_saved_bool(_get(row, "baseline_flag"))
    forest_flag = parse_saved_bool(_get(row, "iforest_flag"))
    explicit_assessed = parse_saved_bool(_get(row, "ml_assessed"))

    # Only infer model coverage from the flag if the report has no explicit value.
    # An explicit False is authoritative; a missing flag is not a negative result.
    if explicit_assessed is None:
        ml_assessed = forest_flag is not None
    else:
        ml_assessed = explicit_assessed

    if ml_assessed is True:
        if baseline is True and forest_flag is True:
            decision = "Flagged by both methods"
        elif baseline is True and forest_flag is False:
            decision = "IQR baseline only"
        elif baseline is False and forest_flag is True:
            decision = "Isolation Forest only"
        elif baseline is False and forest_flag is False:
            decision = "Neither method flagged"
        elif forest_flag is True:
            decision = "Isolation Forest flagged; baseline status unavailable"
        elif forest_flag is False:
            decision = "Isolation Forest did not flag; baseline status unavailable"
        elif baseline is True:
            decision = "Baseline flagged; Isolation Forest result unavailable"
        elif baseline is False:
            decision = "Baseline did not flag; Isolation Forest result unavailable"
        else:
            decision = "Detection status incomplete"
    elif ml_assessed is False:
        if baseline is True:
            decision = "Baseline flagged; ML not assessed"
        elif baseline is False:
            decision = "ML not assessed; baseline did not flag"
        else:
            decision = "Detection status incomplete"
    else:
        if baseline is True:
            decision = "Baseline flagged; ML assessment status unknown"
        elif baseline is False:
            decision = "Baseline did not flag; ML assessment status unknown"
        else:
            decision = "Detection status incomplete"

    reasons: list[str] = []
    if baseline is True:
        reasons.append(
            "**IQR baseline:** the saved energy-only statistical rule flagged this record for review."
        )
    elif baseline is False:
        reasons.append(
            "**IQR baseline:** the saved rule did not flag this record. This is not a safety clearance."
        )
    else:
        reasons.append("**IQR baseline:** no usable saved flag is available for this record.")

    if ml_assessed is True and forest_flag is True:
        reasons.append(
            "**Isolation Forest:** the saved model result flagged this record. The experiment uses log-energy, altitude, and speed magnitude calculated from vx, vy, and vz."
        )
    elif ml_assessed is True and forest_flag is False:
        reasons.append(
            "**Isolation Forest:** the saved model result did not flag this record under the project's current settings; that does not prove the event is normal or safe."
        )
    elif ml_assessed is False:
        reasons.append(
            "**Isolation Forest:** this record is marked as not assessed. A missing model result must not be interpreted as a negative result."
        )
    else:
        reasons.append(
            "**Isolation Forest:** the saved result does not establish whether this record was flagged."
        )

    if ml_assessed is False and forest_flag is not None:
        reasons.append(
            "**Consistency note:** the report contains an Isolation Forest flag value even though `ml_assessed` is false. Check the exported report and model pipeline."
        )

    date_value = _get(row, "date")
    if _is_missing(date_value):
        date_text = "Unavailable"
    elif isinstance(date_value, pd.Timestamp):
        date_text = date_value.strftime("%Y-%m-%d %H:%M:%S GMT")
    else:
        date_text = str(date_value)

    missing_fields: list[str] = []
    field_labels = {
        "energy": "reported radiated energy",
        "impact-e": "estimated impact energy",
        "alt": "altitude at peak brightness",
        "vx": "velocity component vx",
        "vy": "velocity component vy",
        "vz": "velocity component vz",
        "component_speed": "component-derived speed",
        "map_latitude": "map latitude",
        "map_longitude": "map longitude",
    }
    for field, label in field_labels.items():
        if _is_missing(_get(row, field)):
            missing_fields.append(label)

    required_ml_fields = ["energy", "alt", "vx", "vy", "vz"]
    missing_ml_fields = [
        field for field in required_ml_fields if _is_missing(_get(row, field))
    ]

    warnings: list[str] = []
    energy = _get(row, "energy")
    try:
        energy_num = float(energy)
    except (TypeError, ValueError):
        energy_num = float("nan")
    if not math.isfinite(energy_num):
        warnings.append("Reported energy is unavailable or non-numeric.")
    elif energy_num <= 0:
        warnings.append("Reported energy is non-positive; check it before log-energy analysis.")

    if _is_missing(_get(row, "date")):
        warnings.append("Event date/time is missing, so the record cannot be placed reliably on a timeline.")
    if ml_assessed is False and not missing_ml_fields:
        warnings.append(
            "The saved report says ML was not assessed, but the usual required feature fields appear present. Check the original preprocessing/model export rather than assuming a result."
        )

    return {
        "decision_label": decision,
        "baseline_flag": baseline,
        "ml_assessed": ml_assessed,
        "iforest_flag": forest_flag,
        "date_text": date_text,
        "reasons": reasons,
        "missing_fields": missing_fields,
        "missing_ml_fields": missing_ml_fields,
        "warnings": warnings,
        "complete_decision": decision in _COMPLETE_DECISIONS,
    }


def build_agent_explanation(row: Any) -> str:
    """Create a structured, evidence-linked plain-language explanation."""
    assessment = assess_event(row)
    energy = _get(row, "energy")
    impact_energy = _get(row, "impact-e")
    altitude = _get(row, "alt")
    speed = _get(row, "component_speed")
    if _is_missing(speed):
        vx, vy, vz = (_get(row, k) for k in ("vx", "vy", "vz"))
        if all(not _is_missing(v) for v in (vx, vy, vz)):
            try:
                speed = math.sqrt(float(vx) ** 2 + float(vy) ** 2 + float(vz) ** 2)
            except (TypeError, ValueError, OverflowError):
                speed = None

    lines = [
        "### Agent decision",
        f"**Derived interpretation:** {assessment['decision_label']}",
        f"**Historical event time:** {assessment['date_text']}",
        "",
        "### What the record contains",
        f"- Reported total radiated energy: {_display(energy)} × 10¹⁰ joules.",
        f"- Estimated impact energy: {_display(impact_energy)} kt.",
        f"- Altitude at peak brightness: {_display(altitude)} km.",
        f"- Speed magnitude from velocity components: {_display(speed)} km/s.",
        "",
        "### Why this interpretation was made",
    ]
    lines.extend(f"- {reason}" for reason in assessment["reasons"])

    lines.extend(["", "### Missing data and coverage"])
    if assessment["missing_fields"]:
        lines.append("- Unavailable in this record: " + ", ".join(assessment["missing_fields"]) + ".")
    else:
        lines.append("- The displayed fields in this record are present; completeness does not guarantee measurement accuracy.")

    if assessment["missing_ml_fields"]:
        lines.append(
            "- Fields used by the prototype's Isolation Forest experiment that are missing: "
            + ", ".join(assessment["missing_ml_fields"])
            + "."
        )
    elif assessment["ml_assessed"] is False:
        lines.append(
            "- The saved report marks this record as not assessed, although the usual model-input fields appear present. Review the source pipeline."
        )

    if assessment["warnings"]:
        lines.extend(["", "### Data checks"])
        lines.extend(f"- {warning}" for warning in assessment["warnings"])

    lines.extend([
        "",
        "### Interpretation boundary",
        "These are explanations of saved statistical flags, not proof of a physical cause. A flag is a prompt for human review, not a danger rating. An unflagged record is not proof of safety, and METEORWATCH does not predict future impacts.",
    ])
    return "\n".join(lines)


def run_agent_self_tests() -> pd.DataFrame:
    """Run deterministic logic tests using synthetic examples, not ground truth."""
    cases: list[dict[str, Any]] = []

    def record(name: str, expected: str, row: Mapping[str, Any], meaning: str) -> None:
        result = assess_event(row)
        observed = result["decision_label"]
        cases.append({
            "Test case": name,
            "Expected result": expected,
            "Observed result": observed,
            "Passed": observed == expected,
            "Purpose": meaning,
        })

    common = {
        "date": pd.Timestamp("2020-01-01"),
        "energy": 1.2,
        "impact-e": 0.1,
        "alt": 30.0,
        "vx": 1.0,
        "vy": 2.0,
        "vz": 3.0,
        "component_speed": float(np.sqrt(14)),
        "map_latitude": 1.0,
        "map_longitude": 2.0,
    }
    record(
        "Both methods flag",
        "Flagged by both methods",
        {**common, "baseline_flag": True, "iforest_flag": True, "ml_assessed": True},
        "A dual flag is described as review priority, not confirmed danger.",
    )
    record(
        "IQR baseline only",
        "IQR baseline only",
        {**common, "baseline_flag": True, "iforest_flag": False, "ml_assessed": True},
        "A baseline flag and a negative saved model flag stay distinct.",
    )
    record(
        "Isolation Forest only",
        "Isolation Forest only",
        {**common, "baseline_flag": False, "iforest_flag": True, "ml_assessed": True},
        "An ML-only flag is identified separately.",
    )
    record(
        "Neither method flagged",
        "Neither method flagged",
        {**common, "baseline_flag": False, "iforest_flag": False, "ml_assessed": True},
        "No flags are not treated as proof of safety.",
    )
    record(
        "Baseline flag; ML not assessed",
        "Baseline flagged; ML not assessed",
        {**common, "baseline_flag": True, "iforest_flag": None, "ml_assessed": False},
        "An unavailable ML result is not interpreted as False.",
    )
    record(
        "Baseline did not flag; ML not assessed",
        "ML not assessed; baseline did not flag",
        {**common, "baseline_flag": False, "iforest_flag": None, "ml_assessed": False},
        "No model result remains explicitly unassessed.",
    )
    missing_result = assess_event({
        **common,
        "baseline_flag": False,
        "iforest_flag": None,
        "ml_assessed": False,
        "alt": None,
        "vx": None,
        "vy": None,
        "vz": None,
        "component_speed": None,
    })
    missing_fields_observed = ", ".join(missing_result["missing_ml_fields"])
    cases.append({
        "Test case": "Missing ML features are surfaced",
        "Expected result": "alt, vx, vy, vz listed as missing",
        "Observed result": missing_fields_observed,
        "Passed": set(missing_result["missing_ml_fields"]) == {"alt", "vx", "vy", "vz"},
        "Purpose": "The explanation can state why an event may not have been assessed.",
    })
    missing_energy_text = build_agent_explanation({
        **common,
        "energy": None,
        "baseline_flag": None,
        "iforest_flag": None,
        "ml_assessed": False,
    })
    cases.append({
        "Test case": "Missing energy is not shown as zero",
        "Expected result": "Unavailable value and missing-energy warning",
        "Observed result": "Unavailable" if "Unavailable in this record × 10¹⁰ joules" in missing_energy_text and "energy is unavailable" in missing_energy_text.lower() else "Missing check",
        "Passed": "Unavailable in this record × 10¹⁰ joules" in missing_energy_text and "energy is unavailable" in missing_energy_text.lower(),
        "Purpose": "Missing values are not silently filled with zero.",
    })
    caution_text = build_agent_explanation({**common, "baseline_flag": False, "iforest_flag": False, "ml_assessed": True})
    cases.append({
        "Test case": "Scientific caution stays visible",
        "Expected result": "No danger rating or future-impact prediction claim",
        "Observed result": "Caution present" if "not a danger rating" in caution_text and "does not predict future impacts" in caution_text else "Caution missing",
        "Passed": "not a danger rating" in caution_text and "does not predict future impacts" in caution_text,
        "Purpose": "The tool avoids overclaiming from historical anomaly flags.",
    })

    return pd.DataFrame(cases)


def _canonical_status(value: Any) -> str | None:
    if _is_missing(value):
        return None
    key = " ".join(str(value).strip().lower().replace("_", " ").replace("-", " ").split())
    aliases = {
        "flagged by both methods": "Flagged by both methods",
        "both methods flagged": "Flagged by both methods",
        "iqr baseline only": "IQR baseline only",
        "isolation forest only": "Isolation Forest only",
        "baseline flagged; ml not assessed": "Baseline flagged; ML not assessed",
        "ml not assessed; baseline did not flag": "ML not assessed; baseline did not flag",
        "neither method flagged": "Neither method flagged",
        "neither method flagged this record": "Neither method flagged",
    }
    return aliases.get(key)


def audit_saved_statuses(df: pd.DataFrame) -> tuple[dict[str, int], pd.DataFrame]:
    """Compare saved review labels with decisions reconstructed from saved flags.

    Only rows with a known baseline flag, explicit ML assessment and known ML flag
    are eligible. Unknown/incomplete statuses are counted as not comparable.
    """
    counts = {
        "total_rows": int(len(df)),
        "comparable_rows": 0,
        "matching_rows": 0,
        "mismatching_rows": 0,
        "not_comparable_rows": 0,
    }
    mismatches: list[dict[str, Any]] = []
    for index, row in df.iterrows():
        result = assess_event(row)
        baseline = result["baseline_flag"]
        forest = result["iforest_flag"]
        status_value = _get(row, "review_status")
        saved_status = _canonical_status(status_value)

        eligible = (
            result["ml_assessed"] is True
            and baseline is not None
            and forest is not None
            and result["decision_label"] in _COMPLETE_DECISIONS
            and saved_status is not None
        )
        if not eligible:
            counts["not_comparable_rows"] += 1
            continue

        counts["comparable_rows"] += 1
        if saved_status == result["decision_label"]:
            counts["matching_rows"] += 1
        else:
            counts["mismatching_rows"] += 1
            date_value = _get(row, "date")
            if isinstance(date_value, pd.Timestamp):
                date_text = date_value.strftime("%Y-%m-%d %H:%M:%S GMT")
            else:
                date_text = "Unavailable" if _is_missing(date_value) else str(date_value)
            mismatches.append({
                "Row index": index,
                "Date/time": date_text,
                "Energy (×10¹⁰ J)": _get(row, "energy"),
                "Saved review status": status_value,
                "Agent-derived status": result["decision_label"],
                "Baseline flag": baseline,
                "ML assessed": result["ml_assessed"],
                "Isolation Forest flag": forest,
            })

    return counts, pd.DataFrame(mismatches)
