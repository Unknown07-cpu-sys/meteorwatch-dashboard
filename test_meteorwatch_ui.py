"""Tests for the METEORWATCH visual design helpers.

These check the rules the design depends on (for example, that "not assessed" never looks
like "not flagged"), that HTML is escaped, and that missing values are never shown as zero.
They do not test how the page looks in a browser.
"""
from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from meteorwatch_agent import assess_event

try:
    import meteorwatch_ui as ui
except ImportError:  # plotly is not installed in this environment
    ui = None


ALL_SAVED_STATUSES = [
    "Flagged by both methods",
    "IQR baseline only",
    "Isolation Forest only",
    "Baseline flagged; ML not assessed",
    "Not flagged by either method",
    "ML not assessed; baseline did not flag",
]


@unittest.skipIf(ui is None, "plotly is not installed")
class StatusEncodingTests(unittest.TestCase):
    def test_every_saved_status_is_recognised(self):
        for status in ALL_SAVED_STATUSES:
            self.assertNotEqual(ui.classify_status(status), "unknown", status)

    def test_not_assessed_is_hollow_and_not_flagged_is_filled(self):
        self.assertTrue(ui.is_hollow("ML not assessed; baseline did not flag"))
        self.assertTrue(ui.is_hollow("Baseline flagged; ML not assessed"))
        self.assertFalse(ui.is_hollow("Not flagged by either method"))
        self.assertNotEqual(
            ui.status_color("ML not assessed; baseline did not flag"),
            ui.status_color("Not flagged by either method"),
        )

    def test_flagged_statuses_have_distinct_colours(self):
        colours = {
            ui.status_color(s)
            for s in ["Flagged by both methods", "IQR baseline only", "Isolation Forest only", "Not flagged by either method"]
        }
        self.assertEqual(len(colours), 4)

    def test_missing_or_unrecognised_status_is_unknown_not_quiet(self):
        for value in [None, float("nan"), "", "Something new"]:
            self.assertEqual(ui.classify_status(value), "unknown")

    def test_ordering_is_stable_and_complete(self):
        shuffled = list(reversed(ALL_SAVED_STATUSES)) + [None, float("nan")]
        self.assertEqual(ui.ordered_statuses(shuffled), ALL_SAVED_STATUSES)


@unittest.skipIf(ui is None, "plotly is not installed")
class FormattingTests(unittest.TestCase):
    def test_amounts_adapt_and_missing_stays_missing(self):
        self.assertEqual(ui.fmt_amount(37500), "37,500")
        self.assertEqual(ui.fmt_amount(5.4), "5.40")
        self.assertEqual(ui.fmt_amount(0.079), "0.079")
        self.assertIsNone(ui.fmt_amount(None))
        self.assertIsNone(ui.fmt_amount(float("nan")))
        self.assertIsNone(ui.fmt_amount(float("inf")))

    def test_coordinates_use_compass_letters(self):
        self.assertEqual(ui.fmt_coords(-41.8, -173.1), "41.80° S, 173.10° W")
        self.assertEqual(ui.fmt_coords(54.4, 100.1), "54.40° N, 100.10° E")
        self.assertIsNone(ui.fmt_coords(None, 3))

    def test_dates_do_not_depend_on_platform_strftime_flags(self):
        stamp = pd.Timestamp("2026-10-04 03:14:45")
        self.assertEqual(ui.fmt_day(stamp), "4 Oct 2026")
        self.assertEqual(ui.fmt_stamp(stamp), "4 Oct 2026, 03:14:45 GMT")


@unittest.skipIf(ui is None, "plotly is not installed")
class ComponentTests(unittest.TestCase):
    def _row(self, **overrides):
        row = {
            "date": pd.Timestamp("2026-09-15 11:26:13"),
            "energy": 2.2,
            "impact-e": 0.079,
            "alt": 37.0,
            "component_speed": np.nan,
            "map_latitude": -37.6,
            "map_longitude": -161.6,
            "iforest_score": np.nan,
            "review_status": "ML not assessed; baseline did not flag",
            "baseline_flag": False,
            "ml_assessed": False,
            "iforest_flag": pd.NA,
        }
        row.update(overrides)
        return pd.Series(row)

    def test_record_sheet_marks_missing_values_and_never_shows_zero(self):
        row = self._row()
        sheet = ui.record_sheet_html(row, assess_event(row))
        self.assertIn("Not reported", sheet)
        self.assertIn("Not assessed", sheet)
        self.assertNotIn(">0<", sheet)
        self.assertNotIn(">nan<", sheet.lower())

    def test_record_sheet_escapes_text_from_the_data(self):
        row = self._row(review_status='<script>alert("x")</script>')
        sheet = ui.record_sheet_html(row, assess_event(row))
        self.assertNotIn("<script>", sheet)
        self.assertIn("&lt;script&gt;", sheet)

    def test_record_sheet_handles_a_record_with_no_date_or_location(self):
        row = self._row(date=pd.NaT, map_latitude=np.nan, map_longitude=np.nan)
        sheet = ui.record_sheet_html(row, assess_event(row))
        self.assertIn("Date not reported", sheet)

    def test_html_has_no_blank_lines_that_would_end_a_markdown_html_block(self):
        row = self._row()
        pieces = [
            ui.record_sheet_html(row, assess_event(row)),
            ui.masthead_html("report.csv", 10, pd.Timestamp("1988-04-15"), pd.Timestamp("2026-10-04")),
            ui.status_key_html([("Flagged by both methods", 2), ("Not flagged by either method", 0)], 2, 10),
            ui.coverage_html(3, 6, 1, 10, 2, 1),
            ui.section_html("Title", "Intro"),
            ui.callout_html("Body", lead="Lead."),
            ui.empty_state_html("Nothing here", "Try again."),
            ui.mark_legend_html(),
            ui.footer_html(),
        ]
        for piece in pieces:
            self.assertNotIn("\n\n", piece)
            self.assertFalse(piece.startswith(" "))

    def test_status_key_lists_every_status_including_empty_ones(self):
        html_text = ui.status_key_html([("Flagged by both methods", 2), ("Not flagged by either method", 0)], 2, 10)
        self.assertIn("Flagged by both methods", html_text)
        self.assertIn("Not flagged by either method", html_text)
        self.assertIn("mw-zero", html_text)

    def test_coverage_bar_keeps_unknown_separate_from_not_assessed(self):
        html_text = ui.coverage_html(3, 6, 1, 10, 2, 1)
        self.assertIn("1 have an unknown assessment status", html_text)
        self.assertIn("not the same as", html_text)

    def test_theme_css_has_no_unformatted_placeholders(self):
        css = ui.theme_css()
        self.assertTrue(css.startswith("<style>"))
        self.assertNotIn("%(", css)
        self.assertNotIn("%%", css)


@unittest.skipIf(ui is None, "plotly is not installed")
class FigureTests(unittest.TestCase):
    def test_empty_inputs_return_none_instead_of_raising(self):
        empty = pd.DataFrame(columns=["date", "energy", "review_status", "map_latitude", "map_longitude"])
        self.assertIsNone(ui.timeline_figure(empty))
        self.assertIsNone(ui.energy_histogram_figure(empty))
        self.assertIsNone(ui.map_figure(empty))


if __name__ == "__main__":
    unittest.main()
