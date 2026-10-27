from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st


st.set_page_config(
    page_title="METEORWATCH",
    page_icon="🌠",
    layout="wide"
)


@st.cache_data
def load_data(file_bytes):
    from io import BytesIO
    df = pd.read_csv(BytesIO(file_bytes))

    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    numeric_cols = [
        "energy", "impact-e", "alt",
        "component_speed", "iforest_score"
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Handle True, False and missing boolean values in CSV files.
    def parse_bool(value):
        if pd.isna(value):
            return pd.NA
        if isinstance(value, (bool, np.bool_)):
            return bool(value)

        value = str(value).strip().lower()

        if value in ("true", "1"):
            return True
        if value in ("false", "0"):
            return False
        return pd.NA

    for col in ["baseline_flag", "iforest_flag", "ml_assessed"]:
        if col in df.columns:
            df[col] = df[col].map(parse_bool).astype("boolean")

    return df


st.title("🌠 METEORWATCH")
st.caption("AI-assisted historical fireball event analysis")

st.info(
    "METEORWATCH identifies unusual historical records for review. "
    "A flag is not a danger prediction, and an unflagged record "
    "is not a guarantee of safety."
)

# Load the report saved by the earlier Colab workflow.
uploaded_file = st.sidebar.file_uploader(
    "Upload the full historical report CSV",
    type=["csv"]
)

default_file = Path("meteorwatch_full_review_report.csv")

if uploaded_file is not None:
    df = load_data(uploaded_file.getvalue())
elif default_file.exists():
    df = load_data(default_file.read_bytes())
else:
    st.warning(
        "Upload meteorwatch_full_review_report.csv using the sidebar."
    )
    st.stop()

required_cols = {"date", "energy", "review_status"}
if not required_cols.issubset(df.columns):
    st.error("The uploaded file is missing required report columns.")
    st.stop()

# Sidebar filters
st.sidebar.header("Filter historical events")

statuses = ["All statuses"] + sorted(
    df["review_status"].dropna().unique().tolist()
)

selected_status = st.sidebar.selectbox(
    "Review status",
    statuses
)

search_text = st.sidebar.text_input(
    "Search event date or explanation"
)

min_energy = st.sidebar.number_input(
    "Minimum energy",
    min_value=0.0,
    max_value=float(df["energy"].max()),
    value=0.0
)

filtered = df.copy()

if selected_status != "All statuses":
    filtered = filtered[
        filtered["review_status"] == selected_status
    ]

filtered = filtered[filtered["energy"] >= min_energy]

if search_text.strip():
    search = search_text.strip()
    mask = (
        filtered["date"].astype(str).str.contains(
            search, case=False, na=False
        )
    )

    if "explanation" in filtered.columns:
        mask |= filtered["explanation"].astype(str).str.contains(
            search, case=False, na=False
        )

    filtered = filtered[mask]

# Summary metrics use the full report, not just the filtered view.
total_records = len(df)
ml_assessed = int(df["ml_assessed"].eq(True).sum())
ml_not_assessed = total_records - ml_assessed
baseline_flags = int(df["baseline_flag"].eq(True).sum())
ml_flags = int(df["iforest_flag"].eq(True).sum())

a, b, c, d = st.columns(4)
a.metric("Historical records", f"{total_records:,}")
b.metric("IQR baseline flags", f"{baseline_flags:,}")
c.metric("Isolation Forest flags", f"{ml_flags:,}")
d.metric("ML not assessed", f"{ml_not_assessed:,}")

st.divider()

# Charts
left, right = st.columns(2)

with left:
    st.subheader("Review status distribution")
    counts = (
        df["review_status"]
        .value_counts()
        .rename_axis("Status")
        .reset_index(name="Records")
    )

    fig_status = px.bar(
        counts,
        x="Status",
        y="Records",
        title="Records by review status"
    )
    fig_status.update_layout(xaxis_tickangle=-35)
    st.plotly_chart(fig_status, use_container_width=True)

with right:
    st.subheader("Reported energy distribution")
    energy_data = df[df["energy"] > 0]

    fig_energy = px.histogram(
        energy_data,
        x="energy",
        nbins=35,
        log_x=True,
        title="Energy distribution (logarithmic x-axis)",
        labels={"energy": "Reported energy"}
    )
    st.plotly_chart(fig_energy, use_container_width=True)

st.divider()

st.subheader("Historical event explorer")
st.write(f"Showing **{len(filtered):,}** of **{total_records:,}** records.")

display_cols = [
    col for col in [
        "date", "energy", "impact-e", "alt", "component_speed",
        "ml_assessed", "baseline_flag", "iforest_flag",
        "review_status"
    ]
    if col in filtered.columns
]

st.dataframe(
    filtered[display_cols],
    use_container_width=True,
    hide_index=True
)

st.download_button(
    "Download filtered records as CSV",
    data=filtered.to_csv(index=False).encode("utf-8"),
    file_name="meteorwatch_filtered_report.csv",
    mime="text/csv"
)

st.divider()

st.subheader("Inspect an individual event")

if len(filtered) > 0:
    selected_index = st.selectbox(
        "Select an event",
        options=filtered.index.tolist(),
        format_func=lambda i: (
            f"{filtered.loc[i, 'date']} | "
            f"Energy: {filtered.loc[i, 'energy']:g}"
        )
    )

    event = filtered.loc[selected_index]

    x, y = st.columns(2)

    with x:
        st.write("**Event measurements**")
        st.write(f"Date: {event['date']}")
        st.write(f"Energy: {event['energy']}")
        st.write(f"Impact energy: {event.get('impact-e', 'Unavailable')}")
        st.write(f"Altitude: {event.get('alt', 'Unavailable')}")
        st.write(
            f"Calculated speed: "
            f"{event.get('component_speed', 'Unavailable')}"
        )

    with y:
        st.write("**Analysis results**")
        st.write(f"Review status: {event['review_status']}")
        st.write(f"ML assessed: {event['ml_assessed']}")
        st.write(f"Baseline flag: {event['baseline_flag']}")
        st.write(f"Isolation Forest flag: {event['iforest_flag']}")

    st.write("**Explanation**")
    st.write(
        event.get(
            "explanation",
            "No explanation is available for this record."
        )
    )
else:
    st.info("No records match the selected filters.")

st.divider()
st.caption(
    "Research prototype | Historical records only | "
    "No future-impact prediction or operational warning"
)
