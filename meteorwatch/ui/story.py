"""Sections of the scroll story: hero, statement, chapter heads, pinned scene, closing.

The hero sky is not decoration. Every dot is one record from the catalogue:
left to right is time, higher is more reported energy, and colour is review status.
All numbers on the page come from the loaded data.
"""
from __future__ import annotations

import math
from typing import Sequence

import numpy as np
import pandas as pd

from meteorwatch.ui.design import classify_status, esc, fmt_day, is_missing

_STAR_CLASS = {
    "both": "k-both",
    "baseline": "k-base",
    "forest": "k-forest",
    "baseline_unassessed": "k-baseun",
    "quiet": "k-quiet",
    "unassessed": "k-unass",
    "unknown": "k-unk",
}
_FLAGGED = {"both", "baseline", "forest"}
# Flagged records are drawn last so they sit on top of the crowd.
_DRAW_ORDER = {"unknown": 0, "unassessed": 1, "quiet": 2, "baseline_unassessed": 3, "baseline": 4, "forest": 5, "both": 6}


def sky_dots_html(frame: pd.DataFrame) -> str:
    """One <i> per record, placed by date (x) and log energy (y, higher = more energy)."""
    data = frame.dropna(subset=["date", "energy"])
    data = data[data["energy"] > 0]
    if data.empty:
        return ""
    seconds = (data["date"] - data["date"].min()).dt.total_seconds().to_numpy(dtype=float)
    span = seconds.max() if seconds.max() > 0 else 1.0
    logs = np.log10(data["energy"].to_numpy(dtype=float))
    low, high = logs.min(), logs.max()
    scale = (high - low) if high > low else 1.0
    ranks = pd.Series(logs).rank(pct=True).to_numpy()

    dots = []
    for status, sec, log_e, rank in zip(data["review_status"], seconds, logs, ranks):
        key = classify_status(status)
        x = 2.0 + 96.0 * sec / span
        y = 8.0 + 78.0 * (1.0 - (log_e - low) / scale)
        if rank >= 0.985:
            size = "s4"
        elif rank >= 0.88:
            size = "s3"
        elif rank >= 0.5 or key in _FLAGGED:
            size = "s2"
        else:
            size = "s1"
        dots.append((_DRAW_ORDER[key], f'<i class="{_STAR_CLASS[key]} {size}" style="left:{x:.2f}%;top:{y:.2f}%"></i>'))
    dots.sort(key=lambda pair: pair[0])
    return "".join(markup for _, markup in dots)


def _count(value: int, label: str) -> str:
    """A number that counts up where the browser can animate it, and reads correctly everywhere."""
    return (
        f'<span class="mw-count" style="--mw-target:{int(value)}" aria-hidden="true"></span>'
        f'<span class="mw-sr">{int(value):,} {esc(label)}</span>'
    )


def hero_html(frame: pd.DataFrame, years: int, flagged_any: int) -> str:
    total = len(frame)
    first = frame["date"].min()
    last = frame["date"].max()
    if is_missing(first) or is_missing(last):
        span_text = "across the whole catalogue"
    else:
        span_text = f"from {fmt_day(first)} to {fmt_day(last)}"
    return (
        '<section class="mw-hero" id="top">'
        '<div class="mw-sky-wrap" aria-hidden="true"><div class="mw-sky">'
        f'{sky_dots_html(frame)}'
        '</div></div>'
        '<div class="mw-meteors" aria-hidden="true"><span></span><span></span><span></span><span></span><span></span><span></span></div>'
        '<div class="mw-hero-inner">'
        '<p class="mw-kicker">A review desk for historical fireball records</p>'
        '<div class="mw-hero-title" role="heading" aria-level="1"><span>METEOR</span><span class="mw-out">WATCH</span></div>'
        f'<p class="mw-hero-lede">Every star behind this title is a real fireball in the NASA/JPL catalogue, {esc(span_text)}.</p>'
        '<p class="mw-hero-key">Left to right is time. Higher means more reported energy. '
        'Gold, orange and violet stars were flagged for review. Teal stars were not flagged. '
        'Faint stars were not assessed by the Isolation Forest.</p>'
        '<dl class="mw-hero-stats">'
        f'<div><dt>years of records</dt><dd>{_count(years, "years of records")}</dd></div>'
        f'<div><dt>fireballs recorded</dt><dd>{total:,}</dd></div>'
        f'<div><dt>flagged by at least one method</dt><dd>{_count(flagged_any, "flagged by at least one method")}</dd></div>'
        '</dl>'
        '<p class="mw-scrollcue">Scroll<span></span></p>'
        '</div>'
        '</section>'
    )


def statement_html(kicker: str, text: str) -> str:
    """A large paragraph whose words brighten as they scroll into view."""
    words = "".join(f'<span class="w">{esc(word)}</span> ' for word in text.split())
    return (
        '<section class="mw-statement">'
        f'<p class="mw-kicker">{esc(kicker)}</p>'
        f'<p>{words.rstrip()}</p>'
        '</section>'
    )


def chapter_head_html(number: str, title_lines: Sequence[str], intro: str, outline_last: bool = True) -> str:
    """Big numbered chapter opener. ``intro`` is plain text and is escaped."""
    lines = []
    for index, line in enumerate(title_lines):
        outlined = outline_last and index == len(title_lines) - 1 and len(title_lines) > 1
        cls = ' class="mw-out"' if outlined else ""
        lines.append(f"<span{cls}>{esc(line)}</span>")
    return (
        '<div class="mw-chapter-head">'
        f'<p class="mw-chapter-no">{esc(number)}</p>'
        f'<div class="mw-chapter-title" role="heading" aria-level="2">{"".join(lines)}</div>'
        f'<p class="mw-chapter-intro">{esc(intro)}</p>'
        '</div>'
    )


def detectors_story_html(
    assessed: int,
    total: int,
    baseline_flags: int,
    forest_flags: int,
    flagged_both: int,
) -> str:
    """Pinned two-column scene: the title stays put while three steps scroll past."""
    pct = (assessed / total * 100) if total else 0.0
    steps = [
        (
            "1",
            "A transparent baseline",
            f"The <strong>IQR rule</strong> looks only at reported energy, on a log scale. A record outside "
            f"the fences is flagged. It is simple enough to check by hand, and it flagged "
            f"<strong>{baseline_flags:,}</strong> records.",
        ),
        (
            "2",
            "A model that sees more",
            f"The <strong>Isolation Forest</strong> also looks at altitude and speed, so it can only assess records "
            f"that report all of them: <strong>{assessed:,} of {total:,} ({pct:.1f}%)</strong>. "
            f"It flagged <strong>{forest_flags:,}</strong>. A record it could not assess is not a record it cleared.",
        ),
        (
            "3",
            "A prompt, not a verdict",
            f"<strong>{flagged_both:,}</strong> records were flagged by both methods. There are no independently "
            "verified anomaly labels here, so a flag only tells a person where to look first. "
            "It is never a hazard rating.",
        ),
    ]
    cards = "".join(
        f'<div class="mw-step"><p class="mw-step-no mw-out">{n}</p>'
        f'<div class="mw-step-title" role="heading" aria-level="3">{esc(title)}</div><p>{body}</p></div>'
        for n, title, body in steps
    )
    return (
        '<section class="mw-pin">'
        '<div class="mw-pin-left">'
        '<p class="mw-chapter-no">03</p>'
        '<div class="mw-chapter-title" role="heading" aria-level="2"><span>Two ways to</span><span class="mw-out">look closer</span></div>'
        '</div>'
        f'<div class="mw-pin-right">{cards}</div>'
        '</section>'
    )


def closing_html() -> str:
    return (
        '<section class="mw-closing">'
        '<div class="mw-chapter-title" role="heading" aria-level="2"><span>A flag is a prompt,</span><span class="mw-out">not a verdict.</span></div>'
        '<p class="mw-fine">METEORWATCH is a student research prototype for historical analysis. '
        'It does not predict future impacts or issue operational warnings. '
        'Measurements come from the NASA/JPL Fireball Data API; flags are saved statistical results, '
        'not verified anomaly labels.</p>'
        '</section>'
    )
