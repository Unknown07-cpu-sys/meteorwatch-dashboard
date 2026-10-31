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
    missing_sentinel = object()
    raw_assessment = _get(row, "ml_assessed", missing_sentinel)
    explicit_field_present = raw_assessment is not missing_sentinel
    explicit_assessed = parse_saved_bool(raw_assessment) if explicit_field_present else None

    # A legacy report with no ml_assessed field at all may use the forest flag as
    # a weak coverage proxy. If the field exists but is blank/unknown, preserve
    # that uncertainty instead of inferring assessment from the flag.
    if not explicit_field_present:
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
    elif ml_assessed is None and forest_flag is not None:
        reasons.append(
            "**Isolation Forest:** a flag value is saved, but the assessment status is unknown. Do not infer model coverage from this incomplete combination."
        )
    else:
        reasons.append(
            "**Isolation Forest:** the saved result does not establish whether this record was flagged."
        )

    if ml_assessed is False and forest_flag is not None:
        reasons.append(
            "**Consistency note:** the report contains an Isolation Forest flag value even though `ml_assessed` is false. Check the exported report and model pipeline."
        )
    elif ml_assessed is None and forest_flag is not None:
        reasons.append(
            "**Coverage note:** an Isolation Forest flag is stored, but `ml_assessed` is missing or unrecognised. Confirm the source pipeline before counting this row as assessed."
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



def build_structured_review_export(df: pd.DataFrame) -> pd.DataFrame:
    """Build a human-friendly, one-event-per-row review CSV table.

    This is a curated view for faculty/demo review. The source/technical export
    remains available separately so no original data columns are lost.
    """
    field_labels = {
        "date": "event date/time",
        "energy": "reported radiated energy",
        "impact-e": "estimated impact energy",
        "alt": "altitude at peak brightness",
        "vel": "reported scalar velocity",
        "vx": "velocity component vx",
        "vy": "velocity component vy",
        "vz": "velocity component vz",
        "map_latitude": "peak-brightness latitude",
        "map_longitude": "peak-brightness longitude",
    }
    available_source_fields = [key for key in field_labels if key in df.columns]

    def flag_label(value: Any) -> str:
        parsed = parse_saved_bool(value)
        if parsed is None:
            return "Unknown"
        return "Yes" if parsed else "No"

    def clean_timestamp(value: Any) -> str:
        if _is_missing(value):
            return ""
        try:
            timestamp = pd.to_datetime(value, errors="coerce")
        except (TypeError, ValueError):
            return str(value)
        if pd.isna(timestamp):
            return ""
        return timestamp.strftime("%Y-%m-%d %H:%M:%S")

    def clean_number(value: Any) -> Any:
        if _is_missing(value):
            return None
        try:
            number = float(value)
        except (TypeError, ValueError, OverflowError):
            return str(value)
        if not math.isfinite(number):
            return None
        return number

    records: list[dict[str, Any]] = []
    for fallback_number, (source_index, row) in enumerate(df.iterrows(), start=1):
        if isinstance(source_index, (int, np.integer)) and int(source_index) >= 0:
            source_number = int(source_index) + 1
        else:
            source_number = fallback_number

        assessment = assess_event(row)
        decision = assessment["decision_label"]
        baseline_flag = assessment["baseline_flag"]
        forest_flag = assessment["iforest_flag"]
        ml_assessed = assessment["ml_assessed"]

        if decision == "Flagged by both methods":
            queue_group, queue_rank = "Both methods flagged", 1
            next_step = "Review this record first; both detection methods flagged it. This is not proof of danger."
        elif forest_flag is True and baseline_flag is not True:
            queue_group, queue_rank = "Isolation Forest flag", 2
            next_step = "Review the Isolation Forest flag and compare the available measurements."
        elif baseline_flag is True and ml_assessed is True and forest_flag is False:
            queue_group, queue_rank = "IQR baseline flag", 3
            next_step = "Review the energy-based IQR flag and compare it with the model result."
        elif baseline_flag is True and ml_assessed is not True:
            queue_group, queue_rank = "Baseline flag; ML unavailable", 4
            next_step = "Review the baseline flag; the model did not assess this record or its status is unknown."
        elif decision == "Neither method flagged":
            queue_group, queue_rank = "Neither method flagged", 6
            next_step = "No saved detector flag is present; this is not a safety clearance."
        elif ml_assessed is False or decision == "Detection status incomplete":
            queue_group, queue_rank = "Coverage / status check", 5
            next_step = "Check data completeness and saved detection fields before interpreting this record."
        else:
            queue_group, queue_rank = "Coverage / status check", 5
            next_step = "Check incomplete or inconsistent detection fields before interpreting this record."

        missing_fields = [
            field_labels[key]
            for key in available_source_fields
            if _is_missing(_get(row, key))
        ]
        # Keep the saved ML inputs separate from general record completeness.
        missing_ml_fields = list(assessment["missing_ml_fields"])

        if baseline_flag is True:
            baseline_reason = "The saved IQR energy-only rule flagged this record for review."
        elif baseline_flag is False:
            baseline_reason = "The saved IQR rule did not flag this record; this is not a safety clearance."
        else:
            baseline_reason = "No usable saved IQR baseline flag is available."

        if ml_assessed is False:
            forest_reason = "The Isolation Forest did not assess this record; do not interpret this as a negative result."
        elif ml_assessed is True and forest_flag is True:
            forest_reason = "The saved Isolation Forest result flagged this record for review."
        elif ml_assessed is True and forest_flag is False:
            forest_reason = "The saved Isolation Forest result did not flag this record; this does not prove the event is normal or safe."
        else:
            forest_reason = "The saved Isolation Forest result is unavailable or its assessment status is unknown."

        warnings = list(assessment["warnings"])
        if ("map_latitude" in df.columns and "map_longitude" in df.columns
                and (_is_missing(_get(row, "map_latitude")) or _is_missing(_get(row, "map_longitude")))):
            warnings.append("Peak-brightness map coordinates are unavailable or invalid.")

        date_value = _get(row, "date")
        date_export = clean_timestamp(date_value)
        energy_value = clean_number(_get(row, "energy"))
        impact_value = clean_number(_get(row, "impact-e"))
        altitude_value = clean_number(_get(row, "alt"))
        velocity_value = clean_number(_get(row, "vel"))
        speed_value = clean_number(_get(row, "component_speed"))
        if speed_value is None:
            vx, vy, vz = (_get(row, key) for key in ("vx", "vy", "vz"))
            if all(not _is_missing(value) for value in (vx, vy, vz)):
                try:
                    speed_value = math.sqrt(float(vx) ** 2 + float(vy) ** 2 + float(vz) ** 2)
                except (TypeError, ValueError, OverflowError):
                    speed_value = None

        score = clean_number(_get(row, "iforest_score"))
        if ml_assessed is False:
            score_note = "ML marked not assessed; any saved score should be checked for consistency."
        elif score is None:
            score_note = "Unavailable"
        else:
            score_note = "More negative scores are ranked as more unusual by this fitted model; not a danger score."

        if ml_assessed is False:
            forest_flag_display = "Not assessed"
        else:
            forest_flag_display = flag_label(_get(row, "iforest_flag"))

        records.append({
            "Source record number": source_number,
            "METEORWATCH record ID": f"MW-{source_number:04d}",
            "Event date/time (GMT)": date_export,
            "Saved review status": "" if _is_missing(_get(row, "review_status")) else str(_get(row, "review_status")),
            "Agent interpretation from saved flags": decision,
            "Review queue group": queue_group,
            "IQR baseline flagged": flag_label(_get(row, "baseline_flag")),
            "Isolation Forest assessed": flag_label(_get(row, "ml_assessed")),
            "Isolation Forest flagged": forest_flag_display,
            "Isolation Forest score": score,
            "Score interpretation": score_note,
            "Reported radiated energy (×10¹⁰ J)": energy_value,
            "Estimated impact energy (kt)": impact_value,
            "Altitude at peak brightness (km)": altitude_value,
            "Reported scalar velocity (km/s)": velocity_value,
            "Speed calculated from vx/vy/vz (km/s)": speed_value,
            "Peak-brightness latitude (degrees)": clean_number(_get(row, "map_latitude")),
            "Peak-brightness longitude (degrees)": clean_number(_get(row, "map_longitude")),
            "Missing measurements or fields": "; ".join(missing_fields),
            "Missing Isolation Forest inputs": "; ".join(missing_ml_fields),
            "Data-quality notes": "; ".join(dict.fromkeys(warnings)),
            "IQR baseline explanation": baseline_reason,
            "Isolation Forest explanation": forest_reason,
            "Suggested review action": next_step,
            "Interpretation boundary": "Historical statistical review only; flags are not confirmed anomalies or danger ratings, and METEORWATCH does not predict future impacts.",
            "Original saved explanation": "" if _is_missing(_get(row, "explanation")) else str(_get(row, "explanation")),
            "_queue_rank": queue_rank,
        })

    columns = [
        "Source record number",
        "METEORWATCH record ID",
        "Event date/time (GMT)",
        "Saved review status",
        "Agent interpretation from saved flags",
        "Review queue group",
        "IQR baseline flagged",
        "Isolation Forest assessed",
        "Isolation Forest flagged",
        "Isolation Forest score",
        "Score interpretation",
        "Reported radiated energy (×10¹⁰ J)",
        "Estimated impact energy (kt)",
        "Altitude at peak brightness (km)",
        "Reported scalar velocity (km/s)",
        "Speed calculated from vx/vy/vz (km/s)",
        "Peak-brightness latitude (degrees)",
        "Peak-brightness longitude (degrees)",
        "Missing measurements or fields",
        "Missing Isolation Forest inputs",
        "Data-quality notes",
        "IQR baseline explanation",
        "Isolation Forest explanation",
        "Suggested review action",
        "Interpretation boundary",
        "Original saved explanation",
        "_queue_rank",
    ]
    result = pd.DataFrame(records, columns=columns)
    if not result.empty:
        result = result.sort_values(
            ["_queue_rank", "Reported radiated energy (×10¹⁰ J)", "Event date/time (GMT)"],
            ascending=[True, False, False],
            na_position="last",
            kind="stable",
        )
    result = result.drop(columns=["_queue_rank"], errors="ignore").reset_index(drop=True)
    return result

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
