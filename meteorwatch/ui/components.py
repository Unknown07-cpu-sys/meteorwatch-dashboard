"""Small HTML components: status key, coverage bar, callouts, record sheet.

Every function returns one compact HTML string with no blank lines, so Streamlit's
markdown renderer keeps it as a single block. Text that comes from the data is escaped.
"""
from __future__ import annotations

from typing import Any, Sequence

from meteorwatch.ui.design import (
    STATUS_STYLES,
    TEXT,
    esc,
    fmt_amount,
    fmt_coords,
    is_hollow,
    is_missing,
    status_color,
)


def _measure(value: Any, unit: str = "", digits: int | None = None) -> str:
    text = fmt_amount(value, digits)
    if text is None:
        return '<span class="mw-na">Not reported</span>'
    unit_html = f'<span class="mw-unit">{esc(unit)}</span>' if unit else ""
    return f"{esc(text)}{unit_html}"


# ---------------------------------------------------------------------------
# HTML components (single-line-safe: no blank lines, no indented blocks)
# ---------------------------------------------------------------------------

def _dot(color: str, hollow: bool) -> str:
    kind = "hollow" if hollow else "solid"
    style = f"border-color:{color}" if hollow else f"background:{color};border-color:{color}"
    return f'<span class="mw-dot mw-dot--{kind}" style="{style}" aria-hidden="true"></span>'


def status_dot(status: Any) -> str:
    return _dot(status_color(status), is_hollow(status))


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
    status_text = "Status unavailable" if is_missing(status) else str(status)
    chip_cls = "mw-chip mw-chip--hollow" if is_hollow(status_text) else "mw-chip"
    chip = (
        f'<span class="{chip_cls}" style="border-color:{status_color(status_text)}">'
        f'{status_dot(status_text)}{esc(status_text)}</span>'
    )

    ts = get("date")
    if is_missing(ts):
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
        if not is_missing(score)
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
