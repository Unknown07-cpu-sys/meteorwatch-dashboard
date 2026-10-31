"""METEORWATCH interface design system.

    design      tokens, status encoding, number/date formatting   (pure Python)
    theme       the page stylesheet                               (pure Python)
    components  small HTML components: status key, coverage bar, record sheet
    story       scroll-story sections: hero sky, statement, chapter heads, pinned scene
    charts      Plotly figures and the shared dark template       (needs plotly)

``from meteorwatch import ui`` exposes every public name in one place. Names are loaded
on first use, so importing ``meteorwatch.ui.design`` never requires Plotly.
"""
from __future__ import annotations

import importlib
from typing import Any

_EXPORTS: dict[str, tuple[str, ...]] = {
    "design": (
        "BODY_FONT_CSS", "DECK", "DECK_2", "DIM", "DISPLAY_FONT_CSS", "FAINT", "LAND", "LINE",
        "OCEAN", "PLOT_DISPLAY_FONT", "PLOT_FONT", "SKY", "STATUS_RANK", "STATUS_STYLES", "TEXT",
        "classify_status", "esc", "fmt_amount", "fmt_coords", "fmt_day", "fmt_stamp",
        "is_hollow", "is_missing", "ordered_statuses", "status_color",
    ),
    "theme": ("theme_css",),
    "components": (
        "callout_html", "coverage_html", "definitions_html", "empty_state_html", "inview_html",
        "mark_legend_html", "record_sheet_html", "section_html", "side_title_html",
        "status_dot", "status_key_html",
    ),
    "story": (
        "chapter_head_html", "closing_html", "detectors_story_html", "hero_html",
        "sky_dots_html", "statement_html",
    ),
    "charts": (
        "PLOT_CONFIG", "TEMPLATE", "completeness_figure", "energy_histogram_figure",
        "locator_figure", "map_figure", "outcome_figure", "sensitivity_figure", "timeline_figure",
    ),
}
_OWNER = {name: module for module, names in _EXPORTS.items() for name in names}
__all__ = sorted(_OWNER)


def __getattr__(name: str) -> Any:
    module = _OWNER.get(name)
    if module is None:
        raise AttributeError(f"module 'meteorwatch.ui' has no attribute {name!r}")
    value = getattr(importlib.import_module(f"meteorwatch.ui.{module}"), name)
    globals()[name] = value
    return value
