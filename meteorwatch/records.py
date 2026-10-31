"""Record-table helpers: ordering, labels and the readable table. Pure pandas, no Streamlit."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from meteorwatch.ui.design import fmt_amount, fmt_stamp

SORT_OPTIONS = [
    "Newest first",
    "Oldest first",
    "Highest energy",
    "Lowest energy",
    "Flagged records first",
    "Most unusual ML score",
]

SEARCH_COLUMNS = [
    "date", "energy", "impact-e", "alt", "component_speed", "review_status",
    "explanation", "lat", "lat-dir", "lon", "lon-dir", "map_latitude", "map_longitude",
]


def py_scalar(value: Any) -> Any:
    """Plain Python ints for index labels, so dict lookups and widget state stay predictable."""
    return int(value) if isinstance(value, np.integer) else value


def sort_events(candidates: pd.DataFrame, sort_choice: str) -> pd.DataFrame:
    """Order records for review. This is a workflow order, not a physical-risk ranking."""
    if sort_choice == "Newest first":
        return candidates.sort_values("date", ascending=False, na_position="last")
    if sort_choice == "Oldest first":
        return candidates.sort_values("date", ascending=True, na_position="last")
    if sort_choice == "Highest energy":
        return candidates.sort_values("energy", ascending=False, na_position="last")
    if sort_choice == "Lowest energy":
        return candidates.sort_values("energy", ascending=True, na_position="last")
    if sort_choice == "Most unusual ML score":
        # More negative Isolation Forest decision scores are more unusual under this
        # fitted model. Missing ML scores stay at the end.
        if "iforest_score" in candidates.columns:
            return candidates.sort_values("iforest_score", ascending=True, na_position="last")
        return candidates.sort_values("date", ascending=False, na_position="last")
    if sort_choice == "Flagged records first":
        baseline = candidates.get("baseline_flag", pd.Series(False, index=candidates.index)).eq(True).fillna(False)
        ml = candidates.get("iforest_flag", pd.Series(False, index=candidates.index)).eq(True).fillna(False)
        return (
            candidates.assign(_picker_any_flag=(baseline | ml))
            .sort_values(["_picker_any_flag", "date"], ascending=[False, False], na_position="last")
            .drop(columns="_picker_any_flag")
        )
    return candidates


def event_labels(rows: pd.DataFrame) -> dict[Any, str]:
    labels: dict[Any, str] = {}
    for idx, ts, energy, status in zip(rows.index, rows["date"], rows["energy"], rows["review_status"]):
        energy_text = fmt_amount(energy) or "not reported"
        labels[py_scalar(idx)] = f"{fmt_stamp(ts)}, energy {energy_text}, {status}"
    return labels


def selected_rows(event: Any) -> list[int]:
    """Row positions from st.dataframe(on_select=...), whatever container type it returns."""
    selection = getattr(event, "selection", None)
    if selection is None and isinstance(event, dict):
        selection = event.get("selection")
    rows = getattr(selection, "rows", None)
    if rows is None and isinstance(selection, dict):
        rows = selection.get("rows")
    return [int(r) for r in (rows or [])]


def _numeric(base: pd.DataFrame, name: str) -> pd.Series:
    if name in base.columns:
        return base[name]
    return pd.Series(np.nan, index=base.index, dtype="float64")


def records_table(view: pd.DataFrame) -> pd.DataFrame:
    """A readable table. 'Not assessed' stays its own word instead of looking like 'No flag'."""
    base = view.reset_index(drop=True)

    def state(name: str, value: bool) -> np.ndarray:
        if name not in base.columns:
            return np.zeros(len(base), dtype=bool)
        return base[name].eq(value).fillna(False).to_numpy(dtype=bool)

    baseline = np.select(
        [state("baseline_flag", True), state("baseline_flag", False)],
        ["Flagged", "No flag"],
        default="No saved result",
    )
    assessed, not_assessed = state("ml_assessed", True), state("ml_assessed", False)
    forest = np.select(
        [
            not_assessed,
            assessed & state("iforest_flag", True),
            assessed & state("iforest_flag", False),
            assessed,
        ],
        ["Not assessed", "Flagged", "No flag", "No saved flag"],
        default="Status unknown",
    )
    return pd.DataFrame(
        {
            "Date (GMT)": base["date"],
            "Review status": base["review_status"].astype(str),
            "Energy (×10¹⁰ J)": _numeric(base, "energy"),
            "Impact energy (kt)": _numeric(base, "impact-e"),
            "Altitude (km)": _numeric(base, "alt"),
            "Speed (km/s)": _numeric(base, "component_speed"),
            "IQR baseline": baseline,
            "Isolation Forest": forest,
            "ML score": _numeric(base, "iforest_score"),
        }
    )
