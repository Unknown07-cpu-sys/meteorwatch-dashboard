"""Load and normalise the METEORWATCH full-review report."""
from __future__ import annotations

from io import BytesIO
from typing import Any

import numpy as np
import pandas as pd


def load_report(file_bytes: bytes) -> pd.DataFrame:
    """Load and normalize the exported METEORWATCH full-review CSV."""
    df = pd.read_csv(BytesIO(file_bytes))

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

    numeric_cols = [
        "energy", "impact-e", "lat", "lon", "alt", "vel",
        "vx", "vy", "vz", "component_speed", "iforest_score",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    def parse_bool(value: Any) -> Any:
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

    for col in ["baseline_flag", "iforest_flag", "ml_assessed"]:
        if col in df.columns:
            df[col] = df[col].map(parse_bool).astype("boolean")

    # Derive signed coordinates from the original NASA/JPL direction fields.
    # North/East are positive; South/West are negative.
    if {"lat", "lat-dir", "lon", "lon-dir"}.issubset(df.columns):
        lat_dir = df["lat-dir"].astype("string").str.strip().str.upper()
        lon_dir = df["lon-dir"].astype("string").str.strip().str.upper()

        lat_north = lat_dir.eq("N").fillna(False).to_numpy(dtype=bool)
        lat_south = lat_dir.eq("S").fillna(False).to_numpy(dtype=bool)
        lon_east = lon_dir.eq("E").fillna(False).to_numpy(dtype=bool)
        lon_west = lon_dir.eq("W").fillna(False).to_numpy(dtype=bool)

        lat_values = df["lat"].to_numpy(dtype=float)
        lon_values = df["lon"].to_numpy(dtype=float)
        df["map_latitude"] = np.select(
            [lat_north, lat_south],
            [lat_values, -lat_values],
            default=np.nan,
        )
        df["map_longitude"] = np.select(
            [lon_east, lon_west],
            [lon_values, -lon_values],
            default=np.nan,
        )
    elif {"latitude", "longitude"}.issubset(df.columns):
        df["map_latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
        df["map_longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    else:
        df["map_latitude"] = np.nan
        df["map_longitude"] = np.nan

    # Calculate speed from current documented components if available.
    if {"vx", "vy", "vz"}.issubset(df.columns):
        component_columns = ["vx", "vy", "vz"]
        component_valid = df[component_columns].notna().all(axis=1)
        calculated_speed = np.sqrt(
            df["vx"].pow(2) + df["vy"].pow(2) + df["vz"].pow(2)
        )
        # Recompute from components rather than trusting a potentially stale
        # derived scalar field. Keep missing values missing.
        df["component_speed"] = calculated_speed.where(component_valid)

    # Keep map coordinates only if they are geographically valid.
    valid_coords = (
        df["map_latitude"].between(-90, 90)
        & df["map_longitude"].between(-180, 180)
    )
    df.loc[~valid_coords, ["map_latitude", "map_longitude"]] = np.nan

    return df


def safe_int(series: pd.Series | None) -> int:
    if series is None:
        return 0
    return int(series.eq(True).sum())
