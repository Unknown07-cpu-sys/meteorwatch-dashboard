"""Design tokens, status encoding and number/date formatting for METEORWATCH.

Design rule: colour is reserved for detector status. Everything else (chrome,
text, neutral charts) stays in moonlit blue-greys, so a coloured mark always
means something about how a record was reviewed.

Status encoding
    * filled mark   -> the record was assessed by the detectors named in its status
    * hollow mark   -> the Isolation Forest did not (or could not) assess it.
                       Hollow is deliberately NOT the colour of "not flagged".

Pure Python: no Streamlit and no Plotly, so it can be tested on its own.
"""
from __future__ import annotations

import html
import math
from typing import Any, Iterable

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Tokens
# ---------------------------------------------------------------------------

SKY = "#121A33"       # page
DECK = "#1A2342"      # panels
DECK_2 = "#232E57"    # raised / hover
LINE = "#33407A"      # borders
TEXT = "#ECEAF6"      # moonlight
DIM = "#AEB6D8"       # secondary text
FAINT = "#7C86B3"     # tertiary text (non-essential only)

LAND = "#27336A"
OCEAN = "#0F1630"

DISPLAY_FONT_CSS = "'Bricolage Grotesque', 'Instrument Sans', system-ui, sans-serif"
BODY_FONT_CSS = "'Instrument Sans', system-ui, -apple-system, 'Segoe UI', sans-serif"
PLOT_FONT = "Instrument Sans, system-ui, -apple-system, Segoe UI, sans-serif"
PLOT_DISPLAY_FONT = "Bricolage Grotesque, Instrument Sans, system-ui, sans-serif"

# key -> (colour, hollow)
STATUS_STYLES: dict[str, tuple[str, bool]] = {
    "both": ("#FFD97A", False),                 # white-hot
    "baseline": ("#FF7B54", False),             # ember
    "forest": ("#C79BFF", False),               # ultraviolet
    "baseline_unassessed": ("#FF7B54", True),   # ember, ML did not assess
    "quiet": ("#5FA9B8", False),                # cool slate: not flagged
    "unassessed": ("#7C86B8", True),            # faded: ML did not assess
    "unknown": ("#8A8FA8", True),
}
STATUS_RANK = {key: i for i, key in enumerate(STATUS_STYLES)}


def is_missing(value: Any) -> bool:
    if value is None:
        return True
    try:
        result = pd.isna(value)
        if isinstance(result, (bool, np.bool_)):
            return bool(result)
    except (TypeError, ValueError):
        pass
    return False


def classify_status(status: Any) -> str:
    """Map a saved review-status string to a visual style key."""
    if is_missing(status):
        return "unknown"
    text = str(status).strip().lower()
    if not text:
        return "unknown"
    if "both" in text:
        return "both"
    if "not assessed" in text or "assessment status unknown" in text:
        if "baseline flagged" in text:
            return "baseline_unassessed"
        if "baseline did not flag" in text:
            return "unassessed"
        return "unknown"
    if "isolation forest only" in text:
        return "forest"
    if "baseline only" in text:
        return "baseline"
    if "not flagged by either" in text or "neither" in text:
        return "quiet"
    if "baseline flagged" in text and "unknown" in text:
        return "baseline_unassessed"
    return "unknown"


def status_color(status: Any) -> str:
    return STATUS_STYLES[classify_status(status)][0]


def is_hollow(status: Any) -> bool:
    return STATUS_STYLES[classify_status(status)][1]


def ordered_statuses(values: Iterable[Any]) -> list[str]:
    """Unique status strings in a stable, meaningful visual order."""
    seen: dict[str, None] = {}
    for value in values:
        if is_missing(value):
            continue
        seen.setdefault(str(value), None)
    return sorted(seen, key=lambda s: (STATUS_RANK[classify_status(s)], s))


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

esc = html.escape


def fmt_day(ts: Any) -> str:
    if is_missing(ts):
        return "date not reported"
    return f"{ts.day} {ts.strftime('%b')} {ts.year}"


def fmt_stamp(ts: Any) -> str:
    if is_missing(ts):
        return "Date not reported"
    return f"{ts.day} {ts.strftime('%b')} {ts.year}, {ts.strftime('%H:%M:%S')} GMT"


def fmt_amount(value: Any, digits: int | None = None) -> str | None:
    """Adaptive number format. Returns None when the value is missing."""
    if is_missing(value):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not math.isfinite(number):
        return None
    if digits is not None:
        return f"{number:,.{digits}f}"
    magnitude = abs(number)
    if magnitude >= 100:
        return f"{number:,.0f}"
    if magnitude >= 10:
        return f"{number:,.1f}"
    if magnitude >= 1:
        return f"{number:,.2f}"
    return f"{number:,.3f}"


def fmt_coords(lat: Any, lon: Any) -> str | None:
    if is_missing(lat) or is_missing(lon):
        return None
    lat, lon = float(lat), float(lon)
    return (
        f"{abs(lat):.2f}° {'N' if lat >= 0 else 'S'}, "
        f"{abs(lon):.2f}° {'E' if lon >= 0 else 'W'}"
    )
