from __future__ import annotations

from pathlib import Path
from typing import Any
import hashlib
import inspect

import numpy as np
import pandas as pd
import streamlit as st

from meteorwatch import ui
from meteorwatch.agent import (
    assess_event,
    audit_saved_statuses,
    build_structured_review_export,
    run_agent_self_tests,
)
from meteorwatch.briefing import event_briefing, make_ai_briefing
from meteorwatch.data import load_report as read_report, safe_int
from meteorwatch.evaluation import (
    build_detector_evaluation,
    build_detector_evaluation_table,
    build_event_level_comparison,
)
from meteorwatch.exports import build_review_workbook
from meteorwatch.records import (
    SEARCH_COLUMNS,
    SORT_OPTIONS,
    event_labels,
    py_scalar,
    records_table,
    selected_rows,
    sort_events,
)
from meteorwatch.sensitivity import build_score_threshold_sensitivity


APP_TITLE = "METEORWATCH"
DATA_FILENAME = "meteorwatch_full_review_report.csv"
ROOT = Path(__file__).resolve().parent
DATA_CANDIDATES = [ROOT / "data" / DATA_FILENAME, ROOT / DATA_FILENAME, Path(DATA_FILENAME)]
NASA_API_DOCS = "https://ssd-api.jpl.nasa.gov/doc/fireball.html"
NASA_FIREBALLS = "https://cneos.jpl.nasa.gov/fireballs/"
DEFAULT_GEMINI_MODEL = "gemini-3.5-flash-lite"

st.set_page_config(
    page_title=f"{APP_TITLE} | Historical fireball review desk",
    page_icon="☄️",
    layout="wide",
    initial_sidebar_state="collapsed",
)
st.markdown(ui.theme_css(), unsafe_allow_html=True)


def _stretch_kwargs(func: Any) -> dict[str, Any]:
    """Full-width sizing that works on current and older Streamlit releases."""
    try:
        default = inspect.signature(func).parameters["use_container_width"].default
    except Exception:
        default = False
    return {"width": "stretch"} if default is None else {"use_container_width": True}


STRETCH_DF = _stretch_kwargs(st.dataframe)
STRETCH_PLOT = _stretch_kwargs(st.plotly_chart)


def show_plot(fig: Any, key: str | None = None) -> None:
    if fig is not None:
        st.plotly_chart(fig, theme=None, config=ui.PLOT_CONFIG, key=key, **STRETCH_PLOT)


def show_table(data: pd.DataFrame, **kwargs: Any) -> None:
    st.dataframe(data, hide_index=True, **STRETCH_DF, **kwargs)


def say(html_text: str) -> None:
    """Render trusted, author-written HTML from meteorwatch.ui."""
    st.markdown(html_text, unsafe_allow_html=True)


def chapter(name: str) -> Any:
    """A styled container. ``key=`` needs Streamlit 1.39 or later; older versions get a plain one."""
    try:
        return st.container(key=f"mw_{name}")
    except TypeError:
        return st.container()


@st.cache_data(show_spinner=False)
def load_report(file_bytes: bytes) -> pd.DataFrame:
    return read_report(file_bytes)


# Heavy, deterministic computations are cached so that selecting a row or changing a
# filter does not rebuild workbooks and evaluation tables.
@st.cache_data(show_spinner=False)
def cached_structured_export(frame: pd.DataFrame) -> pd.DataFrame:
    return build_structured_review_export(frame)


@st.cache_data(show_spinner=False)
def cached_workbook(frame: pd.DataFrame, full: pd.DataFrame) -> bytes:
    return build_review_workbook(frame, full)


@st.cache_data(show_spinner=False)
def cached_evaluation(full: pd.DataFrame) -> tuple[Any, pd.DataFrame, pd.DataFrame]:
    return (
        build_detector_evaluation(full),
        build_detector_evaluation_table(full),
        build_event_level_comparison(full),
    )


@st.cache_data(show_spinner=False)
def cached_sensitivity(full: pd.DataFrame) -> Any:
    return build_score_threshold_sensitivity(full)


@st.cache_data(show_spinner=False)
def cached_self_tests() -> pd.DataFrame:
    return run_agent_self_tests()


def table_column_config() -> dict[str, Any]:
    cc = st.column_config
    return {
        "Date (GMT)": cc.DatetimeColumn("Date (GMT)", format="YYYY-MM-DD HH:mm"),
        "Review status": cc.TextColumn("Review status", width="large"),
        "Energy (×10¹⁰ J)": cc.NumberColumn("Energy (×10¹⁰ J)", format="%.2f"),
        "Impact energy (kt)": cc.NumberColumn("Impact energy (kt)", format="%.3f"),
        "Altitude (km)": cc.NumberColumn("Altitude (km)", format="%.1f"),
        "Speed (km/s)": cc.NumberColumn("Speed (km/s)", format="%.1f"),
        "ML score": cc.NumberColumn("ML score", format="%.4f"),
    }

# ---------------------------------------------------------------------------
# Load the report
# ---------------------------------------------------------------------------

default_file = next((p for p in DATA_CANDIDATES if p.exists()), None)

with st.sidebar:
    with st.expander("Report file", expanded=default_file is None):
        uploaded_file = st.file_uploader(
            "Upload the full historical report CSV",
            type=["csv"],
            help="Use meteorwatch_full_review_report.csv from your analysis workflow.",
        )

try:
    if uploaded_file is not None:
        df = load_report(uploaded_file.getvalue())
        source_label = "Uploaded CSV"
    elif default_file is not None:
        df = load_report(default_file.read_bytes())
        source_label = DATA_FILENAME
    else:
        say(
            ui.empty_state_html(
                "Add the report to get started",
                "Open the sidebar and upload meteorwatch_full_review_report.csv, or put it in the data/ folder.",
            )
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
    # Do not infer assessment from the mere presence of a saved flag.
    df["ml_assessed"] = pd.Series(pd.NA, index=df.index, dtype="boolean")
if "explanation" not in df.columns:
    df["explanation"] = "No saved explanation is available for this row."

# Catalogue-level figures derived from the loaded data.
total_records = len(df)
ml_assessed_count = int(df["ml_assessed"].eq(True).sum())
ml_not_assessed_count = int(df["ml_assessed"].eq(False).sum())
ml_assessment_unknown_count = int(df["ml_assessed"].isna().sum())
baseline_count = safe_int(df["baseline_flag"])
ml_flag_count = safe_int(df["iforest_flag"])
coordinate_count = int(df[["map_latitude", "map_longitude"]].notna().all(axis=1).sum())

# ---------------------------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------------------------
# Widget keys carry a version and a data signature. "Reset filters" bumps the version,
# and a newly uploaded file gets a fresh set of widgets, so stale selections never leak.

st.session_state.setdefault("mw_filter_version", 0)
data_sig = hashlib.md5(
    f"{total_records}|{df['date'].min()}|{df['date'].max()}|{df['energy'].sum()}|{source_label}".encode()
).hexdigest()[:8]
fkey = f"{st.session_state['mw_filter_version']}_{data_sig}"


def reset_filters() -> None:
    st.session_state["mw_filter_version"] = st.session_state.get("mw_filter_version", 0) + 1


with st.sidebar:
    say(ui.side_title_html("Filter the records"))
    st.caption("Filters apply to chapters 01, 02, 04 and 05. The opening sky and chapter 03 always use the whole catalogue.")
    inview_slot = st.empty()

    status_values = ui.ordered_statuses(df["review_status"])
    selected_statuses = st.multiselect(
        "Review status",
        options=status_values,
        default=status_values,
        key=f"flt_status_{fkey}",
    )

    min_date = df["date"].min()
    max_date = df["date"].max()
    if pd.notna(min_date) and pd.notna(max_date):
        date_range = st.date_input(
            "Event date range (GMT)",
            value=(min_date.date(), max_date.date()),
            min_value=min_date.date(),
            max_value=max_date.date(),
            key=f"flt_dates_{fkey}",
        )
    else:
        date_range = None

    minimum_energy = float(max(0.0, df["energy"].min(skipna=True)))
    maximum_energy = float(df["energy"].max(skipna=True))
    if np.isfinite(maximum_energy) and maximum_energy >= minimum_energy:
        energy_floor = st.number_input(
            "Minimum reported energy (×10¹⁰ joules)",
            min_value=minimum_energy,
            max_value=maximum_energy,
            value=minimum_energy,
            step=1.0,
            key=f"flt_energy_{fkey}",
        )
    else:
        energy_floor = 0.0
    missing_energy_count = int(df["energy"].isna().sum())
    if missing_energy_count:
        st.caption(
            f"{missing_energy_count:,} catalogue records have no reported energy; "
            "they remain included because the energy filter cannot be applied to them."
        )

    search_text = st.text_input(
        "Search records",
        placeholder="Date, energy, status, coordinates…",
        key=f"flt_search_{fkey}",
        help="Searches dates, energy values, review status, explanations and coordinates.",
    )
    st.button("Reset filters", on_click=reset_filters, key="reset_filters_btn")

filtered = df.copy()
filtered = filtered[filtered["review_status"].astype(str).isin(selected_statuses)]
# Apply the minimum-energy filter only where energy was reported. Keep missing-energy
# records visible so a numeric filter does not silently hide incomplete observations.
filtered = filtered[filtered["energy"].isna() | (filtered["energy"] >= energy_floor)]
if date_range and isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    start_date, end_date = date_range
    filtered = filtered[
        filtered["date"].notna()
        & (filtered["date"].dt.date >= start_date)
        & (filtered["date"].dt.date <= end_date)
    ]
if search_text.strip() and not filtered.empty:
    term = search_text.strip()
    search_columns = [col for col in SEARCH_COLUMNS if col in filtered.columns]
    searchable = filtered[search_columns].astype("string").fillna("").agg(" ".join, axis=1)
    filtered = filtered[searchable.str.contains(term, case=False, na=False, regex=False)]

inview_slot.markdown(ui.inview_html(len(filtered), total_records), unsafe_allow_html=True)


# ===========================================================================
# The page: one scrolling story
# ===========================================================================

_years = (max_date.year - min_date.year) if pd.notna(min_date) and pd.notna(max_date) else 0
_flagged_any = int((df["baseline_flag"].eq(True) | df["iforest_flag"].eq(True)).sum())
_first_year = int(min_date.year) if pd.notna(min_date) else None
_last_year = int(max_date.year) if pd.notna(max_date) else None

# ---- Opening: the catalogue as a sky ---------------------------------------
say(ui.hero_html(df, years=_years, flagged_any=_flagged_any))

_span = f" recorded between {_first_year} and {_last_year}" if _first_year and _last_year else ""
say(
    ui.statement_html(
        "The record",
        f"This catalogue holds {total_records:,} fireballs{_span}. Each one has a time and an energy. "
        "Only some report where, how high and how fast. What is missing matters as much as what is there.",
    )
)

# ---- 01 Sky ------------------------------------------------------------------
with chapter("sky"):
    say(
        ui.chapter_head_html(
            "01",
            ["Every fireball,", "by date and energy"],
            "Each mark is one record, placed by when it happened and how much energy it radiated. "
            "Drag to zoom and hover for details. Open the arrow at the top left to filter.",
        )
    )
    if filtered.empty:
        say(
            ui.empty_state_html(
                "No records match these filters",
                "Widen the date range, lower the minimum energy, or clear the search in the sidebar.",
            )
        )
    else:
        view_counts = filtered["review_status"].astype(str).value_counts()
        say(
            ui.status_key_html(
                [(status, int(view_counts.get(status, 0))) for status in status_values],
                in_view=len(filtered),
                catalogue=total_records,
            )
        )
        show_plot(ui.timeline_figure(filtered), key="plot_timeline")

        sky_left, sky_right = st.columns([1.7, 1], gap="large")
        with sky_left:
            say(
                ui.section_html(
                    "How energy is spread out",
                    "Reported energy spans several orders of magnitude, so each bar covers a quarter of a "
                    "power of ten.",
                )
            )
            show_plot(ui.energy_histogram_figure(filtered), key="plot_energy_hist")
        with sky_right:
            say(ui.section_html("Reading the marks"))
            say(ui.mark_legend_html())

# ---- 02 Map ------------------------------------------------------------------
with chapter("map"):
    say(
        ui.chapter_head_html(
            "02",
            ["Where they", "peaked"],
            "Each mark is the reported peak-brightness location of one fireball. Larger marks radiated more energy.",
        )
    )
    map_mode = st.radio("View", ["Flat map", "Globe"], horizontal=True, key="map_view")
    centre_lon = 0.0
    if map_mode == "Globe":
        centre_lon = float(st.slider("Turn the globe (longitude)", -180, 180, 0, key="map_globe_lon"))
    map_fig = ui.map_figure(filtered, globe=(map_mode == "Globe"), centre_lon=centre_lon) if not filtered.empty else None
    if map_fig is None:
        say(
            ui.empty_state_html(
                "No mapped records in view",
                "None of the records matching your filters reports valid coordinates. Widen the filters to see more.",
            )
        )
    else:
        mapped = int(filtered[["map_latitude", "map_longitude"]].notna().all(axis=1).sum())
        st.caption(
            f"{mapped:,} records in view report a location. North and east are positive; south and west are negative."
        )
        show_plot(map_fig, key="plot_map")
        say(
            ui.callout_html(
                "A mark shows the reported peak-brightness location, not an impact site. "
                "Records without a reported location are left off the map rather than guessed.",
                lead="Read the map carefully.",
            )
        )

# ---- 03 Detectors (pinned scene) -------------------------------------------
say(
    ui.detectors_story_html(
        assessed=ml_assessed_count,
        total=total_records,
        baseline_flags=baseline_count,
        forest_flags=ml_flag_count,
        flagged_both=int((df["baseline_flag"].eq(True) & df["iforest_flag"].eq(True)).sum()),
    )
)
with chapter("detectors"):
    say(
        ui.coverage_html(
            assessed=ml_assessed_count,
            not_assessed=ml_not_assessed_count,
            unknown=ml_assessment_unknown_count,
            total=total_records,
            baseline_flags=baseline_count,
            forest_flags=ml_flag_count,
        )
    )
    with st.expander("How to read these flags"):
        st.markdown(
            "- **A flag is a prompt to review.** A saved statistical check picked the record out. "
            "It is not a hazard rating or proof of a physical anomaly.\n"
            "- **Not flagged does not mean safe.** It only means neither saved check selected the record.\n"
            "- **Not assessed is not the same as not flagged.** The Isolation Forest only assesses records "
            "that report energy, altitude and all three velocity components.\n"
            "- **Locations are not impact sites.** Coordinates mark where the fireball was brightest."
        )

# ---- 04 Explore --------------------------------------------------------------
with chapter("explore"):
    say(
        ui.chapter_head_html(
            "04",
            ["Look at a", "single fireball"],
            "Select a row to open its record sheet: what was measured, what each detector saved, and where the fireball was brightest.",
        )
    )
    if filtered.empty:
        say(
            ui.empty_state_html(
                "No records match these filters",
                "Change the sidebar filters to inspect records.",
            )
        )
    else:
        head_left, head_right = st.columns([3, 1], gap="large")
        with head_left:
            say(
                ui.section_html(
                    "Records in view",
                    f"{len(filtered):,} records match your filters. Order them, then select a row.",
                )
            )
        with head_right:
            sort_choice = st.selectbox("Order by", SORT_OPTIONS, key="records_sort")

        with st.expander("Download this view"):
            st.caption(
                "The structured report groups identity, measurements with units, detector results, agent "
                "explanations, missing fields and a suggested review action. Records needing review come "
                "first; that order is not a hazard ranking."
            )
            structured_export = cached_structured_export(filtered)
            export_left, export_middle, export_right = st.columns(3)
            with export_left:
                st.download_button(
                    "Structured review report (CSV)",
                    data=structured_export.to_csv(index=False, lineterminator="\n").encode("utf-8-sig"),
                    file_name="meteorwatch_structured_review_report.csv",
                    mime="text/csv",
                    help="One row per event, with readable units, decision explanations, missing-data notes and a suggested review action.",
                    key="download_structured_review_v8",
                )
            with export_middle:
                st.download_button(
                    "Multi-sheet workbook (XLSX)",
                    data=cached_workbook(filtered, df),
                    file_name="meteorwatch_review_workbook.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    help="Eight sheets, including detector agreement and the catalogue-wide score-threshold sensitivity study.",
                    key="download_review_workbook_v11",
                )
            with export_right:
                st.download_button(
                    "Technical data (CSV)",
                    data=filtered.drop(columns=["map_latitude", "map_longitude"], errors="ignore")
                    .to_csv(index=False, lineterminator="\n")
                    .encode("utf-8-sig"),
                    file_name="meteorwatch_filtered_technical_data.csv",
                    mime="text/csv",
                    help="The filtered source/technical columns, retained for analysis and reproducibility.",
                    key="download_technical_data_v8",
                )

        view = sort_events(filtered, sort_choice)
        table = records_table(view)

        selection_supported = True
        selected_position: int | None = None
        try:
            table_event = st.dataframe(
                table,
                hide_index=True,
                height=330,
                column_config=table_column_config(),
                on_select="rerun",
                selection_mode="single-row",
                key="records_table",
                **STRETCH_DF,
            )
            picked = selected_rows(table_event)
            if picked and picked[0] < len(view):
                selected_position = picked[0]
        except TypeError:
            # Older Streamlit without row selection: fall back to a dropdown.
            selection_supported = False
            show_table(table, height=330, column_config=table_column_config())

        if not selection_supported:
            labels = event_labels(view)
            fallback_ids = list(labels)
            if st.session_state.get("explorer_selected_event_id") not in labels:
                st.session_state["explorer_selected_event_id"] = fallback_ids[0]
            chosen_id_pick = st.selectbox(
                "Choose a record",
                fallback_ids,
                format_func=lambda i: labels.get(i, str(i)),
                key="explorer_selected_event_id",
            )
            selected_position = fallback_ids.index(chosen_id_pick)
        elif selected_position is None:
            selected_position = 0
            st.caption("Showing the first record in this order. Select any row above to open another.")

        chosen = view.iloc[selected_position]
        chosen_id = py_scalar(view.index[selected_position])
        st.session_state["mw_focus_id"] = chosen_id  # lets the Briefing tab open the same record

        agent_assessment = assess_event(chosen)
        sheet_col, globe_col = st.columns([1.7, 1], gap="large")
        with sheet_col:
            say(ui.record_sheet_html(chosen, agent_assessment))
        with globe_col:
            if pd.notna(chosen.get("map_latitude")) and pd.notna(chosen.get("map_longitude")):
                show_plot(
                    ui.locator_figure(
                        float(chosen["map_latitude"]),
                        float(chosen["map_longitude"]),
                        chosen.get("review_status"),
                    ),
                    key="plot_locator",
                )
                st.caption("Where this fireball was brightest. Not an impact site.")
            else:
                say(
                    ui.empty_state_html(
                        "No location reported",
                        "This record has no valid coordinates, so nothing is placed on the globe.",
                    )
                )

        with st.expander("Rule-generated briefing for this record", expanded=True):
            st.markdown(event_briefing(chosen))
            st.caption(
                "This briefing is generated from fixed rules and the record's fields. "
                "It is not a generative-AI conclusion or a validated physical explanation."
            )

# ---- 05 Briefing ---------------------------------------------------------------
with chapter("brief"):
    say(
        ui.chapter_head_html(
            "05",
            ["Put it in", "plain words"],
            "Pick a record, choose what to explain, then generate a briefing. "
            "A briefing explains a record; it does not detect or confirm hazards.",
        )
    )
    say(
        ui.callout_html(
            "AI output can be incomplete or mistaken. A statistical flag is a prompt for human review, "
            "not a danger prediction, and METEORWATCH does not forecast future impacts.",
            lead="Check the output.",
        )
    )

    setup_col, run_col = st.columns([1, 1.3], gap="large")

    with setup_col:
        provider = st.selectbox(
            "How should the briefing be written?",
            [
                "No API — built-in briefing (free)",
                "OpenRouter — free-model router",
                "Google Gemini API",
                "Custom OpenAI-compatible API",
            ],
            key="ai_provider_choice",
        )

        api_key = ""
        model_name = ""
        base_url = ""
        api_provider_name = provider

        if provider == "OpenRouter — free-model router":
            st.markdown(
                "Use your own OpenRouter API key with its free-model router. "
                "The default model is `openrouter/free`, which routes to available free models. "
                "Free service still has rate limits and availability can change."
            )
            api_key = st.text_input(
                "Your OpenRouter API key",
                type="password",
                key="openrouter_user_api_key",
                help="The key is used for this request and is not written to the project files by this app.",
            )
            model_name = "openrouter/free"
            base_url = "https://openrouter.ai/api/v1"
            api_provider_name = "OpenAI-compatible API"
            st.caption("OpenRouter free model information: https://openrouter.ai/docs/guides/routing/routers/free-router")

        elif provider == "Google Gemini API":
            st.markdown(
                "Gemini offers a free tier for selected models, subject to account eligibility and rate limits. "
                "Free-tier data handling differs from paid-tier data handling; review the provider's terms before use."
            )
            api_key = st.text_input(
                "Your Gemini API key",
                type="password",
                key="gemini_user_api_key",
                help="Create a key in Google AI Studio. Do not paste it into GitHub or share it in a public message.",
            )
            model_name = st.text_input(
                "Gemini model name",
                value=DEFAULT_GEMINI_MODEL,
                key="gemini_model_name",
                help="This model is listed with free-tier input/output pricing in Google's current pricing documentation; limits and availability can still vary.",
            )
            api_provider_name = "Google Gemini API"
            st.caption("Check current pricing and terms: https://ai.google.dev/gemini-api/docs/pricing")

        elif provider == "Custom OpenAI-compatible API":
            st.markdown(
                "For APIs that implement the OpenAI-compatible `/chat/completions` format. "
                "Not every API uses this format. Ask your provider for its base URL and model name."
            )
            base_url = st.text_input(
                "HTTPS API base URL",
                value="https://api.groq.com/openai/v1",
                key="custom_api_base_url",
                help="Examples: Groq uses https://api.groq.com/openai/v1; OpenRouter uses https://openrouter.ai/api/v1.",
            )
            model_name = st.text_input(
                "Model name",
                value="openai/gpt-oss-20b",
                key="custom_api_model",
                help="Use a model ID supported by your provider and plan.",
            )
            api_key = st.text_input(
                "Your provider API key",
                type="password",
                key="custom_api_user_key",
                help="This app does not intentionally save it to a file or repository. It is passed through the app server to the provider.",
            )
            api_provider_name = "OpenAI-compatible API"
            st.caption("Provider models, rate limits, and billing depend on the provider/account you select.")

        else:
            say(
                ui.callout_html(
                    "No external API is needed. METEORWATCH writes a rule-based briefing from the selected "
                    "record and its saved detection results. It is not a generative language model.",
                    lead="Built-in briefing.",
                )
            )

        say(
            ui.callout_html(
                "If you enter a key, it passes through this Streamlit-hosted app’s server to make the request. "
                "This code does not intentionally write the key to disk, a CSV or GitHub, but only enter a key "
                "if you trust the app operator and the provider. Never enter confidential data.",
                lead="Keys and privacy.",
            )
        )

    with run_col:
        if filtered.empty:
            say(
                ui.empty_state_html(
                    "No records to brief",
                    "Adjust the sidebar filters to choose a record.",
                )
            )
        else:
            ai_rows = filtered.sort_values("date", ascending=False, na_position="last")
            ai_labels = event_labels(ai_rows)
            ai_ids = list(ai_labels)

            # Open the record chosen on the Records tab, once per change of that choice.
            focus_id = st.session_state.get("mw_focus_id")
            if focus_id in ai_labels and st.session_state.get("mw_ai_synced") != focus_id:
                st.session_state["ai_event_id"] = focus_id
                st.session_state["mw_ai_synced"] = focus_id
            elif st.session_state.get("ai_event_id") not in ai_labels:
                st.session_state["ai_event_id"] = ai_ids[0]

            ai_selected_id = st.selectbox(
                "Record to explain",
                ai_ids,
                format_func=lambda i: ai_labels.get(i, str(i)),
                key="ai_event_id",
                help="Starts from the record open on the Records tab. Type to search the list.",
            )
            ai_selected = ai_rows.loc[ai_selected_id]

            if provider == "No API — built-in briefing (free)":
                ai_mode_options = [
                    "Generate an event briefing",
                    "Explain the detection status",
                    "Explain missing measurements and uncertainty",
                ]
            else:
                ai_mode_options = [
                    "Generate an event briefing",
                    "Explain the detection status",
                    "Explain missing measurements and uncertainty",
                    "Answer my question about this record",
                ]

            ai_mode = st.selectbox("What should the briefing explain?", ai_mode_options, key="ai_mode")

            if ai_mode == "Generate an event briefing":
                user_question = "Generate a concise, plain-language briefing for this historical record."
            elif ai_mode == "Explain the detection status":
                user_question = "Explain the saved baseline and Isolation Forest status for this event, including whether ML assessed it."
            elif ai_mode == "Explain missing measurements and uncertainty":
                user_question = "Explain which measurements are unavailable and how that limits interpretation of this record."
            else:
                user_question = st.text_area(
                    "Your question",
                    placeholder="Example: What can we conclude from this record, and what can’t we conclude?",
                    max_chars=700,
                    key="ai_custom_question",
                ).strip()

            st.caption(
                "Only the selected record's allowlisted fields, brief project-level counts, and your question "
                "are sent to the selected provider. The full CSV is not submitted."
            )

            if st.button("Generate briefing", type="primary", key="generate_ai_briefing_v5"):
                if not user_question:
                    st.warning("Enter a question before generating a briefing.")
                elif provider != "No API — built-in briefing (free)" and not api_key.strip():
                    st.warning("Enter your own provider API key, or choose the no-API option.")
                else:
                    with st.spinner("Preparing the event briefing…"):
                        try:
                            if provider == "No API — built-in briefing (free)":
                                result = event_briefing(ai_selected)
                                result += (
                                    "\n\n**No-API mode:** This is generated from fixed rules and saved fields. "
                                    "It does not interpret an open-ended question with a language model."
                                )
                                shown_model = "Built-in rule-based briefing (no API)"
                            else:
                                result = make_ai_briefing(
                                    ai_selected,
                                    user_question,
                                    provider=api_provider_name,
                                    api_key=api_key,
                                    model=model_name,
                                    base_url=base_url,
                                    catalogue_records=total_records,
                                    records_assessed=ml_assessed_count,
                                )
                                shown_model = f"{provider} · {model_name}"

                            st.session_state["meteorwatch_ai_result"] = result
                            st.session_state["meteorwatch_ai_result_key"] = (
                                str(ai_selected.get("date")), str(ai_selected_id), ai_mode,
                                user_question, provider, model_name,
                            )
                            st.session_state["meteorwatch_ai_result_provider"] = shown_model
                        except Exception as exc:
                            # Never display raw exception strings because some providers
                            # may include request details. Do not log the supplied API key.
                            st.error(
                                f"The briefing request failed ({type(exc).__name__}). Check the API key, "
                                "model name, endpoint, rate limit, and provider account. "
                                "The no-API rule-based briefing remains available."
                            )

            expected_key = (
                str(ai_selected.get("date")), str(ai_selected_id), ai_mode,
                user_question, provider, model_name,
            )
            if (
                st.session_state.get("meteorwatch_ai_result")
                and st.session_state.get("meteorwatch_ai_result_key") == expected_key
            ):
                with st.container(border=True):
                    st.markdown(st.session_state["meteorwatch_ai_result"])
                st.caption(
                    f"Written by {st.session_state.get('meteorwatch_ai_result_provider', provider)}. "
                    "Check it against the record and the project methods."
                )
                st.download_button(
                    "Download briefing as Markdown",
                    data=st.session_state["meteorwatch_ai_result"].encode("utf-8"),
                    file_name="meteorwatch_event_briefing.md",
                    mime="text/markdown",
                    key="download_ai_briefing_v5",
                )

# ---- 06 Checks ---------------------------------------------------------------
with chapter("lab"):
    say(
        ui.chapter_head_html(
            "06",
            ["Check the", "checks"],
            "How well the two detectors agree, how much the Isolation Forest threshold matters, whether the "
            "software follows its own rules, and how complete the data is. Nothing here measures detector accuracy, "
            "because the project has no independently verified anomaly labels.",
        )
    )
    lab_agree, lab_sens, lab_audit, lab_tests, data_quality, data_method = st.tabs(
        ["Agreement", "Threshold sensitivity", "Status audit", "Logic tests", "Data quality", "Method and limits"]
    )

    # ---- Agreement ----
    with lab_agree:
        say(
            ui.section_html(
                "Do the two detectors agree?",
                "This compares the saved IQR and Isolation Forest results where both exist. Agreement is not "
                "accuracy, and neither method is treated as ground truth.",
            )
        )
        say(
            ui.callout_html(
                "This evaluation uses the entire loaded report and ignores the sidebar filters. It does not report "
                "precision, recall or detector accuracy.",
                lead="Whole catalogue.",
            )
        )

        detector_eval, evaluation_table, pairwise_export = cached_evaluation(df)
        comp_1, comp_2, comp_3, comp_4 = st.columns(4)
        comp_1.metric("Loaded records", f"{detector_eval['total_records']:,}")
        comp_2.metric(
            "Baseline results available",
            f"{detector_eval['baseline_results_available']:,}",
            f"{detector_eval['baseline_coverage_pct']:.1f}% coverage" if detector_eval["baseline_coverage_pct"] is not None else "Coverage unavailable",
            delta_color="off",
        )
        comp_3.metric(
            "ML explicitly assessed",
            f"{detector_eval['ml_explicitly_assessed']:,}",
            f"{detector_eval['ml_assessed_pct']:.1f}% of loaded records" if detector_eval["ml_assessed_pct"] is not None else "Coverage unavailable",
            delta_color="off",
        )
        comp_4.metric(
            "Comparable pairs",
            f"{detector_eval['comparable_pairs']:,}",
            f"{detector_eval['comparable_pct_of_loaded_records']:.1f}% of loaded records" if detector_eval["comparable_pct_of_loaded_records"] is not None else "No comparable records",
            delta_color="off",
        )

        agree_1, agree_2, agree_3 = st.columns(3)
        agreement_value = detector_eval["observed_agreement_pct"]
        kappa_value = detector_eval["cohen_kappa"]
        jaccard_value = detector_eval["jaccard_flag_overlap_pct"]
        agree_1.metric("Observed agreement", "N/A" if agreement_value is None else f"{agreement_value:.1f}%")
        agree_2.metric("Cohen's kappa", "N/A" if kappa_value is None else f"{kappa_value:.3f}")
        agree_3.metric("Flagged-set overlap (Jaccard)", "N/A" if jaccard_value is None else f"{jaccard_value:.1f}%")

        outcome_table = pd.DataFrame(
            [
                {"Pairwise outcome": name, "Comparable records": int(count)}
                for name, count in detector_eval["outcome_counts"].items()
            ]
        )
        say(ui.section_html("Outcomes among comparable records"))
        if detector_eval["comparable_pairs"]:
            show_plot(ui.outcome_figure(outcome_table), key="plot_outcomes")
        else:
            say(
                ui.callout_html(
                    "No records have both known detector results and an explicit ML-assessed status, "
                    "so agreement statistics are not defined.",
                    lead="Nothing to compare.",
                )
            )
        with st.expander("Counts, definitions and consistency counters"):
            show_table(outcome_table)
            show_table(evaluation_table)
            st.caption(
                "Observed agreement is the fraction of comparable records where the methods returned the same flag. "
                "Cohen's kappa adjusts agreement for the observed marginal rates. Jaccard overlap compares the sets "
                "flagged by either method. These descriptive statistics do not identify which method is correct."
            )

        export_eval_col, export_pair_col = st.columns(2)
        with export_eval_col:
            st.download_button(
                "Detector evaluation summary (CSV)",
                data=evaluation_table.to_csv(index=False, lineterminator="\n").encode("utf-8-sig"),
                file_name="meteorwatch_detector_evaluation_summary.csv",
                mime="text/csv",
                key="download_detector_eval_summary_v10",
            )
        with export_pair_col:
            st.download_button(
                "Event-level detector comparison (CSV)",
                data=pairwise_export.to_csv(index=False, lineterminator="\n").encode("utf-8-sig"),
                file_name="meteorwatch_event_detector_comparison.csv",
                mime="text/csv",
                help="Includes comparable outcomes, unassessed records, and saved-field inconsistencies.",
                key="download_detector_pairwise_v10",
            )

    # ---- Threshold sensitivity ----
    with lab_sens:
        say(
            ui.section_html(
                "How sensitive is the score threshold?",
                "This shows how the number of selected records changes when different percentile cutoffs are "
                "applied to the saved Isolation Forest scores. Lower scores are treated as more unusual.",
            )
        )
        say(
            ui.callout_html(
                "This is a threshold-only study. It reuses the saved scores and does not refit the model, change "
                "stored flags, alter the review queue, or show which records are true anomalies. It uses the whole "
                "loaded report, not the filtered view.",
                lead="Scores only.",
            )
        )
        sensitivity_result = cached_sensitivity(df)
        sensitivity_summary = sensitivity_result["summary"]
        sensitivity_detail = sensitivity_result["event_detail"]
        sensitivity_meta = sensitivity_result["metadata"]

        sens_1, sens_2, sens_3, sens_4 = st.columns(4)
        sens_1.metric("Scored records included", f"{sensitivity_meta['eligible_scored_records']:,}")
        sens_2.metric("Explicitly not assessed", f"{sensitivity_meta['not_assessed_records']:,}")
        sens_3.metric("Assessment status unknown", f"{sensitivity_meta['assessment_status_unknown_records']:,}")
        sens_4.metric("Assessed but score unavailable", f"{sensitivity_meta['assessed_records_without_finite_score']:,}")

        if sensitivity_summary.empty:
            say(
                ui.callout_html(
                    "No records have both an explicit ML-assessed status and a finite saved Isolation Forest score.",
                    lead="Study unavailable.",
                )
            )
        else:
            reference_disagreements = sensitivity_meta["reference_saved_flag_disagreements"]
            if reference_disagreements is not None:
                st.caption(
                    f"At the 5% reference setting, {sensitivity_meta['reference_records_flagged']:,} "
                    f"records are below the score cutoff. Among {sensitivity_meta['saved_flags_comparable_at_reference']:,} "
                    f"records with saved flags, {reference_disagreements:,} differ from the score-derived result. "
                    "This is a consistency check; inspect differences rather than assuming either value is correct."
                )
            show_plot(ui.sensitivity_figure(sensitivity_summary), key="plot_sensitivity")
            show_table(sensitivity_summary)

            sens_download_a, sens_download_b = st.columns(2)
            with sens_download_a:
                st.download_button(
                    "Threshold sensitivity summary (CSV)",
                    data=sensitivity_summary.to_csv(index=False, lineterminator="\n").encode("utf-8-sig"),
                    file_name="meteorwatch_score_threshold_sensitivity_summary.csv",
                    mime="text/csv",
                    key="download_score_threshold_sensitivity_v11",
                )
            with sens_download_b:
                st.download_button(
                    "Event-level threshold comparison (CSV)",
                    data=sensitivity_detail.to_csv(index=False, lineterminator="\n").encode("utf-8-sig"),
                    file_name="meteorwatch_score_threshold_sensitivity_events.csv",
                    mime="text/csv",
                    help="Includes all rows and labels records excluded because they were not assessed, have unknown assessment status, or lack a saved score.",
                    key="download_score_threshold_events_v11",
                )
            with st.expander("Method and limitations"):
                st.markdown(
                    "- The analysis uses existing `iforest_score` values; smaller (more negative) scores are treated as more unusual.\n"
                    "- It calculates score cutoffs at 1%, 2.5%, 5%, 7.5%, 10%, and 15%. The 5% setting is the reference for overlap calculations.\n"
                    "- A record is selected only when its score is strictly below the percentile cutoff. Tied scores at the cutoff may make the actual selected percentage lower than the setting.\n"
                    "- Only rows with `ml_assessed = True` and a finite saved score are included. Missing or unknown states remain excluded and visible in the event-level export.\n"
                    "- This does not test different training samples, features, random seeds, or refit the model. It is not a measure of accuracy, precision, recall, physical danger, or future impact risk."
                )

    # ---- Status audit ----
    with lab_audit:
        say(
            ui.section_html(
                "Do saved statuses match the saved flags?",
                "This audit rebuilds each record’s interpretation from the saved baseline_flag, ml_assessed and "
                "iforest_flag, then compares it with the saved review_status. Incomplete rows count as not "
                "comparable instead of matching.",
            )
        )
        if st.button("Run consistency audit on the loaded report", key="run_agent_status_audit_v7"):
            audit_counts, audit_mismatches = audit_saved_statuses(df)
            st.session_state["meteorwatch_agent_audit_counts_v7"] = audit_counts
            st.session_state["meteorwatch_agent_audit_mismatches_v7"] = audit_mismatches

        audit_counts = st.session_state.get("meteorwatch_agent_audit_counts_v7")
        audit_mismatches = st.session_state.get("meteorwatch_agent_audit_mismatches_v7")
        if audit_counts is not None:
            audit_a, audit_b, audit_c, audit_d = st.columns(4)
            audit_a.metric("Rows compared", f"{audit_counts['comparable_rows']:,}")
            audit_b.metric("Matches", f"{audit_counts['matching_rows']:,}")
            audit_c.metric("Mismatches", f"{audit_counts['mismatching_rows']:,}")
            audit_d.metric("Not comparable", f"{audit_counts['not_comparable_rows']:,}")
            st.caption(
                f"Loaded rows: {audit_counts['total_rows']:,}. Only rows with both known detector flags "
                "and an assessed model result can be compared. A mismatch is a consistency-review item, "
                "not proof that a physical event was misclassified."
            )
            if audit_mismatches is not None and not audit_mismatches.empty:
                say(ui.section_html("Rows for review"))
                show_table(audit_mismatches)
                st.download_button(
                    "Status mismatches (CSV)",
                    data=audit_mismatches.to_csv(index=False).encode("utf-8"),
                    file_name="meteorwatch_agent_status_mismatches.csv",
                    mime="text/csv",
                    key="download_agent_status_mismatches_v7",
                )
            elif audit_counts["comparable_rows"]:
                st.write("No saved-status mismatches were found among comparable rows.")
            else:
                st.write(
                    "No rows had enough saved information for a status comparison. "
                    "Check that the CSV includes baseline_flag, ml_assessed, iforest_flag, and review_status."
                )
        else:
            st.caption("Run the audit to see how many rows match, differ, or cannot be compared.")

        say(
            ui.callout_html(
                "“Flagged” means a saved statistical method selected the record for review. “Not flagged” is not "
                "“safe”, and “ML not assessed” is not “ML did not flag”. The agent explains saved outputs; it does "
                "not verify the NASA/JPL measurements or infer a future trajectory.",
                lead="How to read the agent’s result.",
            )
        )

    # ---- Logic tests ----
    with lab_tests:
        say(
            ui.section_html(
                "Does the agent follow its own rules?",
                "These synthetic cases check that the agent reads saved flags consistently, keeps missing values "
                "missing, and keeps scientific limits visible. They are software tests, not verified fireball labels "
                "and not a measure of detector accuracy.",
            )
        )
        self_test_report = cached_self_tests()
        passed_tests = int(self_test_report["Passed"].sum())
        total_tests = int(len(self_test_report))
        failed_tests = total_tests - passed_tests
        test_col1, test_col2, test_col3 = st.columns(3)
        test_col1.metric("Logic tests passed", f"{passed_tests}/{total_tests}")
        test_col2.metric("Failed checks", f"{failed_tests}")
        test_col3.metric("Test type", "Synthetic cases")
        show_table(self_test_report)
        st.download_button(
            "Agent self-test report (CSV)",
            data=self_test_report.to_csv(index=False).encode("utf-8"),
            file_name="meteorwatch_agent_self_tests.csv",
            mime="text/csv",
            key="download_agent_self_tests_v7",
        )
        st.caption(
            "A passing test means the software followed the expected rule for that example. "
            "It does not prove the detector finds real physical anomalies or predicts hazards."
        )

    with data_method:
        say(ui.section_html("What the system does"))
        st.markdown(
            "1. Loads a saved NASA/JPL Fireball Data API response and normalizes field types.\n"
            "2. Uses an IQR rule on log-transformed reported energy as a transparent baseline.\n"
            "3. Uses Isolation Forest on log-energy, altitude, and the magnitude calculated from entry-velocity components, but only where all required values are present.\n"
            "4. Combines the flags into review statuses and creates rule-generated context for a human reviewer.\n"
            "5. Optionally uses a user-provided LLM API key with a supported provider, or a built-in rule-based briefing without an API; neither retrains the detector or validates physical risk."
        )

        say(ui.section_html("Fields and units"))
        say(
            ui.definitions_html(
                [
                    ("date", "Time of peak brightness, reported in GMT."),
                    ("energy", "Approximate total radiated energy, in units of 10¹⁰ joules."),
                    ("impact-e", "Approximate impact energy, in kilotons (kt)."),
                    ("alt", "Altitude above the Earth geoid at peak brightness, in kilometres."),
                    ("vx, vy, vz", "Entry-velocity components in km/s. This app computes speed as √(vx² + vy² + vz²)."),
                    ("lat, lon", "Reported peak-brightness location, not a confirmed ground impact point."),
                ]
            )
        )
        st.markdown(
            f"Sources: [NASA/JPL Fireball API documentation]({NASA_API_DOCS}) and "
            f"[NASA/JPL Fireballs]({NASA_FIREBALLS})."
        )

        say(ui.section_html("Limits that stay visible"))
        say(
            ui.callout_html(
                "This is exploratory anomaly detection, not a validated danger classifier. The dataset is a catalogue "
                "of reported detections, not a complete census of every fireball. Many records lack altitude, velocity "
                "components, or location, so the model assessed only a subset. The 5% Isolation Forest contamination "
                "value is a model setting, not the true rate of physical anomalies. There are no independently verified "
                "anomaly labels here, so accuracy, recall, and danger claims cannot be established from these results "
                "alone. An unflagged record is not proof of safety.",
                lead="Read before drawing conclusions.",
            )
        )

    with data_quality:
        say(
            ui.section_html(
                "Dataset quality and model coverage",
                "This page describes how complete and well-formed the loaded report is. It does not certify that the "
                "source measurements are physically correct. Missing values stay missing; they are never treated as zero.",
            )
        )

        valid_dates = df["date"].dropna() if "date" in df.columns else pd.Series(dtype="datetime64[ns]")
        date_start = valid_dates.min() if not valid_dates.empty else pd.NaT
        date_end = valid_dates.max() if not valid_dates.empty else pd.NaT
        duplicate_rows = int(df.duplicated().sum())
        ml_assessed_rows = int(df["ml_assessed"].eq(True).sum()) if "ml_assessed" in df else 0
        ml_not_assessed_rows = int(df["ml_assessed"].eq(False).sum()) if "ml_assessed" in df else 0
        ml_assessment_unknown_rows = int(df["ml_assessed"].isna().sum()) if "ml_assessed" in df else total_records
        ml_coverage_pct = (ml_assessed_rows / total_records * 100) if total_records else 0.0
        coordinate_count_local = int(
            df[["map_latitude", "map_longitude"]].notna().all(axis=1).sum()
        ) if {"map_latitude", "map_longitude"}.issubset(df.columns) else 0

        q1, q2, q3, q4, q5 = st.columns(5)
        q1.metric("Total catalogue rows", f"{total_records:,}")
        q2.metric("ML assessed", f"{ml_assessed_rows:,}", f"{ml_coverage_pct:.1f}% of rows", delta_color="off")
        q3.metric("ML not assessed", f"{ml_not_assessed_rows:,}")
        q4.metric("Assessment status unknown", f"{ml_assessment_unknown_rows:,}")
        q5.metric("Rows with map coordinates", f"{coordinate_count_local:,}")

        if pd.notna(date_start) and pd.notna(date_end):
            st.caption(
                f"Date coverage in this file: {date_start.strftime('%Y-%m-%d')} through "
                f"{date_end.strftime('%Y-%m-%d')} (reported event times are GMT)."
            )
        say(
            ui.callout_html(
                f"The report explicitly marks {ml_assessed_rows:,} rows as assessed, "
                f"{ml_not_assessed_rows:,} as not assessed, and {ml_assessment_unknown_rows:,} with unknown "
                "assessment status. Unknown status is reported separately rather than silently counted as "
                "either assessed or not assessed.",
                lead="Coverage.",
            )
        )

        say(ui.section_html("Field completeness"))
        field_labels = {
            "date": "Event date/time",
            "energy": "Reported radiated energy (×10¹⁰ J)",
            "impact-e": "Estimated impact energy (kt)",
            "lat": "Latitude magnitude",
            "lon": "Longitude magnitude",
            "alt": "Altitude (km)",
            "component_speed": "Speed calculated from vx/vy/vz (km/s)",
            "vx": "Velocity component vx (km/s)",
            "vy": "Velocity component vy (km/s)",
            "vz": "Velocity component vz (km/s)",
            "map_latitude": "Valid signed map latitude",
            "map_longitude": "Valid signed map longitude",
        }
        available_quality_fields = [col for col in field_labels if col in df.columns]
        completeness_rows = []
        for col in available_quality_fields:
            missing_count = int(df[col].isna().sum())
            present_count = int(df[col].notna().sum())
            completeness_rows.append({
                "Field": field_labels[col],
                "Available": present_count,
                "Missing": missing_count,
                "Missing (%)": round(missing_count / total_records * 100, 2) if total_records else 0.0,
            })
        completeness = pd.DataFrame(completeness_rows)
        if not completeness.empty:
            left_quality, right_quality = st.columns([1, 1.2], gap="large")
            with left_quality:
                show_table(completeness)
                st.download_button(
                    "Field-completeness report (CSV)",
                    data=completeness.to_csv(index=False).encode("utf-8"),
                    file_name="meteorwatch_field_completeness.csv",
                    mime="text/csv",
                    key="download_field_completeness_v6",
                )
            with right_quality:
                show_plot(ui.completeness_figure(completeness), key="plot_completeness")

        say(ui.section_html("Structural checks"))
        checks = []
        checks.append({
            "Check": "Rows with an unparseable/missing date",
            "Rows affected": int(df["date"].isna().sum()) if "date" in df else total_records,
            "Interpretation": "These rows cannot be placed reliably on the time axis.",
        })
        checks.append({
            "Check": "Rows with missing or invalid signed map coordinates",
            "Rows affected": int(df[["map_latitude", "map_longitude"]].isna().any(axis=1).sum())
                if {"map_latitude", "map_longitude"}.issubset(df.columns) else total_records,
            "Interpretation": "Locations are omitted from the map; no location is inferred.",
        })
        checks.append({
            "Check": "Rows with missing or non-positive reported energy",
            "Rows affected": int((df["energy"].isna() | (df["energy"] <= 0)).sum()) if "energy" in df else total_records,
            "Interpretation": "Review these values before applying log-energy analysis.",
        })
        if {"vx", "vy", "vz", "alt", "energy"}.issubset(df.columns):
            feature_complete = df[["energy", "alt", "vx", "vy", "vz"]].notna().all(axis=1)
            checks.append({
                "Check": "Rows missing one or more required Isolation Forest features",
                "Rows affected": int((~feature_complete).sum()),
                "Interpretation": "The v2/v3 model experiment required energy, altitude, and all three velocity components.",
            })
        checks.append({
            "Check": "Exact duplicate rows in the loaded report",
            "Rows affected": duplicate_rows,
            "Interpretation": "Exact-row comparison only; it does not identify differently formatted versions of the same event.",
        })
        show_table(pd.DataFrame(checks))

        say(ui.section_html("Saved review-status breakdown"))
        if "review_status" in df.columns:
            status_breakdown = (
                df["review_status"].fillna("Status unavailable")
                .value_counts()
                .rename_axis("Review status")
                .reset_index(name="Records")
            )
            show_table(status_breakdown)
            st.download_button(
                "Review-status breakdown (CSV)",
                data=status_breakdown.to_csv(index=False).encode("utf-8"),
                file_name="meteorwatch_review_status_breakdown.csv",
                mime="text/csv",
                key="download_status_breakdown_v6",
            )

        say(
            ui.callout_html(
                "Completeness is not measurement accuracy. A complete row can still contain a revised or uncertain "
                "reported estimate. Missing coordinates do not mean an event did not occur. Missing ML results are "
                "not negative predictions. The 5% Isolation Forest contamination value is a configuration choice, "
                "not an observed rate of physically anomalous fireballs. This project has no independently verified "
                "anomaly labels, so the dashboard does not claim classification accuracy or a danger score.",
                lead="How to read this page.",
            )
        )

# ---- Closing -------------------------------------------------------------------
say(ui.closing_html())
