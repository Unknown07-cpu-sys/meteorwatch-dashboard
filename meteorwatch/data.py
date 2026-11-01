"""Load and normalise the METEORWATCH full-review report.

For input problems, either load honest missing values or refuse with a clear
message. Never drop a record silently or turn a missing value into a number.
"""
from __future__ import annotations

import csv
from io import StringIO
from typing import Any

import numpy as np
import pandas as pd

REQUIRED_COLUMNS = ("date", "energy", "review_status")
STATUS_MISSING_LABEL = "Status unavailable"

KNOWN_COLUMNS = (
    "date", "energy", "impact-e", "lat", "lat-dir", "lon", "lon-dir", "alt", "vel",
    "vx", "vy", "vz", "component_speed", "baseline_flag", "iforest_flag", "ml_assessed",
    "iforest_score", "review_status", "explanation", "latitude", "longitude",
)
_NUMERIC_COLUMNS = (
    "energy", "impact-e", "lat", "lon", "alt", "vel",
    "vx", "vy", "vz", "component_speed", "iforest_score", "latitude", "longitude",
)
_BOOLEAN_COLUMNS = ("baseline_flag", "iforest_flag", "ml_assessed")


class ReportLoadError(ValueError):
    """The report cannot be used, and the message says what to fix."""


def _decode(file_bytes: bytes) -> str:
    if b"\x00" in file_bytes[:4096]:
        raise ReportLoadError("This looks like a binary file, not a CSV. Upload the report as a plain-text .csv file.")
    try:
        return file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        return file_bytes.decode("cp1252", errors="replace")


def _detect_separator(text: str) -> str:
    first_line = next((line for line in text.splitlines() if line.strip()), "")
    if "," not in first_line:
        for candidate in (";", "\t"):
            if candidate in first_line:
                return candidate
    return ","


def _canonical_names(raw_names: list[str]) -> list[str]:
    known = {name.lower(): name for name in KNOWN_COLUMNS}
    cleaned = [str(name).strip() for name in raw_names]
    return [known.get(name.lower(), name) for name in cleaned]


def _parse_bool(value: Any) -> Any:
    if pd.isna(value):
        return pd.NA
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    return pd.NA


def load_report(file_bytes: bytes) -> pd.DataFrame:
    """Load and normalise a METEORWATCH full-review CSV."""
    text = _decode(file_bytes)
    if not text.strip():
        raise ReportLoadError("The file is empty. Upload the METEORWATCH full-review report (.csv).")

    separator = _detect_separator(text)
    header_line = next(line for line in text.splitlines() if line.strip())
    header_names = _canonical_names(next(csv.reader([header_line], delimiter=separator)))
    repeated = sorted({name for name in header_names if header_names.count(name) > 1})
    if repeated:
        raise ReportLoadError(
            f"These column headings appear more than once: {', '.join(repeated)}. "
            "Remove the duplicates and try again."
        )

    try:
        df = pd.read_csv(StringIO(text), sep=separator)
    except pd.errors.EmptyDataError as exc:
        raise ReportLoadError("The file is empty. Upload the METEORWATCH full-review report (.csv).") from exc
    except (pd.errors.ParserError, ValueError) as exc:
        raise ReportLoadError(f"This file could not be read as a CSV. {exc}") from exc

    df.columns = _canonical_names(list(df.columns))
    missing = [name for name in REQUIRED_COLUMNS if name not in df.columns]
    if missing:
        raise ReportLoadError(
            "This does not look like a METEORWATCH report. "
            f"Missing required columns: {', '.join(missing)}. "
            f"Columns found: {', '.join(map(str, df.columns))}."
        )
    if df.empty:
        raise ReportLoadError("The report has column headings but no rows.")

    df["date"] = pd.to_datetime(
        df["date"], errors="coerce", utc=True, format="mixed"
    ).dt.tz_localize(None)

    for col in _NUMERIC_COLUMNS:
        if col in df.columns:
            numbers = pd.to_numeric(df[col], errors="coerce")
            df[col] = numbers.replace([np.inf, -np.inf], np.nan)

    for col in _BOOLEAN_COLUMNS:
        if col in df.columns:
            df[col] = df[col].map(_parse_bool).astype("boolean")

    status = df["review_status"].astype("string").str.strip().fillna("")
    df["review_status"] = status.where(status != "", STATUS_MISSING_LABEL).astype(str)

    if {"lat", "lat-dir", "lon", "lon-dir"}.issubset(df.columns):
        lat_dir = df["lat-dir"].astype("string").str.strip().str.upper()
        lon_dir = df["lon-dir"].astype("string").str.strip().str.upper()
        lat_north = lat_dir.eq("N").fillna(False).to_numpy(dtype=bool)
        lat_south = lat_dir.eq("S").fillna(False).to_numpy(dtype=bool)
        lon_east = lon_dir.eq("E").fillna(False).to_numpy(dtype=bool)
        lon_west = lon_dir.eq("W").fillna(False).to_numpy(dtype=bool)
        lat_values = df["lat"].to_numpy(dtype=float)
        lon_values = df["lon"].to_numpy(dtype=float)
        df["map_latitude"] = np.select([lat_north, lat_south], [lat_values, -lat_values], default=np.nan)
        df["map_longitude"] = np.select([lon_east, lon_west], [lon_values, -lon_values], default=np.nan)
    elif {"latitude", "longitude"}.issubset(df.columns):
        df["map_latitude"] = df["latitude"]
        df["map_longitude"] = df["longitude"]
    else:
        df["map_latitude"] = np.nan
        df["map_longitude"] = np.nan

    if {"vx", "vy", "vz"}.issubset(df.columns):
        component_valid = df[["vx", "vy", "vz"]].notna().all(axis=1)
        calculated_speed = np.sqrt(df["vx"].pow(2) + df["vy"].pow(2) + df["vz"].pow(2))
        df["component_speed"] = calculated_speed.where(component_valid)

    valid_coords = df["map_latitude"].between(-90, 90) & df["map_longitude"].between(-180, 180)
    df.loc[~valid_coords, ["map_latitude", "map_longitude"]] = np.nan
    return df
