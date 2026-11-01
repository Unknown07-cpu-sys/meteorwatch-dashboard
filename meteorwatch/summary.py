"""Catalogue-level counts shared by the dashboard and export tests.

A flag counts only when explicitly True. Missing is not False, and "not
assessed" is not "not flagged".
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import pandas as pd


def _true_count(frame: pd.DataFrame, column: str) -> int:
    if column not in frame.columns:
        return 0
    return int(frame[column].eq(True).sum())


def _false_count(frame: pd.DataFrame, column: str) -> int:
    if column not in frame.columns:
        return 0
    return int(frame[column].eq(False).sum())


@dataclass(frozen=True)
class CatalogueSummary:
    records: int
    first_date: pd.Timestamp | None
    last_date: pd.Timestamp | None
    years: int
    ml_assessed: int
    ml_not_assessed: int
    ml_unknown: int
    baseline_flags: int
    forest_flags: int
    flagged_both: int
    flagged_any: int
    with_location: int


def summarise(frame: pd.DataFrame) -> CatalogueSummary:
    dates = frame["date"].dropna() if "date" in frame.columns else pd.Series(dtype="datetime64[ns]")
    first = dates.min() if not dates.empty else None
    last = dates.max() if not dates.empty else None
    baseline = frame["baseline_flag"].eq(True) if "baseline_flag" in frame.columns else pd.Series(False, index=frame.index)
    forest = frame["iforest_flag"].eq(True) if "iforest_flag" in frame.columns else pd.Series(False, index=frame.index)
    unknown = int(frame["ml_assessed"].isna().sum()) if "ml_assessed" in frame.columns else len(frame)
    located = (
        int(frame[["map_latitude", "map_longitude"]].notna().all(axis=1).sum())
        if {"map_latitude", "map_longitude"}.issubset(frame.columns)
        else 0
    )
    return CatalogueSummary(
        records=len(frame),
        first_date=first,
        last_date=last,
        years=int(last.year - first.year) if first is not None and last is not None else 0,
        ml_assessed=_true_count(frame, "ml_assessed"),
        ml_not_assessed=_false_count(frame, "ml_assessed"),
        ml_unknown=unknown,
        baseline_flags=int(baseline.sum()),
        forest_flags=int(forest.sum()),
        flagged_both=int((baseline & forest).sum()),
        flagged_any=int((baseline | forest).sum()),
        with_location=located,
    )


def count_by_status(frame: pd.DataFrame, statuses: Sequence[str]) -> list[tuple[str, int]]:
    """Return record counts in the requested status order, including zeroes."""
    counts = (
        frame["review_status"].astype(str).value_counts()
        if "review_status" in frame.columns
        else pd.Series(dtype=int)
    )
    return [(status, int(counts.get(status, 0))) for status in statuses]
