"""Visual design system for the METEORWATCH dashboard.

Design rule: colour is reserved for detector status. Everything else (chrome,
text, neutral charts) stays in moonlit blue-greys, so a coloured mark always
means something about how a record was reviewed.

Status encoding
    * filled mark   -> the record was assessed by the detectors named in its status
    * hollow mark   -> the Isolation Forest did not (or could not) assess it.
                       Hollow is deliberately NOT the colour of "not flagged".

This module returns HTML/CSS strings and Plotly figures. It does not import
Streamlit, so it can be tested on its own.
"""
from __future__ import annotations

import html
import math
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd
import plotly.graph_objects as go

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


def classify_status(status: Any) -> str:
    """Map a saved review-status string to a visual style key."""
    if _is_missing(status):
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
        if _is_missing(value):
            continue
        seen.setdefault(str(value), None)
    return sorted(seen, key=lambda s: (STATUS_RANK[classify_status(s)], s))


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

esc = html.escape


def fmt_day(ts: Any) -> str:
    if _is_missing(ts):
        return "date not reported"
    return f"{ts.day} {ts.strftime('%b')} {ts.year}"


def fmt_stamp(ts: Any) -> str:
    if _is_missing(ts):
        return "Date not reported"
    return f"{ts.day} {ts.strftime('%b')} {ts.year}, {ts.strftime('%H:%M:%S')} GMT"


def fmt_amount(value: Any, digits: int | None = None) -> str | None:
    """Adaptive number format. Returns None when the value is missing."""
    if _is_missing(value):
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
    if _is_missing(lat) or _is_missing(lon):
        return None
    lat, lon = float(lat), float(lon)
    return (
        f"{abs(lat):.2f}° {'N' if lat >= 0 else 'S'}, "
        f"{abs(lon):.2f}° {'E' if lon >= 0 else 'W'}"
    )


def _measure(value: Any, unit: str = "", digits: int | None = None) -> str:
    text = fmt_amount(value, digits)
    if text is None:
        return '<span class="mw-na">Not reported</span>'
    unit_html = f'<span class="mw-unit">{esc(unit)}</span>' if unit else ""
    return f"{esc(text)}{unit_html}"


# ---------------------------------------------------------------------------
# Theme CSS
# ---------------------------------------------------------------------------

_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,400..800&family=Instrument+Sans:wght@400..700&display=swap');

:root{
  --mw-sky:%(SKY)s; --mw-deck:%(DECK)s; --mw-deck2:%(DECK_2)s; --mw-line:%(LINE)s;
  --mw-text:%(TEXT)s; --mw-dim:%(DIM)s; --mw-faint:%(FAINT)s;
  --mw-display:%(DISPLAY)s; --mw-body:%(BODY)s;
}

/* ---- page ---- */
.stApp{background:var(--mw-sky);color:var(--mw-text);font-family:var(--mw-body);}
.stApp, .stApp p, .stApp li, .stApp label, .stApp input, .stApp textarea, .stApp button{font-family:var(--mw-body);}
[data-testid="stHeader"]{background:transparent;}
.block-container{max-width:1240px;padding-top:1.4rem;padding-bottom:3rem;}
:focus-visible{outline:2px solid var(--mw-text)!important;outline-offset:2px;}
[data-testid="stElementContainer"]:has(> [data-testid="stMarkdownContainer"] > style),
.element-container:has(> .stMarkdown > style){display:none;}
a{color:var(--mw-text);text-underline-offset:3px;}

/* ---- masthead ---- */
.mw-mast{position:relative;padding:1.2rem 0 1.1rem;margin:0 0 1rem;border-bottom:1px solid var(--mw-line);}
.mw-mast-row{display:flex;flex-wrap:wrap;align-items:flex-end;justify-content:space-between;gap:.8rem 2rem;}
.mw-mast .mw-wordmark{position:relative;display:inline-block;overflow:hidden;
  font-family:var(--mw-display)!important;font-weight:800!important;font-size:clamp(2.3rem,5.4vw,4rem)!important;
  letter-spacing:-.035em!important;line-height:1!important;margin:0!important;padding:0 .1em .08em 0!important;color:var(--mw-text);}
.mw-mast .mw-wordmark::after{content:"";position:absolute;left:0;top:46%%;width:42%%;height:2px;opacity:0;pointer-events:none;
  background:linear-gradient(90deg,transparent,rgba(236,234,246,.95));transform-origin:left center;transform:translateX(-120%%) rotate(-7deg);}
@media (prefers-reduced-motion:no-preference){
  .mw-mast .mw-wordmark::after{animation:mw-streak 1.6s .3s ease-out 1 forwards;}
}
@keyframes mw-streak{0%%{opacity:0;transform:translateX(-120%%) rotate(-7deg);}12%%{opacity:1;}
  100%%{opacity:0;transform:translateX(310%%) rotate(-7deg);}}
.mw-facts{display:flex;flex-wrap:wrap;gap:.3rem 1.8rem;margin:0;padding:0;}
.mw-facts div{display:flex;flex-direction:column;margin:0;}
.mw-facts dt{color:var(--mw-faint);font-size:.76rem;margin:0;}
.mw-facts dd{color:var(--mw-dim);font-size:.9rem;margin:0;}
.mw-lede{font-size:1.18rem;line-height:1.5;max-width:60ch;color:var(--mw-text);margin:.9rem 0 .5rem;}
.mw-scope{font-size:.94rem;line-height:1.5;color:var(--mw-dim);max-width:72ch;margin:0;}
.mw-scope strong{color:var(--mw-text);}

/* ---- status key ---- */
.mw-key{display:grid;grid-template-columns:minmax(180px,.8fr) 4fr;gap:1rem 2rem;align-items:start;margin:0 0 .9rem;}
@media (max-width:900px){.mw-key{grid-template-columns:1fr;}}
.mw-num{font-family:var(--mw-display);font-weight:700;font-variant-numeric:tabular-nums;letter-spacing:-.02em;color:var(--mw-text);line-height:1;}
.mw-key-total .mw-num{display:block;font-size:2.9rem;}
.mw-key-total .mw-cap{display:block;margin-top:.35rem;font-size:.86rem;color:var(--mw-dim);}
.mw-key ul.mw-key-list{list-style:none!important;margin:0!important;padding:0!important;display:grid;
  grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:1rem 1.3rem;}
.mw-key-list li{display:grid;grid-template-columns:auto 1fr;column-gap:.55rem;align-items:center;margin:0!important;padding:0!important;}
.mw-key-list li .mw-num{font-size:1.7rem;}
.mw-key-list li .mw-cap{grid-column:2;font-size:.8rem;line-height:1.3;color:var(--mw-dim);}
.mw-key-list li.mw-zero{opacity:.5;}
.mw-dot{display:inline-block;width:.8rem;height:.8rem;border-radius:50%%;flex:none;border:2px solid transparent;box-sizing:border-box;}
.mw-dot--hollow{background:transparent;}

/* ---- coverage bar ---- */
.mw-cover{margin:0 0 1.1rem;}
.mw-cover-bar{display:flex;height:10px;border-radius:999px;overflow:hidden;background:var(--mw-deck);border:1px solid var(--mw-line);}
.mw-cover-bar span{display:block;height:100%%;}
.mw-cover-bar .a{background:var(--mw-text);}
.mw-cover-bar .n{background:repeating-linear-gradient(135deg,#7C86B8 0 4px,transparent 4px 8px);}
.mw-cover-bar .u{background:repeating-linear-gradient(135deg,#7C86B3 0 2px,transparent 2px 6px);}
.mw-cover p{font-size:.88rem;line-height:1.5;color:var(--mw-dim);margin:.5rem 0 0;max-width:84ch;}
.mw-cover p strong{color:var(--mw-text);}

/* ---- sections, callouts, empty states ---- */
.mw-section{margin:1.5rem 0 .6rem;}
.mw-section .mw-h2{font-family:var(--mw-display)!important;font-size:1.5rem!important;font-weight:650!important;
  letter-spacing:-.018em!important;line-height:1.2!important;margin:0!important;padding:0!important;color:var(--mw-text);}
.mw-section p{margin:.35rem 0 0;color:var(--mw-dim);max-width:70ch;line-height:1.55;font-size:.97rem;}
.mw-callout{border:1px solid var(--mw-line);border-left:4px solid var(--mw-text);border-radius:4px 12px 12px 4px;
  background:var(--mw-deck);padding:.85rem 1.05rem;margin:.6rem 0 1rem;font-size:.94rem;line-height:1.55;color:var(--mw-dim);max-width:92ch;}
.mw-callout strong{color:var(--mw-text);}
.mw-callout code{font-size:.88em;}
.mw-empty{border:1px dashed var(--mw-line);border-radius:12px;padding:2.2rem 1.4rem;text-align:center;margin:1rem 0;}
.mw-empty .mw-empty-title{font-family:var(--mw-display);font-size:1.25rem;font-weight:650;margin:0 0 .4rem;padding:0;color:var(--mw-text);}
.mw-empty p{margin:0;color:var(--mw-dim);}
.mw-legend-list{list-style:none!important;margin:.4rem 0 0!important;padding:0!important;}
.mw-legend-list li{display:grid;grid-template-columns:auto 1fr;gap:.2rem .7rem;align-items:start;margin:0 0 .85rem!important;padding:0!important;
  color:var(--mw-dim);font-size:.93rem;line-height:1.5;}
.mw-legend-list li strong{color:var(--mw-text);}
.mw-legend-list .mw-dot{margin-top:.28rem;}

/* ---- record sheet ---- */
.mw-sheet{background:var(--mw-deck);border:1px solid var(--mw-line);border-radius:16px;padding:1.4rem 1.5rem 1.2rem;}
.mw-sheet-head{display:flex;flex-wrap:wrap;align-items:center;gap:.5rem 1.1rem;margin-bottom:1.1rem;}
.mw-sheet-date{font-family:var(--mw-display);font-weight:750;font-size:clamp(1.5rem,3vw,2.1rem);letter-spacing:-.025em;line-height:1.1;margin:0;color:var(--mw-text);}
.mw-sheet-time{color:var(--mw-dim);margin:0;font-variant-numeric:tabular-nums;}
.mw-chip{display:inline-flex;align-items:center;gap:.55rem;border:1.5px solid var(--mw-line);border-radius:999px;padding:.22rem .8rem .22rem .6rem;
  font-size:.87rem;font-weight:600;color:var(--mw-text);}
.mw-chip.mw-chip--hollow{border-style:dashed;}
.mw-sheet-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:1.3rem 2.4rem;}
.mw-sheet .mw-h3{font-family:var(--mw-display)!important;font-size:1.02rem!important;font-weight:650!important;
  margin:0 0 .3rem!important;padding:0!important;color:var(--mw-dim);}
.mw-rows{margin:0;padding:0;display:grid;grid-template-columns:minmax(0,1fr) auto;column-gap:1.2rem;}
.mw-rows dt,.mw-rows dd{margin:0;padding:.55rem 0;border-bottom:1px solid rgba(51,64,122,.65);}
.mw-rows dt{color:var(--mw-dim);font-size:.9rem;}
.mw-rows dd{text-align:right;font-weight:600;font-variant-numeric:tabular-nums;color:var(--mw-text);}
.mw-rows dd .mw-dot{width:.62rem;height:.62rem;margin-right:.45rem;vertical-align:baseline;}
.mw-unit{color:var(--mw-faint);font-weight:400;margin-left:.35rem;font-size:.82rem;}
.mw-na{color:var(--mw-faint);font-weight:400;}
.mw-sheet-note{color:var(--mw-dim);font-size:.85rem;line-height:1.5;margin:1rem 0 0;max-width:80ch;}

/* ---- sidebar ---- */
[data-testid="stSidebar"]{background:var(--mw-deck);border-right:1px solid var(--mw-line);}
.mw-side-title{font-family:var(--mw-display);font-weight:650;font-size:1.1rem;margin:.2rem 0 .4rem;color:var(--mw-text);}
.mw-inview{display:flex;align-items:baseline;gap:.55rem;margin:.1rem 0 .8rem;color:var(--mw-dim);font-size:.88rem;}
.mw-inview .mw-num{font-size:1.9rem;}

/* ---- footer ---- */
.mw-foot{margin:2.5rem 0 0;padding-top:1rem;border-top:1px solid var(--mw-line);color:var(--mw-dim);font-size:.85rem;line-height:1.55;max-width:90ch;}

/* ---- Streamlit components ---- */
.stTabs [data-baseweb="tab-list"]{gap:.2rem;border-bottom:1px solid var(--mw-line);}
.stTabs button[data-baseweb="tab"]{font-family:var(--mw-display);font-weight:600;font-size:1.02rem;color:var(--mw-dim);
  padding:.7rem 1rem;background:transparent;}
.stTabs button[data-baseweb="tab"]:hover{color:var(--mw-text);background:transparent;}
.stTabs button[data-baseweb="tab"][aria-selected="true"]{color:var(--mw-text);}
.stTabs [data-baseweb="tab-highlight"]{background:var(--mw-text);height:3px;border-radius:3px;}
.stTabs [data-baseweb="tab-border"]{background:transparent;}
/* nested tabs read as a quieter, pill-shaped second level */
.stTabs .stTabs [data-baseweb="tab-list"]{border-bottom:none;gap:.4rem;margin-top:.4rem;}
.stTabs .stTabs button[data-baseweb="tab"]{font-size:.92rem;padding:.35rem .9rem;border:1px solid var(--mw-line);border-radius:999px;}
.stTabs .stTabs button[data-baseweb="tab"][aria-selected="true"]{background:var(--mw-deck2);border-color:var(--mw-dim);}
.stTabs .stTabs [data-baseweb="tab-highlight"]{display:none;}

[data-testid="stMetric"]{background:var(--mw-deck);border:1px solid var(--mw-line);border-radius:6px;padding:.85rem 1rem;}
[data-testid="stMetricLabel"] p{color:var(--mw-dim);font-size:.84rem;}
[data-testid="stMetricValue"]{font-family:var(--mw-display);font-weight:700;letter-spacing:-.02em;}

.stButton>button,.stDownloadButton>button,[data-testid="stBaseButton-secondary"]{border-radius:8px;border:1px solid var(--mw-line);
  background:transparent;color:var(--mw-text);font-weight:600;}
.stButton>button:hover,.stDownloadButton>button:hover,[data-testid="stBaseButton-secondary"]:hover{border-color:var(--mw-text);background:var(--mw-deck2);color:var(--mw-text);}
.stButton>button[kind="primary"],[data-testid="stBaseButton-primary"]{background:var(--mw-text);color:var(--mw-sky);border:1px solid var(--mw-text);}
.stButton>button[kind="primary"]:hover,[data-testid="stBaseButton-primary"]:hover{background:#FFFFFF;color:var(--mw-sky);}

[data-testid="stExpander"] details{border:1px solid var(--mw-line);border-radius:10px;background:transparent;}
[data-testid="stExpander"] summary{font-weight:600;}
[data-testid="stDataFrame"]{border:1px solid var(--mw-line);border-radius:8px;overflow:hidden;}
[data-testid="stCaptionContainer"]{color:var(--mw-dim);}
hr{border-color:var(--mw-line);}
/* ---- cinematic scroll treatment ---- */
.stApp{background:radial-gradient(circle at 78%% 8%%,rgba(115,79,201,.17),transparent 29rem),radial-gradient(circle at 14%% 32%%,rgba(42,136,180,.12),transparent 28rem),linear-gradient(180deg,#080d1b 0%%,#0b1226 42%%,#0d1530 100%%);overflow-x:hidden;}
.stApp::before{content:"";position:fixed;inset:0;pointer-events:none;opacity:.55;z-index:0;background-image:radial-gradient(circle at 12%% 14%%,rgba(255,255,255,.8) 0 1px,transparent 1.5px),radial-gradient(circle at 67%% 19%%,rgba(186,207,255,.6) 0 1px,transparent 1.5px),radial-gradient(circle at 38%% 61%%,rgba(255,255,255,.42) 0 1px,transparent 1.4px),radial-gradient(circle at 91%% 74%%,rgba(186,207,255,.55) 0 1px,transparent 1.5px);background-size:230px 190px,310px 270px,280px 250px,360px 330px;}
.block-container{position:relative;z-index:1;max-width:1380px;padding-top:1.1rem;padding-bottom:5rem;}
[data-testid="stSidebar"]{background:linear-gradient(180deg,rgba(10,16,35,.96),rgba(16,24,55,.94));backdrop-filter:blur(18px);}
.mw-mast{min-height:70vh;display:flex;flex-direction:column;justify-content:center;border:1px solid rgba(124,134,179,.26);border-radius:28px;margin:.2rem 0 1.25rem;padding:clamp(2rem,6vw,6rem);overflow:hidden;isolation:isolate;background:linear-gradient(135deg,rgba(15,25,53,.72),rgba(11,17,38,.4));box-shadow:0 28px 90px rgba(0,0,0,.28);}
.mw-mast::before{content:"";position:absolute;right:-11rem;top:-12rem;width:38rem;height:38rem;border-radius:50%%;border:1px solid rgba(175,185,255,.28);box-shadow:0 0 0 42px rgba(122,111,229,.035),0 0 0 86px rgba(122,111,229,.025);transform:rotate(-18deg);z-index:-1;}
.mw-mast::after{content:"";position:absolute;right:4rem;top:14%%;width:24rem;height:1px;background:linear-gradient(90deg,transparent,rgba(187,202,255,.75),transparent);transform:rotate(-34deg);opacity:.7;z-index:-1;}
.mw-mast-row{align-items:flex-start;position:relative;z-index:1;}
.mw-mast .mw-wordmark{flex:1 1 auto;min-width:0;white-space:nowrap;font-size:clamp(3.4rem,8vw,7.4rem)!important;line-height:.88!important;letter-spacing:-.07em!important;text-shadow:0 0 36px rgba(187,202,255,.18);}
.mw-mast .mw-wordmark::before{content:"// HISTORICAL FIREBALL REVIEW DESK";display:block;font-family:var(--mw-body);font-size:.72rem;letter-spacing:.2em;font-weight:700;color:#8fa0db;margin:0 0 1.2rem .15rem;}
.mw-mast .mw-wordmark::after{height:3px;width:55%%;top:57%%;background:linear-gradient(90deg,#f9d17d,rgba(249,209,125,0));}
.mw-facts{justify-content:flex-end;gap:.8rem;max-width:30rem;}
.mw-facts div{min-width:8rem;padding:.8rem 1rem;border:1px solid rgba(124,134,179,.25);border-radius:14px;background:rgba(16,25,53,.6);}
.mw-facts dt{font-size:.67rem;letter-spacing:.14em;text-transform:uppercase;color:#7f8bc1;}
.mw-facts dd{font-size:.84rem;color:#d5dcff;margin-top:.25rem;}
.mw-lede{font-family:var(--mw-display);font-size:clamp(1.35rem,2.7vw,2.25rem);line-height:1.12;max-width:24ch;margin:clamp(2.4rem,8vh,5.5rem) 0 .9rem;letter-spacing:-.035em;}
.mw-scope{max-width:52ch;font-size:.94rem;color:#aeb9df;}
.mw-hero-meta{display:flex;align-items:center;gap:1rem;margin-top:2.4rem;color:#8998d0;font-size:.76rem;letter-spacing:.14em;text-transform:uppercase;}
.mw-hero-meta::before{content:"";display:block;width:3.5rem;height:1px;background:#f9d17d;}
.mw-chapter-nav{position:sticky;top:.65rem;z-index:20;display:flex;align-items:center;gap:.35rem;overflow-x:auto;margin:0 0 1.6rem;padding:.45rem;border:1px solid rgba(124,134,179,.27);border-radius:999px;background:rgba(10,16,35,.78);backdrop-filter:blur(18px);box-shadow:0 10px 30px rgba(0,0,0,.18);}
.mw-chapter-nav a{white-space:nowrap;text-decoration:none!important;color:#9da9d0;padding:.58rem .85rem;border-radius:999px;font-size:.72rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;transition:background .2s ease,color .2s ease,transform .2s ease;}
.mw-chapter-nav a:hover,.mw-chapter-nav a:focus-visible{background:rgba(190,204,255,.12);color:#f3f1ff;transform:translateY(-1px);}
.mw-chapter-nav .mw-nav-mark{width:.42rem;height:.42rem;border-radius:50%%;background:#f9d17d;box-shadow:0 0 16px #f9d17d;margin:0 .45rem 0 .35rem;flex:none;}
.mw-signal-strip{display:grid;grid-template-columns:1.35fr repeat(4,1fr);gap:0;margin:0 0 2.1rem;border-top:1px solid rgba(124,134,179,.32);border-bottom:1px solid rgba(124,134,179,.32);}
.mw-signal{padding:1.05rem 1.1rem;border-right:1px solid rgba(124,134,179,.22);}
.mw-signal:last-child{border-right:0;}
.mw-signal .mw-signal-value{display:block;font-family:var(--mw-display);font-size:clamp(1.5rem,3vw,2.6rem);font-weight:750;letter-spacing:-.05em;color:#f5f1ff;line-height:1;}
.mw-signal .mw-signal-label{display:block;margin-top:.38rem;color:#8e9ac6;font-size:.68rem;letter-spacing:.14em;text-transform:uppercase;line-height:1.3;}
.mw-signal--accent .mw-signal-value{color:#f9d17d;}
.mw-section{position:relative;margin:3.2rem 0 .8rem;padding-top:.85rem;}
.mw-section::before{content:"";position:absolute;left:0;top:0;width:4.6rem;height:2px;background:linear-gradient(90deg,#f9d17d,transparent);}
.mw-section .mw-h2{font-size:clamp(1.7rem,3vw,2.5rem)!important;letter-spacing:-.045em!important;}
.mw-section p{max-width:62ch;color:#9ea9cf;}
.mw-section .mw-h2::after{content:" /";color:#6977ad;font-weight:400;}
.mw-key{padding:1.5rem 1.35rem;border:1px solid rgba(124,134,179,.23);border-radius:20px;background:linear-gradient(135deg,rgba(20,31,66,.76),rgba(15,24,52,.48));box-shadow:0 18px 50px rgba(0,0,0,.14);}
.mw-key-total .mw-num{font-size:clamp(2.8rem,5vw,4.6rem);letter-spacing:-.07em;}
.mw-cover{padding:1rem 1.2rem;border:1px solid rgba(124,134,179,.18);border-radius:16px;background:rgba(17,27,58,.46);}
.mw-cover-bar{height:8px;background:#131e40;border-color:rgba(124,134,179,.28);}
.mw-sheet{border-radius:22px;background:linear-gradient(145deg,rgba(22,34,72,.9),rgba(14,23,49,.82));border-color:rgba(124,134,179,.28);box-shadow:0 24px 70px rgba(0,0,0,.2);}
.mw-callout{border-left-color:#f9d17d;border-radius:4px 18px 18px 4px;background:rgba(20,31,66,.7);}
.stTabs{margin-top:1rem;}
.stTabs [data-baseweb="tab-list"]{position:sticky;top:4.75rem;z-index:15;gap:.3rem;padding:.4rem;border:1px solid rgba(124,134,179,.25);border-radius:17px;background:rgba(10,16,35,.8);backdrop-filter:blur(16px);overflow-x:auto;}
.stTabs button[data-baseweb="tab"]{font-size:.78rem;letter-spacing:.1em;text-transform:uppercase;border-radius:12px;padding:.72rem 1rem;white-space:nowrap;}
.stTabs button[data-baseweb="tab"][aria-selected="true"]{background:rgba(193,204,255,.11);color:#f7f4ff;}
.stTabs [data-baseweb="tab-highlight"]{background:#f9d17d;height:2px;}
[data-testid="stPlotlyChart"],[data-testid="stDataFrame"]{border:1px solid rgba(124,134,179,.2);border-radius:20px;background:rgba(13,21,46,.35);overflow:hidden;}
[data-testid="stMetric"]{border-radius:16px;background:rgba(19,30,64,.72);border-color:rgba(124,134,179,.24);}
.mw-foot{max-width:none;padding:1.3rem 0 0;color:#7e8bb7;}
@media (max-width:850px){.mw-mast{min-height:72vh;padding:2rem 1.35rem;border-radius:21px}.mw-mast-row{display:block}.mw-mast .mw-wordmark{font-size:clamp(2.35rem,10.3vw,4.5rem)!important;white-space:normal}.mw-facts{justify-content:flex-start;margin-top:2rem}.mw-facts div{min-width:0;flex:1}.mw-signal-strip{grid-template-columns:repeat(2,1fr)}.mw-signal:first-child{grid-column:span 2}.mw-signal:nth-child(2){border-bottom:1px solid rgba(124,134,179,.22)}.mw-signal:nth-child(3){border-bottom:1px solid rgba(124,134,179,.22)}.stTabs [data-baseweb="tab-list"]{top:3.5rem}.mw-key{grid-template-columns:1fr}.mw-key-list{margin-top:1.5rem!important;}}
@media (prefers-reduced-motion:reduce){*,*::before,*::after{scroll-behavior:auto!important;animation:none!important;transition:none!important;}}
"""


def theme_css() -> str:
    """The page stylesheet, wrapped for st.markdown(..., unsafe_allow_html=True)."""
    css = _CSS % {
        "SKY": SKY, "DECK": DECK, "DECK_2": DECK_2, "LINE": LINE, "TEXT": TEXT,
        "DIM": DIM, "FAINT": FAINT, "DISPLAY": DISPLAY_FONT_CSS, "BODY": BODY_FONT_CSS,
    }
    return f"<style>{css}</style>"


# ---------------------------------------------------------------------------
# HTML components (single-line-safe: no blank lines, no indented blocks)
# ---------------------------------------------------------------------------

def _dot(color: str, hollow: bool) -> str:
    kind = "hollow" if hollow else "solid"
    style = f"border-color:{color}" if hollow else f"background:{color};border-color:{color}"
    return f'<span class="mw-dot mw-dot--{kind}" style="{style}" aria-hidden="true"></span>'


def status_dot(status: Any) -> str:
    return _dot(status_color(status), is_hollow(status))


def masthead_html(source_label: str, n_records: int, first: Any, last: Any) -> str:
    coverage = (
        f"{fmt_day(first)} to {fmt_day(last)}"
        if not _is_missing(first) and not _is_missing(last)
        else "Dates not reported"
    )
    return (
        '<header class="mw-mast">'
        '<div class="mw-mast-row">'
        '<div class="mw-wordmark" role="heading" aria-level="1">METEORWATCH</div>'
        '<dl class="mw-facts">'
        '<div><dt>Source</dt><dd>NASA/JPL Fireball Data API</dd></div>'
        f'<div><dt>Coverage</dt><dd>{esc(coverage)}</dd></div>'
        f'<div><dt>File</dt><dd>{esc(source_label)}</dd></div>'
        '</dl>'
        '</div>'
        '<p class="mw-lede">A guided flight through NASA/JPL’s historical fireball records — from raw signal to human review.</p>'
        '<p class="mw-scope"><strong>Historical records only.</strong> A flag means “take a closer look”, '
        'not “dangerous”. METEORWATCH does not forecast impacts or issue warnings.</p>'
        '<div class="mw-hero-meta">scroll to navigate the archive</div>'
        '</header>'
    )


def chapter_nav_html() -> str:
    """A lightweight orientation rail for the long-form dashboard journey."""
    links = [("01", "Sky", "#sky"), ("02", "Map", "#map"), ("03", "Records", "#records"), ("04", "Briefing", "#briefing"), ("05", "Lab", "#lab"), ("06", "Method", "#method")]
    items = ''.join(f'<a href="{href}">{num} / {label}</a>' for num, label, href in links)
    return f'<nav class="mw-chapter-nav" aria-label="Dashboard chapters"><span class="mw-nav-mark" aria-hidden="true"></span>{items}</nav>'


def signal_strip_html(total: int, in_view: int, baseline: int, forest: int, mapped: int) -> str:
    """Top-of-page signal readout: factual, compact, and visually distinct from status colours."""
    cells = [
        ("mw-signal mw-signal--accent", f"{total:,}", "historical records in archive"),
        ("mw-signal", f"{in_view:,}", "records in current view"),
        ("mw-signal", f"{baseline:,}", "IQR review prompts"),
        ("mw-signal", f"{forest:,}", "Isolation Forest prompts"),
        ("mw-signal", f"{mapped:,}", "records with coordinates"),
    ]
    return '<section class="mw-signal-strip" aria-label="Archive signal summary">' + ''.join(
        f'<div class="{cls}"><span class="mw-signal-value">{value}</span><span class="mw-signal-label">{label}</span></div>'
        for cls, value, label in cells
    ) + '</section>'


def status_key_html(counts: Sequence[tuple[str, int]], in_view: int, catalogue: int) -> str:
    items = []
    for status, count in counts:
        zero = " mw-zero" if count == 0 else ""
        items.append(
            f'<li class="{zero.strip()}">{status_dot(status)}'
            f'<span class="mw-num">{count:,}</span>'
            f'<span class="mw-cap">{esc(status)}</span></li>'
        )
    return (
        '<section class="mw-key" aria-label="Records in view by review status">'
        '<div class="mw-key-total">'
        f'<span class="mw-num">{in_view:,}</span>'
        f'<span class="mw-cap">records in view, of {catalogue:,} in the catalogue</span>'
        '</div>'
        f'<ul class="mw-key-list">{"".join(items)}</ul>'
        '</section>'
    )


def coverage_html(
    assessed: int,
    not_assessed: int,
    unknown: int,
    total: int,
    baseline_flags: int,
    forest_flags: int,
) -> str:
    if total <= 0:
        return ""
    pct = lambda n: n / total * 100  # noqa: E731
    extra = ""
    if unknown:
        extra = f" {unknown:,} have an unknown assessment status."
    return (
        '<div class="mw-cover">'
        '<div class="mw-cover-bar" role="img" aria-label="Isolation Forest coverage across the catalogue">'
        f'<span class="a" style="width:{pct(assessed):.3f}%"></span>'
        f'<span class="n" style="width:{pct(not_assessed):.3f}%"></span>'
        f'<span class="u" style="width:{pct(unknown):.3f}%"></span>'
        '</div>'
        f'<p>The Isolation Forest could assess <strong>{assessed:,} of {total:,} records '
        f'({pct(assessed):.1f}%)</strong> across the whole catalogue. The other {not_assessed:,} lacked '
        f'required measurements; that is not the same as “not flagged”.{esc(extra)} '
        f'Saved flags across the catalogue: {baseline_flags:,} from the IQR baseline, '
        f'{forest_flags:,} from the Isolation Forest.</p>'
        '</div>'
    )


def section_html(title: str, intro: str | None = None) -> str:
    intro_html = f"<p>{esc(intro)}</p>" if intro else ""
    return f'<div class="mw-section"><div class="mw-h2" role="heading" aria-level="2">{esc(title)}</div>{intro_html}</div>'


def callout_html(body_html: str, lead: str | None = None) -> str:
    """body_html is trusted, author-written HTML (never user data)."""
    lead_html = f"<strong>{esc(lead)}</strong> " if lead else ""
    return f'<div class="mw-callout" role="note">{lead_html}{body_html}</div>'


def empty_state_html(title: str, hint: str) -> str:
    return f'<div class="mw-empty"><div class="mw-empty-title" role="heading" aria-level="3">{esc(title)}</div><p>{esc(hint)}</p></div>'


def side_title_html(text: str) -> str:
    return f'<p class="mw-side-title">{esc(text)}</p>'


def inview_html(n: int, total: int) -> str:
    return (
        f'<div class="mw-inview"><span class="mw-num">{n:,}</span>'
        f'<span>of {total:,} records match your filters</span></div>'
    )


def mark_legend_html() -> str:
    return (
        '<ul class="mw-legend-list">'
        f'<li>{_dot(TEXT, False)}<span><strong>Filled mark.</strong> Colour shows the saved review status. '
        'Orange is the IQR baseline, violet is the Isolation Forest, gold is both.</span></li>'
        f'<li>{_dot(TEXT, True)}<span><strong>Hollow mark.</strong> The Isolation Forest did not assess this record, '
        'usually because altitude or velocity was not reported. It is not the same as “not flagged”.</span></li>'
        '</ul>'
    )


def definitions_html(rows: Sequence[tuple[str, str]]) -> str:
    """Two-column definition list; terms and text are author-written, escaped here."""
    body = "".join(f"<dt><code>{esc(term)}</code></dt><dd>{esc(text)}</dd>" for term, text in rows)
    return f'<div class="mw-sheet"><dl class="mw-rows">{body}</dl></div>'


def footer_html() -> str:
    return (
        '<footer class="mw-foot">METEORWATCH is a student research prototype for historical analysis. '
        'It does not predict future impacts or issue operational warnings. '
        'Measurements come from the NASA/JPL Fireball Data API; flags are saved statistical results, '
        'not verified anomaly labels.</footer>'
    )


def _baseline_cell(assessment: dict[str, Any]) -> str:
    flag = assessment.get("baseline_flag")
    if flag is True:
        return f'{_dot(STATUS_STYLES["baseline"][0], False)}Flagged'
    if flag is False:
        return f'{_dot(STATUS_STYLES["quiet"][0], False)}No flag'
    return f'{_dot(STATUS_STYLES["unknown"][0], True)}<span class="mw-na">No saved result</span>'


def _forest_cell(assessment: dict[str, Any]) -> str:
    assessed = assessment.get("ml_assessed")
    flag = assessment.get("iforest_flag")
    if assessed is True:
        if flag is True:
            return f'{_dot(STATUS_STYLES["forest"][0], False)}Flagged'
        if flag is False:
            return f'{_dot(STATUS_STYLES["quiet"][0], False)}No flag'
        return f'{_dot(STATUS_STYLES["unknown"][0], True)}<span class="mw-na">No saved flag</span>'
    if assessed is False:
        return f'{_dot(STATUS_STYLES["unassessed"][0], True)}Not assessed'
    return f'{_dot(STATUS_STYLES["unknown"][0], True)}<span class="mw-na">Assessment unknown</span>'


def record_sheet_html(row: Any, assessment: dict[str, Any]) -> str:
    """One record, laid out as a sheet: when, what was measured, what the detectors saved."""
    get = row.get if hasattr(row, "get") else (lambda key, default=None: default)
    status = get("review_status")
    status_text = "Status unavailable" if _is_missing(status) else str(status)
    chip_cls = "mw-chip mw-chip--hollow" if is_hollow(status_text) else "mw-chip"
    chip = (
        f'<span class="{chip_cls}" style="border-color:{status_color(status_text)}">'
        f'{status_dot(status_text)}{esc(status_text)}</span>'
    )

    ts = get("date")
    if _is_missing(ts):
        date_html = '<p class="mw-sheet-date"><span class="mw-na">Date not reported</span></p>'
    else:
        date_html = (
            f'<p class="mw-sheet-date">{ts.day} {esc(ts.strftime("%B"))} {ts.year}</p>'
            f'<p class="mw-sheet-time">{esc(ts.strftime("%H:%M:%S"))} GMT</p>'
        )

    coords = fmt_coords(get("map_latitude"), get("map_longitude"))
    coords_html = esc(coords) if coords else '<span class="mw-na">Not reported</span>'

    measurements = (
        f'<dt>Reported radiated energy</dt><dd>{_measure(get("energy"), "×10¹⁰ J")}</dd>'
        f'<dt>Estimated impact energy</dt><dd>{_measure(get("impact-e"), "kt")}</dd>'
        f'<dt>Altitude at peak brightness</dt><dd>{_measure(get("alt"), "km", 1)}</dd>'
        f'<dt>Speed from velocity components</dt><dd>{_measure(get("component_speed"), "km/s", 1)}</dd>'
        f'<dt>Peak-brightness location</dt><dd>{coords_html}</dd>'
    )

    score = get("iforest_score")
    score_html = _measure(score, "", 4)
    detectors = (
        f'<dt>IQR baseline, energy only</dt><dd>{_baseline_cell(assessment)}</dd>'
        f'<dt>Isolation Forest</dt><dd>{_forest_cell(assessment)}</dd>'
        f'<dt>Isolation Forest score</dt><dd>{score_html}</dd>'
        f'<dt>Agent reading</dt><dd>{esc(str(assessment.get("decision_label", "Unavailable")))}</dd>'
    )
    score_note = (
        " Lower Isolation Forest scores look more unusual to the model."
        if not _is_missing(score)
        else ""
    )

    return (
        '<article class="mw-sheet">'
        f'<div class="mw-sheet-head">{date_html}{chip}</div>'
        '<div class="mw-sheet-grid">'
        f'<section><div class="mw-h3" role="heading" aria-level="3">Reported measurements</div><dl class="mw-rows">{measurements}</dl></section>'
        f'<section><div class="mw-h3" role="heading" aria-level="3">Saved detector results</div><dl class="mw-rows">{detectors}</dl></section>'
        '</div>'
        '<p class="mw-sheet-note">The location is where the fireball was brightest, not an impact site. '
        f'A missing value means the source did not report it; it is never treated as zero.{esc(score_note)}</p>'
        '</article>'
    )


# ---------------------------------------------------------------------------
# Plotly
# ---------------------------------------------------------------------------

def _build_template() -> go.layout.Template:
    axis = dict(
        gridcolor="rgba(124,134,179,0.16)",
        linecolor="rgba(124,134,179,0.45)",
        zeroline=False,
        ticks="outside",
        tickcolor="rgba(124,134,179,0.45)",
        tickfont=dict(size=12, color=DIM),
        title=dict(font=dict(size=12.5, color=DIM)),
    )
    layout = go.Layout(
        font=dict(family=PLOT_FONT, color=TEXT, size=13),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        colorway=[TEXT, DIM, FAINT, "#8FA0E0"],
        xaxis=axis,
        yaxis=axis,
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=12, color=DIM)),
        hoverlabel=dict(
            bgcolor=DECK_2,
            bordercolor=LINE,
            font=dict(family=PLOT_FONT, size=13, color=TEXT),
            align="left",
        ),
        margin=dict(l=8, r=8, t=16, b=8),
        title=dict(font=dict(family=PLOT_DISPLAY_FONT, size=16, color=TEXT)),
    )
    return go.layout.Template(layout=layout)


TEMPLATE = _build_template()
PLOT_CONFIG = {"displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d"]}


def _new_fig() -> go.Figure:
    return go.Figure(layout=go.Layout(template=TEMPLATE))


def _marker(status: Any, size: Any, opacity: float = 0.92) -> dict[str, Any]:
    color = status_color(status)
    if is_hollow(status):
        return dict(size=size, color="rgba(0,0,0,0)", opacity=0.95, line=dict(color=color, width=1.7))
    return dict(size=size, color=color, opacity=opacity, line=dict(color="rgba(18,26,51,0.9)", width=0.6))


def _column(frame: pd.DataFrame, name: str) -> pd.Series:
    if name in frame.columns:
        return frame[name]
    return pd.Series(np.nan, index=frame.index, dtype="float64")


def _hover_texts(frame: pd.DataFrame) -> list[str]:
    def val(value: Any, unit: str, digits: int | None = None) -> str:
        text = fmt_amount(value, digits)
        return f"{text} {unit}".strip() if text is not None else "not reported"

    out = []
    for ts, energy, impact, alt, speed, status in zip(
        _column(frame, "date"),
        _column(frame, "energy"),
        _column(frame, "impact-e"),
        _column(frame, "alt"),
        _column(frame, "component_speed"),
        _column(frame, "review_status"),
    ):
        out.append(
            f"<b>{esc(fmt_stamp(ts))}</b><br>"
            f"Energy: {val(energy, '×10¹⁰ J')}<br>"
            f"Impact energy: {val(impact, 'kt')}<br>"
            f"Altitude: {val(alt, 'km', 1)}<br>"
            f"Speed: {val(speed, 'km/s', 1)}<br>"
            f"{esc(str(status))}"
        )
    return out


def _log_ticks(low: float, high: float) -> tuple[list[float], list[str]]:
    start = math.floor(math.log10(low))
    stop = math.ceil(math.log10(high))
    values = [10.0 ** k for k in range(start, stop + 1)]
    labels = [f"{v:,.0f}" if v >= 1 else f"{v:g}" for v in values]
    return values, labels


def timeline_figure(frame: pd.DataFrame) -> go.Figure | None:
    """Hero chart: every record by date (x) and reported energy (y, log)."""
    data = frame.dropna(subset=["date", "energy"])
    data = data[data["energy"] > 0].copy()
    if data.empty:
        return None
    data["_hover"] = _hover_texts(data)
    fig = _new_fig()
    for status in ordered_statuses(data["review_status"]):
        sub = data[data["review_status"].astype(str) == status]
        fig.add_trace(
            go.Scatter(
                x=sub["date"],
                y=sub["energy"],
                mode="markers",
                name=status,
                text=sub["_hover"],
                hovertemplate="%{text}<extra></extra>",
                marker=_marker(status, 8),
            )
        )

    top = data.loc[data["energy"].idxmax()]
    span_start, span_end = data["date"].min(), data["date"].max()
    span = (span_end - span_start).total_seconds()
    fraction = (top["date"] - span_start).total_seconds() / span if span > 0 else 0.5
    to_left = fraction > 0.6
    fig.add_annotation(
        x=top["date"].strftime("%Y-%m-%d %H:%M:%S"),
        y=math.log10(float(top["energy"])),
        text=f"Highest energy in view: {fmt_amount(top['energy'])} ×10¹⁰ J, {fmt_day(top['date'])}",
        showarrow=True,
        arrowhead=0,
        arrowwidth=1,
        arrowcolor=FAINT,
        ax=-46 if to_left else 46,
        ay=6,
        xanchor="right" if to_left else "left",
        yanchor="middle",
        font=dict(size=12, color=DIM),
    )

    tick_values, tick_text = _log_ticks(float(data["energy"].min()), float(data["energy"].max()))
    fig.update_layout(
        height=470,
        hovermode="closest",
        margin=dict(l=8, r=8, t=24, b=8),
        legend=dict(orientation="h", x=0, y=-0.12, yanchor="top"),
        xaxis=dict(title=dict(text=""), showgrid=False),
        yaxis=dict(
            type="log",
            tickvals=tick_values,
            ticktext=tick_text,
            title=dict(text="Reported energy (×10¹⁰ J), log scale"),
        ),
    )
    return fig


def energy_histogram_figure(frame: pd.DataFrame) -> go.Figure | None:
    """Quarter-decade bins so the bars match the logarithmic idea of the axis."""
    energy = frame["energy"].dropna()
    energy = energy[energy > 0]
    if energy.empty:
        return None
    logs = np.log10(energy.to_numpy(dtype=float))
    step = 0.25
    low = math.floor(logs.min() / step) * step
    high = max(math.ceil(logs.max() / step) * step, low + step)
    edges = np.arange(low, high + step / 2, step)
    counts, _ = np.histogram(logs, bins=edges)
    centers = edges[:-1] + step / 2
    labels = [
        f"{fmt_amount(10 ** a)} to {fmt_amount(10 ** b)} ×10¹⁰ J"
        for a, b in zip(edges[:-1], edges[1:])
    ]
    fig = _new_fig()
    fig.add_trace(
        go.Bar(
            x=centers,
            y=counts,
            width=step * 0.9,
            customdata=labels,
            marker=dict(color=DIM, line=dict(width=0)),
            hovertemplate="%{customdata}<br>%{y} records<extra></extra>",
        )
    )
    ticks = list(range(math.ceil(low), math.floor(high) + 1))
    fig.update_layout(
        height=300,
        bargap=0.05,
        xaxis=dict(
            tickvals=ticks,
            ticktext=[f"{10.0 ** k:,.0f}" if k >= 0 else f"{10.0 ** k:g}" for k in ticks],
            title=dict(text="Reported energy (×10¹⁰ J), log scale"),
            showgrid=False,
        ),
        yaxis=dict(title=dict(text="Records")),
    )
    return fig


def _size_from_energy(energy: pd.Series) -> np.ndarray:
    values = np.clip(energy.to_numpy(dtype=float), 0.01, None)
    return np.clip(5 + 3 * np.log10(values / 0.1), 5, 22)


def _style_geo(fig: go.Figure, **extra: Any) -> None:
    fig.update_geos(
        showland=True,
        landcolor=LAND,
        showocean=True,
        oceancolor=OCEAN,
        showlakes=False,
        showcountries=True,
        countrycolor=LINE,
        showcoastlines=True,
        coastlinecolor="#4A5A9C",
        coastlinewidth=0.6,
        showframe=False,
        bgcolor="rgba(0,0,0,0)",
        lonaxis_showgrid=True,
        lonaxis_gridcolor="rgba(124,134,179,0.18)",
        lonaxis_dtick=30,
        lataxis_showgrid=True,
        lataxis_gridcolor="rgba(124,134,179,0.18)",
        lataxis_dtick=30,
        **extra,
    )


def map_figure(frame: pd.DataFrame) -> go.Figure | None:
    rows = frame.dropna(subset=["map_latitude", "map_longitude"]).copy()
    if rows.empty:
        return None
    rows["_hover"] = _hover_texts(rows)
    fig = _new_fig()
    for status in ordered_statuses(rows["review_status"]):
        sub = rows[rows["review_status"].astype(str) == status]
        sizes = _size_from_energy(sub["energy"]) if "energy" in sub.columns else 8
        fig.add_trace(
            go.Scattergeo(
                lat=sub["map_latitude"],
                lon=sub["map_longitude"],
                mode="markers",
                name=status,
                text=sub["_hover"],
                hovertemplate="%{text}<extra></extra>",
                marker=_marker(status, sizes, opacity=0.85),
            )
        )
    _style_geo(fig, projection_type="natural earth")
    fig.update_layout(
        height=560,
        margin=dict(l=0, r=0, t=0, b=0),
        legend=dict(orientation="h", x=0, y=-0.02, yanchor="top"),
    )
    return fig


def locator_figure(lat: float, lon: float, status: Any) -> go.Figure:
    """A small globe centred on one record."""
    fig = _new_fig()
    fig.add_trace(
        go.Scattergeo(
            lat=[lat],
            lon=[lon],
            mode="markers",
            marker=_marker(status, 14, opacity=1.0),
            hoverinfo="skip",
            showlegend=False,
        )
    )
    _style_geo(
        fig,
        projection_type="orthographic",
        projection_rotation=dict(lon=lon, lat=lat),
    )
    fig.update_layout(height=300, margin=dict(l=0, r=0, t=0, b=0))
    return fig


def outcome_figure(outcomes: pd.DataFrame) -> go.Figure:
    """Pairwise detector outcomes, coloured by the status each outcome corresponds to."""
    names = outcomes["Pairwise outcome"].astype(str).tolist()
    counts = outcomes["Comparable records"].astype(int).tolist()
    fig = _new_fig()
    fig.add_trace(
        go.Bar(
            y=names,
            x=counts,
            orientation="h",
            marker=dict(color=[status_color(n) for n in names]),
            text=[f"{c:,}" for c in counts],
            textposition="outside",
            textfont=dict(color=TEXT),
            cliponaxis=False,
            hovertemplate="%{y}<br>%{x:,} comparable records<extra></extra>",
        )
    )
    fig.update_layout(
        height=max(240, 62 * len(names)),
        margin=dict(l=8, r=40, t=8, b=8),
        xaxis=dict(title=dict(text="Comparable records"), showgrid=True),
        yaxis=dict(autorange="reversed", showgrid=False, ticks=""),
    )
    return fig


def sensitivity_figure(summary: pd.DataFrame) -> go.Figure:
    x_col, y_col = "Score threshold setting (%)", "Records flagged"
    fig = _new_fig()
    fig.add_trace(
        go.Scatter(
            x=summary[x_col],
            y=summary[y_col],
            mode="lines+markers",
            line=dict(color=DIM, width=2),
            marker=dict(size=9, color=SKY, line=dict(color=TEXT, width=2)),
            hovertemplate="%{x}% cutoff<br>%{y:,} records selected<extra></extra>",
            showlegend=False,
        )
    )
    reference = summary[summary[x_col] == 5]
    if not reference.empty:
        fig.add_trace(
            go.Scatter(
                x=reference[x_col],
                y=reference[y_col],
                mode="markers",
                name="5% reference setting",
                marker=dict(size=13, color=TEXT),
                hovertemplate="5% reference<br>%{y:,} records selected<extra></extra>",
            )
        )
    fig.update_layout(
        height=340,
        legend=dict(orientation="h", x=0, y=1.12, yanchor="bottom"),
        xaxis=dict(title=dict(text="Contamination-style score threshold (%)")),
        yaxis=dict(title=dict(text="Records selected for review"), rangemode="tozero"),
    )
    return fig


def completeness_figure(completeness: pd.DataFrame) -> go.Figure:
    data = completeness.sort_values("Missing (%)", ascending=False)
    fig = _new_fig()
    fig.add_trace(
        go.Bar(
            y=data["Field"],
            x=data["Missing (%)"],
            orientation="h",
            marker=dict(color=DIM),
            text=[f"{v:.1f}%" for v in data["Missing (%)"]],
            textposition="outside",
            textfont=dict(color=TEXT),
            cliponaxis=False,
            hovertemplate="%{y}<br>%{x:.1f}% missing<extra></extra>",
        )
    )
    fig.update_layout(
        height=max(340, 34 * len(data) + 60),
        margin=dict(l=8, r=48, t=8, b=8),
        xaxis=dict(range=[0, 108], title=dict(text="Missing values (%)")),
        yaxis=dict(autorange="reversed", showgrid=False, ticks=""),
    )
    return fig



def sound_console_html() -> str:
    # Browser-native Web Audio keeps the theme lightweight and asset-free.
    return '''
<style>
:root{color-scheme:dark}*{box-sizing:border-box}html,body{background:#0b1226}body{margin:0;font-family:Inter,system-ui,sans-serif;color:#eef0ff}.mw-console{position:relative;display:flex;align-items:center;gap:1rem;min-height:68px;padding:.75rem 1rem;border:1px solid rgba(124,134,179,.25);border-radius:18px;background:linear-gradient(135deg,rgba(18,29,62,.86),rgba(10,17,38,.72));overflow:hidden}.mw-console:before{content:"";position:absolute;inset:0;background:radial-gradient(circle at 88% 30%,rgba(249,209,125,.14),transparent 13rem);pointer-events:none}.mw-console__orb{position:relative;width:34px;height:34px;border-radius:50%;border:1px solid rgba(249,209,125,.7);box-shadow:0 0 18px rgba(249,209,125,.35),inset 0 0 14px rgba(199,155,255,.25);flex:none}.mw-console__orb:after{content:"";position:absolute;inset:7px;border-radius:50%;background:#f9d17d;box-shadow:0 0 14px #f9d17d}.mw-console__copy{min-width:120px;flex:1}.mw-console__eyebrow{display:block;color:#f9d17d;font-size:.62rem;font-weight:800;letter-spacing:.16em;text-transform:uppercase}.mw-console__status{display:block;margin-top:.2rem;color:#9faad1;font-size:.76rem}.mw-console__actions{display:flex;flex-wrap:wrap;justify-content:flex-end;gap:.45rem}.mw-console button{appearance:none;border:1px solid rgba(154,168,221,.35);border-radius:999px;background:rgba(19,30,64,.68);color:#dce2ff;padding:.48rem .72rem;font-size:.7rem;font-weight:750;letter-spacing:.06em;cursor:pointer;transition:background .2s ease,border-color .2s ease,transform .2s ease}.mw-console button:hover,.mw-console button:focus-visible{background:rgba(193,204,255,.14);border-color:#d9e0ff;transform:translateY(-1px);outline:none}.mw-console button[data-on="true"]{border-color:#f9d17d;color:#fff2c7;box-shadow:0 0 14px rgba(249,209,125,.14)}.mw-console button[data-on="true"]:before{content:"● ";color:#f9d17d}.mw-console__ping{border-color:rgba(249,209,125,.65)!important}.mw-console__trace{position:absolute;right:1rem;bottom:.5rem;width:100px;height:1px;background:linear-gradient(90deg,transparent,#f9d17d,transparent);opacity:.55;animation:mw-trace 2.8s ease-in-out infinite}.mw-console.reduced .mw-console__trace{animation:none;opacity:.25}@keyframes mw-trace{0%,100%{transform:translateX(-35px);opacity:.1}50%{transform:translateX(25px);opacity:.7}}@media(max-width:620px){.mw-console{align-items:flex-start}.mw-console__actions{justify-content:flex-start}.mw-console__copy{min-width:0}.mw-console{flex-wrap:wrap}.mw-console__actions{width:100%}}
</style>
<div class="mw-console" id="mw-console" aria-label="Mission sound and motion controls">
  <div class="mw-console__orb" aria-hidden="true"></div>
  <div class="mw-console__copy"><span class="mw-console__eyebrow">Mission controls</span><span class="mw-console__status" id="mw-console-status" aria-live="polite">Sound is off — tap a control to begin.</span></div>
  <div class="mw-console__actions"><button type="button" id="mw-ambient" data-on="false" aria-pressed="false">Ambient hum</button><button type="button" id="mw-fx" data-on="false" aria-pressed="false">Signal FX</button><button type="button" id="mw-motion" data-on="false" aria-pressed="false">Calm motion</button><button type="button" class="mw-console__ping" id="mw-ping">Ping archive</button></div><span class="mw-console__trace" aria-hidden="true"></span>
</div>
<script>
(function(){
  const root=document.getElementById('mw-console'), status=document.getElementById('mw-console-status');
  const buttons={ambient:document.getElementById('mw-ambient'),fx:document.getElementById('mw-fx'),motion:document.getElementById('mw-motion')};
  let ctx=null,ambient=null,ambientGain=null;
  const prefs=JSON.parse(localStorage.getItem('mw-mission-controls')||'{}');
  function audio(){if(!ctx){ctx=new (window.AudioContext||window.webkitAudioContext)()}if(ctx.state==='suspended'){ctx.resume()}return ctx}
  function tone(freq=520,duration=.12,type='sine',volume=.045){if(prefs.fx===false&&type!=='ambient')return;const c=audio(),o=c.createOscillator(),g=c.createGain();o.type=type;o.frequency.setValueAtTime(freq,c.currentTime);o.frequency.exponentialRampToValueAtTime(Math.max(80,freq*.62),c.currentTime+duration);g.gain.setValueAtTime(.0001,c.currentTime);g.gain.exponentialRampToValueAtTime(volume,c.currentTime+.012);g.gain.exponentialRampToValueAtTime(.0001,c.currentTime+duration);o.connect(g).connect(c.destination);o.start();o.stop(c.currentTime+duration+.02)}
  function save(){localStorage.setItem('mw-mission-controls',JSON.stringify(prefs))}
  function render(){Object.entries(buttons).forEach(([key,b])=>{const on=!!prefs[key];b.dataset.on=String(on);b.setAttribute('aria-pressed',String(on))});root.classList.toggle('reduced',!!prefs.motion);status.textContent=prefs.ambient?'Ambient hum online · archive ready':prefs.fx?'Signal FX armed · archive ready':'Sound is off — tap a control to begin.'}
  buttons.fx.addEventListener('click',()=>{prefs.fx=!prefs.fx;save();render();if(prefs.fx)tone(640,.16,'triangle',.06)});
  buttons.ambient.addEventListener('click',()=>{prefs.ambient=!prefs.ambient;save();if(prefs.ambient){const c=audio();ambient=c.createOscillator();ambientGain=c.createGain();ambient.type='sine';ambient.frequency.value=72;ambientGain.gain.value=.012;ambient.connect(ambientGain).connect(c.destination);ambient.start();tone(220,.22,'sine',.035)}else if(ambient){ambient.stop();ambient=null}render()});
  buttons.motion.addEventListener('click',()=>{prefs.motion=!prefs.motion;save();render();if(prefs.fx)tone(prefs.motion?260:520,.1,'sine',.04)});
  document.getElementById('mw-ping').addEventListener('click',()=>{prefs.fx=true;save();render();tone(880,.08,'square',.055);setTimeout(()=>tone(1320,.16,'triangle',.045),95);status.textContent='Archive ping received · hover and explore';});
  root.querySelectorAll('button').forEach(b=>b.addEventListener('mouseenter',()=>{if(prefs.fx)tone(360,.045,'sine',.02)}));
  render();
})();
</script>'''
