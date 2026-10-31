"""Tests for the METEORWATCH visual design helpers.

These check the rules the design depends on (for example, that "not assessed" never looks
like "not flagged"), that HTML is escaped, and that missing values are never shown as zero.
They do not test how the page looks in a browser.
"""
from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from meteorwatch import ui
from meteorwatch.agent import assess_event
from meteorwatch.records import event_labels, records_table, sort_events

try:
    import plotly  # noqa: F401
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False


ALL_SAVED_STATUSES = [
    "Flagged by both methods",
    "IQR baseline only",
    "Isolation Forest only",
    "Baseline flagged; ML not assessed",
    "Not flagged by either method",
    "ML not assessed; baseline did not flag",
]


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
            ui.status_key_html([("Flagged by both methods", 2), ("Not flagged by either method", 0)], 2, 10),
            ui.coverage_html(3, 6, 1, 10, 2, 1),
            ui.section_html("Title", "Intro"),
            ui.callout_html("Body", lead="Lead."),
            ui.empty_state_html("Nothing here", "Try again."),
            ui.mark_legend_html(),
            ui.closing_html(),
            ui.statement_html("The record", "Some words to reveal"),
            ui.chapter_head_html("01", ["Line one", "Line two"], "An intro <b>with markup</b>"),
            ui.detectors_story_html(360, 1074, 44, 18, 9),
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


@unittest.skipUnless(HAS_PLOTLY, "plotly is not installed")
class FigureTests(unittest.TestCase):
    def test_empty_inputs_return_none_instead_of_raising(self):
        empty = pd.DataFrame(columns=["date", "energy", "review_status", "map_latitude", "map_longitude"])
        self.assertIsNone(ui.timeline_figure(empty))
        self.assertIsNone(ui.energy_histogram_figure(empty))
        self.assertIsNone(ui.map_figure(empty))


SAMPLE = pd.DataFrame(
    {
        "date": pd.to_datetime(["1990-01-01", "2000-06-01", "2010-03-01", "2020-12-31", None]),
        "energy": [1.0, 10.0, 100.0, 1000.0, 5.0],
        "review_status": [
            "Not flagged by either method",
            "IQR baseline only",
            "Flagged by both methods",
            "ML not assessed; baseline did not flag",
            "Isolation Forest only",
        ],
        "baseline_flag": pd.array([False, True, True, False, False], dtype="boolean"),
        "iforest_flag": pd.array([False, False, True, pd.NA, True], dtype="boolean"),
        "ml_assessed": pd.array([True, True, True, False, True], dtype="boolean"),
        "iforest_score": [0.1, 0.05, -0.2, np.nan, -0.1],
    }
)


class StoryTests(unittest.TestCase):
    def test_every_dated_record_becomes_one_star(self):
        dots = ui.sky_dots_html(SAMPLE)
        self.assertEqual(dots.count("<i "), 4)  # the record with no date cannot be placed

    def _positions(self, html_text):
        import re
        return [(float(x), float(y)) for x, y in re.findall(r"left:([\d.]+)%;top:([\d.]+)%", html_text)]

    def test_stars_stay_inside_the_sky(self):
        for x, y in self._positions(ui.sky_dots_html(SAMPLE)):
            self.assertTrue(0 <= x <= 100 and 0 <= y <= 100, (x, y))

    def test_later_is_further_right_and_higher_energy_is_higher_up(self):
        two = pd.DataFrame(
            {
                "date": pd.to_datetime(["2000-01-01", "2010-01-01"]),
                "energy": [1.0, 1000.0],
                "review_status": ["Not flagged by either method"] * 2,
            }
        )
        (x_old, y_old), (x_new, y_new) = self._positions(ui.sky_dots_html(two))
        self.assertLess(x_old, x_new)
        self.assertLess(y_new, y_old)  # smaller top % means higher on the page

    def test_status_decides_the_colour_class(self):
        dots = ui.sky_dots_html(SAMPLE)
        for expected in ("k-quiet", "k-base", "k-both", "k-unass"):  # the Isolation Forest row has no date, so it is not drawn
            self.assertIn(expected, dots)
        css = ui.theme_css()
        self.assertIn(".mw-sky i.k-both{background:#FFD97A;box-shadow", css)  # flagged stars glow
        self.assertNotIn(".mw-sky i.k-unass{background:#", css)  # unassessed stars are translucent, not solid

    def test_hero_reports_numbers_from_the_data(self):
        hero = ui.hero_html(SAMPLE, years=30, flagged_any=3)
        self.assertIn("--mw-target:30", hero)
        self.assertIn("--mw-target:3", hero)
        self.assertIn(">5<", hero)  # total records, shown as plain text
        self.assertIn("1 Jan 1990", hero)

    def test_statement_wraps_every_word_and_escapes_text(self):
        html_text = ui.statement_html("Kicker", "One <two> three")
        self.assertEqual(html_text.count('class="w"'), 3)
        self.assertIn("&lt;two&gt;", html_text)

    def test_detector_story_states_coverage_and_never_calls_a_flag_a_hazard(self):
        scene = ui.detectors_story_html(360, 1074, 44, 18, 9)
        self.assertIn("360 of 1,074", scene)
        self.assertIn("never a hazard rating", scene)
        self.assertIn("not a record it cleared", scene)

    def test_theme_contains_motion_guards(self):
        css = ui.theme_css()
        self.assertIn("prefers-reduced-motion:no-preference", css)
        self.assertIn("@supports (animation-timeline:view())", css)


class RecordsTests(unittest.TestCase):
    def test_table_keeps_not_assessed_distinct_from_no_flag(self):
        table = records_table(SAMPLE)
        forest = dict(zip(SAMPLE["review_status"], table["Isolation Forest"]))
        self.assertEqual(forest["ML not assessed; baseline did not flag"], "Not assessed")
        self.assertEqual(forest["Not flagged by either method"], "No flag")
        self.assertEqual(forest["Flagged by both methods"], "Flagged")

    def test_table_baseline_column(self):
        table = records_table(SAMPLE)
        self.assertEqual(list(table["IQR baseline"]), ["No flag", "Flagged", "Flagged", "No flag", "No flag"])

    def test_sorting_puts_flagged_first_and_missing_scores_last(self):
        ordered = sort_events(SAMPLE, "Flagged records first")
        flags = [bool(v) for v in (ordered["baseline_flag"].eq(True) | ordered["iforest_flag"].eq(True)).fillna(False)]
        self.assertTrue(flags[0])
        self.assertEqual(flags, sorted(flags, reverse=True))  # every flagged row comes before every unflagged row
        unusual = sort_events(SAMPLE, "Most unusual ML score")
        self.assertTrue(pd.isna(unusual.iloc[-1]["iforest_score"]))
        self.assertEqual(unusual.iloc[0]["iforest_score"], -0.2)

    def test_labels_cover_every_row_even_without_a_date(self):
        labels = event_labels(SAMPLE)
        self.assertEqual(len(labels), len(SAMPLE))
        self.assertIn("Date not reported", labels[4])


if __name__ == "__main__":
    unittest.main()


@unittest.skipUnless(HAS_PLOTLY, "Plotly is required for chart layout tests")
class PlotlyAxisLayoutTests(unittest.TestCase):
    def test_shared_cartesian_axes_enable_automatic_margins(self):
        from meteorwatch.ui.charts import TEMPLATE

        self.assertTrue(TEMPLATE.layout.xaxis.automargin)
        self.assertTrue(TEMPLATE.layout.yaxis.automargin)

    def test_timeline_reserves_room_for_y_axis_labels(self):
        from meteorwatch.ui.charts import timeline_figure

        frame = pd.DataFrame({
            "date": pd.to_datetime(["2024-01-01", "2024-01-02"]),
            "energy": [1.25, 37500.0],
            "review_status": ["Not flagged by either method", "IQR baseline only"],
            "impact-e": [1.0, 2.0],
            "alt": [30.0, 35.0],
            "component_speed": [20.0, 21.0],
        })
        fig = timeline_figure(frame)
        self.assertIsNotNone(fig)
        self.assertTrue(fig.layout.yaxis.automargin)
        self.assertGreaterEqual(fig.layout.margin.l, 80)

    def test_horizontal_category_charts_enable_axis_automargin(self):
        from meteorwatch.ui.charts import completeness_figure, outcome_figure

        outcomes = pd.DataFrame({
            "Pairwise outcome": ["Baseline flagged; ML not assessed", "Not flagged by either method"],
            "Comparable records": [15, 322],
        })
        completeness = pd.DataFrame({
            "Field": ["Velocity component X", "Reported energy"],
            "Missing (%)": [66.2, 0.0],
        })
        outcome = outcome_figure(outcomes)
        quality = completeness_figure(completeness)
        self.assertTrue(outcome.layout.yaxis.automargin)
        self.assertTrue(quality.layout.yaxis.automargin)
        self.assertGreaterEqual(outcome.layout.margin.l, 180)
        self.assertGreaterEqual(quality.layout.margin.l, 140)
