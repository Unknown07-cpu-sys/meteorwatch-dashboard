from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st


APP_TITLE = "METEORWATCH"
DATA_FILENAME = "meteorwatch_full_review_report.csv"
NASA_API_DOCS = "https://ssd-api.jpl.nasa.gov/doc/fireball.html"
NASA_FIREBALLS = "https://cneos.jpl.nasa.gov/fireballs/"

st.set_page_config(
    page_title=f"{APP_TITLE} | Historical Fireball Intelligence",
    page_icon="🌠",
    layout="wide",
)


@st.cache_data(show_spinner=False)
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


def format_value(value: Any, digits: int = 3) -> str:
    if value is None or pd.isna(value):
        return "Unavailable in this record"
    if isinstance(value, (float, np.floating, int, np.integer)):
        return f"{float(value):,.{digits}f}"
    return str(value)


def event_briefing(row: pd.Series) -> str:
    """Create a transparent, rule-generated summary from fields and flags."""
    date_text = (
        row["date"].strftime("%Y-%m-%d %H:%M:%S GMT")
        if pd.notna(row.get("date")) else "Date unavailable"
    )
    status = str(row.get("review_status", "Status unavailable"))
    energy = row.get("energy", np.nan)
    impact_energy = row.get("impact-e", np.nan)
    altitude = row.get("alt", np.nan)
    speed = row.get("component_speed", np.nan)

    paragraphs = [
        f"**Historical event:** {date_text}.",
        (
            "**Reported measurements:** total radiated energy = "
            f"{format_value(energy)} × 10¹⁰ joules; estimated impact energy = "
            f"{format_value(impact_energy)} kt; peak-brightness altitude = "
            f"{format_value(altitude)} km; speed magnitude calculated from the "
            f"entry-velocity components = {format_value(speed)} km/s."
        ),
    ]

    if status == "Flagged by both methods":
        paragraphs.append(
            "**Why it appears for review:** both the energy-only IQR baseline "
            "and Isolation Forest flagged this record under the current settings."
        )
    elif status == "Isolation Forest only":
        paragraphs.append(
            "**Why it appears for review:** Isolation Forest flagged this record "
            "using the combination of log-energy, altitude, and component-derived "
            "speed; the energy-only IQR baseline did not flag it."
        )
    elif status == "IQR baseline only":
        paragraphs.append(
            "**Why it appears for review:** the energy-only IQR baseline flagged "
            "the reported energy, while Isolation Forest did not flag this record "
            "under the current model settings."
        )
    elif status == "Baseline flagged; ML not assessed":
        paragraphs.append(
            "**Why it appears for review:** the energy-only IQR baseline flagged "
            "the record, but the ML model could not assess it because at least "
            "one required feature was missing."
        )
    elif status == "ML not assessed; baseline did not flag":
        paragraphs.append(
            "**Assessment status:** the baseline did not flag this record, but "
            "the ML model could not assess it because at least one required "
            "feature was missing. This is not an ML clearance."
        )
    else:
        paragraphs.append(
            "**Assessment status:** neither method flagged this record under "
            "the current settings. That does not prove the event is normal, safe, "
            "or fully characterized."
        )

    missing = []
    for col, label in [
        ("alt", "altitude"),
        ("component_speed", "velocity components / calculated speed"),
        ("map_latitude", "location coordinates"),
    ]:
        value = row.get(col, np.nan)
        if value is None or pd.isna(value):
            missing.append(label)
    if missing:
        paragraphs.append(
            "**Data gaps:** unavailable measurements: " + ", ".join(missing) + "."
        )

    paragraphs.append(
        "**Caution:** this is a rule-generated briefing based on the saved dataset. "
        "A statistical flag is a prompt for human review, not a danger rating or "
        "prediction of a future impact."
    )
    return "\n\n".join(paragraphs)


st.title("🌠 METEORWATCH")
st.subheader("Historical Fireball Intelligence")
st.caption(
    "An explainable research prototype for examining historical fireball records. "
    "It does not predict future impacts or issue operational warnings."
)

st.info(
    "**Interpretation rule:** an anomaly flag means ‘review this record’, not "
    "‘dangerous’. ‘ML not assessed’ is different from ‘not flagged by ML’."
)

uploaded_file = st.sidebar.file_uploader(
    "Upload the full historical report CSV",
    type=["csv"],
    help="Use meteorwatch_full_review_report.csv from your analysis workflow.",
)
default_file = Path(DATA_FILENAME)

try:
    if uploaded_file is not None:
        df = load_report(uploaded_file.getvalue())
        source_label = "Uploaded CSV"
    elif default_file.exists():
        df = load_report(default_file.read_bytes())
        source_label = DATA_FILENAME
    else:
        st.warning(
            "The full report CSV is not beside app.py. Upload "
            "meteorwatch_full_review_report.csv using the sidebar."
        )
        st.stop()
except Exception as exc:
    st.error(f"Could not load the report: {exc}")
    st.stop()

required = {"date", "energy", "review_status"}
if not required.issubset(df.columns):
    st.error(
        "This CSV does not look like the METEORWATCH full-review report. "
        f"Required columns: {', '.join(sorted(required))}."
    )
    st.stop()

if "baseline_flag" not in df.columns:
    df["baseline_flag"] = pd.Series(pd.NA, index=df.index, dtype="boolean")
if "iforest_flag" not in df.columns:
    df["iforest_flag"] = pd.Series(pd.NA, index=df.index, dtype="boolean")
if "ml_assessed" not in df.columns:
    df["ml_assessed"] = df["iforest_flag"].notna().astype("boolean")
if "explanation" not in df.columns:
    df["explanation"] = "No saved explanation is available for this row."

# Dashboard metrics are derived from loaded data.
total_records = len(df)
ml_assessed_count = safe_int(df["ml_assessed"])
ml_not_assessed_count = total_records - ml_assessed_count
baseline_count = safe_int(df["baseline_flag"])
ml_flag_count = safe_int(df["iforest_flag"])
coordinate_count = int(df[["map_latitude", "map_longitude"]].notna().all(axis=1).sum())

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Historical records", f"{total_records:,}")
m2.metric("IQR baseline flags", f"{baseline_count:,}")
m3.metric("Isolation Forest flags", f"{ml_flag_count:,}")
m4.metric("ML not assessed", f"{ml_not_assessed_count:,}")
m5.metric("Mapped records", f"{coordinate_count:,}")

st.caption(f"Data source file: `{source_label}` · Source fields are from NASA/JPL's historical Fireball Data API.")

# Shared sidebar filters.
st.sidebar.divider()
st.sidebar.header("Filter historical events")
status_values = sorted(df["review_status"].dropna().astype(str).unique().tolist())
selected_statuses = st.sidebar.multiselect(
    "Review status",
    options=status_values,
    default=status_values,
)
min_date = df["date"].min()
max_date = df["date"].max()
if pd.notna(min_date) and pd.notna(max_date):
    date_range = st.sidebar.date_input(
        "Event date range (GMT)",
        value=(min_date.date(), max_date.date()),
        min_value=min_date.date(),
        max_value=max_date.date(),
    )
else:
    date_range = None

minimum_energy = float(max(0.0, df["energy"].min(skipna=True)))
maximum_energy = float(df["energy"].max(skipna=True))
if np.isfinite(maximum_energy) and maximum_energy >= minimum_energy:
    energy_floor = st.sidebar.number_input(
        "Minimum reported energy (×10¹⁰ joules)",
        min_value=minimum_energy,
        max_value=maximum_energy,
        value=minimum_energy,
    )
else:
    energy_floor = 0.0

search_text = st.sidebar.text_input("Search date or explanation")

filtered = df.copy()
filtered = filtered[filtered["review_status"].astype(str).isin(selected_statuses)]
filtered = filtered[filtered["energy"].notna() & (filtered["energy"] >= energy_floor)]
if date_range and isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    start_date, end_date = date_range
    filtered = filtered[
        filtered["date"].notna()
        & (filtered["date"].dt.date >= start_date)
        & (filtered["date"].dt.date <= end_date)
    ]
if search_text.strip():
    term = search_text.strip()
    search_mask = filtered["date"].astype(str).str.contains(term, case=False, na=False)
    search_mask |= filtered["explanation"].astype(str).str.contains(term, case=False, na=False)
    filtered = filtered[search_mask]

# Tabs give the app a cleaner mission-control-style structure.
tab_overview, tab_map, tab_explorer, tab_methods = st.tabs(
    ["Overview", "Event Map", "Event Explorer", "Methods & Limitations"]
)

with tab_overview:
    left, right = st.columns(2)
    with left:
        st.markdown("#### Review status distribution")
        counts = (
            df["review_status"].value_counts(dropna=False)
            .rename_axis("Review status")
            .reset_index(name="Records")
        )
        fig_status = px.bar(
            counts,
            x="Review status",
            y="Records",
            color="Review status",
            title="All records by review status",
        )
        fig_status.update_layout(
            showlegend=False,
            xaxis_tickangle=-30,
            margin=dict(l=10, r=10, t=55, b=100),
        )
        st.plotly_chart(fig_status, use_container_width=True)

    with right:
        st.markdown("#### Reported energy distribution")
        energy_rows = df[df["energy"].notna() & (df["energy"] > 0)]
        fig_energy = px.histogram(
            energy_rows,
            x="energy",
            nbins=35,
            log_x=True,
            title="Energy distribution (logarithmic x-axis)",
            labels={"energy": "Reported energy (×10¹⁰ joules)"},
        )
        fig_energy.update_layout(margin=dict(l=10, r=10, t=55, b=35))
        st.plotly_chart(fig_energy, use_container_width=True)

    st.markdown("#### Current filtered view")
    st.write(f"Showing **{len(filtered):,}** of **{total_records:,}** records after sidebar filters.")
    preview_columns = [
        col for col in [
            "date", "energy", "impact-e", "alt", "component_speed",
            "ml_assessed", "baseline_flag", "iforest_flag", "review_status",
        ] if col in filtered.columns
    ]
    st.dataframe(filtered[preview_columns], use_container_width=True, hide_index=True)

with tab_map:
    st.markdown("#### Reported event locations")
    st.caption(
        "Only records with reported coordinates are shown. North and East are positive; "
        "South and West are negative. These are locations at peak brightness, not impact sites."
    )
    map_rows = filtered.dropna(subset=["map_latitude", "map_longitude"]).copy()
    if map_rows.empty:
        st.info("No records with valid reported coordinates match the current filters.")
    else:
        map_hover = [
            col for col in ["energy", "impact-e", "alt", "component_speed", "review_status"]
            if col in map_rows.columns
        ]
        map_rows["event_time_gmt"] = map_rows["date"].dt.strftime("%Y-%m-%d %H:%M:%S GMT")
        fig_map = px.scatter_geo(
            map_rows,
            lat="map_latitude",
            lon="map_longitude",
            color="review_status",
            hover_name="event_time_gmt",
            hover_data=map_hover,
            projection="natural earth",
            title=f"{len(map_rows):,} mapped records in current view",
        )
        fig_map.update_traces(marker=dict(size=7, opacity=0.8))
        fig_map.update_layout(height=550, margin=dict(l=0, r=0, t=55, b=0))
        st.plotly_chart(fig_map, use_container_width=True)
        st.caption(
            "A plotted point shows the reported peak-brightness location where known. "
            "Missing locations are omitted rather than guessed."
        )

with tab_explorer:
    st.markdown("#### Find and inspect a historical record")
    st.write(f"{len(filtered):,} records match the current filters.")
    table_columns = [
        col for col in [
            "date", "energy", "impact-e", "alt", "component_speed",
            "ml_assessed", "baseline_flag", "iforest_flag", "review_status",
        ] if col in filtered.columns
    ]
    st.dataframe(filtered[table_columns], use_container_width=True, hide_index=True)
    st.download_button(
        "Download current filtered records (CSV)",
        data=filtered.drop(columns=["map_latitude", "map_longitude"], errors="ignore").to_csv(index=False).encode("utf-8"),
        file_name="meteorwatch_filtered_report.csv",
        mime="text/csv",
    )

    if not filtered.empty:
        st.markdown("#### Selected event briefing")
        indexed = filtered.copy()
        indexed["_row_id"] = indexed.index
        row_ids = indexed["_row_id"].tolist()

        def event_label(idx: int) -> str:
            row = indexed.loc[indexed["_row_id"] == idx].iloc[0]
            date_text = row["date"].strftime("%Y-%m-%d %H:%M:%S GMT") if pd.notna(row["date"]) else "Date unavailable"
            return f"{date_text} · Energy {row['energy']:g} · {row['review_status']}"

        chosen_id = st.selectbox("Choose an event", row_ids, format_func=event_label)
        chosen = indexed.loc[indexed["_row_id"] == chosen_id].iloc[0]
        brief_left, brief_right = st.columns(2)
        with brief_left:
            st.markdown("**Event measurements**")
            st.write(f"Date/time: {chosen['date'] if pd.notna(chosen['date']) else 'Unavailable'} GMT")
            st.write(f"Reported total radiated energy: {format_value(chosen.get('energy'))} × 10¹⁰ J")
            st.write(f"Estimated impact energy: {format_value(chosen.get('impact-e'))} kt")
            st.write(f"Altitude at peak brightness: {format_value(chosen.get('alt'))} km")
            st.write(f"Speed magnitude from entry components: {format_value(chosen.get('component_speed'))} km/s")
            if pd.notna(chosen.get("map_latitude")) and pd.notna(chosen.get("map_longitude")):
                st.write(f"Reported peak-brightness coordinates: {chosen['map_latitude']:.3f}, {chosen['map_longitude']:.3f}")
            else:
                st.write("Reported peak-brightness coordinates: unavailable")
        with brief_right:
            st.markdown("**Detection results**")
            st.write(f"Review status: {chosen.get('review_status', 'Unavailable')}")
            st.write(f"Baseline flagged: {chosen.get('baseline_flag', 'Unavailable')}")
            st.write(f"ML assessed: {chosen.get('ml_assessed', 'Unavailable')}")
            st.write(f"Isolation Forest flag: {chosen.get('iforest_flag', 'Unavailable')}")
            st.write(f"Isolation Forest score: {format_value(chosen.get('iforest_score'))}")

        st.markdown("**Rule-generated event briefing**")
        st.markdown(event_briefing(chosen))
        st.caption(
            "This briefing is generated from fixed rules and the record's fields; "
            "it is not a generative-AI conclusion or a validated physical explanation."
        )
    else:
        st.info("No records match the current filters. Change the sidebar filters to inspect events.")

with tab_methods:
    st.markdown("#### What the system does")
    st.markdown(
        "1. Loads a saved NASA/JPL Fireball Data API response and normalizes field types.\n"
        "2. Uses an IQR rule on log-transformed reported energy as a transparent baseline.\n"
        "3. Uses Isolation Forest on log-energy, altitude, and the magnitude calculated from entry-velocity components, but only where all required values are present.\n"
        "4. Combines the flags into review statuses and creates rule-generated context for a human reviewer."
    )

    st.markdown("#### Data definitions and units")
    st.markdown(
        f"- `date`: time of peak brightness, reported in GMT.\n"
        f"- `energy`: approximate total radiated energy, in units of 10¹⁰ joules.\n"
        f"- `impact-e`: approximate impact energy, in kilotons (kt).\n"
        f"- `alt`: altitude above the Earth geoid at peak brightness, in kilometres.\n"
        f"- `vx`, `vy`, `vz`: entry-velocity components in km/s; this app computes speed magnitude as √(vx² + vy² + vz²).\n"
        f"- Coordinates indicate reported peak-brightness location, not a confirmed ground impact point."
    )
    st.markdown(f"Sources: [NASA/JPL Fireball API documentation]({NASA_API_DOCS}) · [NASA/JPL Fireballs]({NASA_FIREBALLS})")

    st.markdown("#### Limitations that must remain visible")
    st.warning(
        "This is exploratory anomaly detection, not a validated danger classifier. "
        "The dataset is a catalogue of reported detections, not a complete census of every fireball. "
        "Many records lack altitude, velocity components, or location; the model therefore assessed "
        "only a subset. The 5% Isolation Forest contamination value is a model setting, not the true "
        "rate of physical anomalies. There are no independently verified anomaly labels here, so "
        "accuracy, recall, and danger claims cannot be established from these results alone. "
        "An unflagged record is not proof of safety."
    )

    st.markdown("#### Dataset quality snapshot")
    quality_cols = [col for col in ["energy", "impact-e", "alt", "component_speed", "map_latitude", "map_longitude"] if col in df.columns]
    quality = pd.DataFrame({
        "Field": quality_cols,
        "Missing values": [int(df[col].isna().sum()) for col in quality_cols],
        "Missing percent": [round(float(df[col].isna().mean() * 100), 2) for col in quality_cols],
    })
    st.dataframe(quality, hide_index=True, use_container_width=True)

st.divider()
st.caption(
    "METEORWATCH · Student research prototype · Historical analysis only · "
    "No future-impact prediction or operational warning"
)
