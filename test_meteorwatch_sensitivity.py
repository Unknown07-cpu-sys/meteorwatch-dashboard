"""Tests for score-threshold sensitivity analysis (not detector accuracy)."""
import unittest

import pandas as pd

from meteorwatch_sensitivity import (
    build_score_threshold_sensitivity,
    build_sensitivity_summary_table,
)


class MeteorwatchSensitivityTests(unittest.TestCase):
    def setUp(self):
        self.frame = pd.DataFrame([
            {"date": pd.Timestamp("2020-01-01"), "energy": 1.0, "ml_assessed": True, "iforest_score": -0.50, "iforest_flag": True},
            {"date": pd.Timestamp("2020-01-02"), "energy": 2.0, "ml_assessed": True, "iforest_score": -0.40, "iforest_flag": True},
            {"date": pd.Timestamp("2020-01-03"), "energy": 3.0, "ml_assessed": True, "iforest_score": -0.30, "iforest_flag": False},
            {"date": pd.Timestamp("2020-01-04"), "energy": 4.0, "ml_assessed": True, "iforest_score": -0.20, "iforest_flag": False},
            {"date": pd.Timestamp("2020-01-05"), "energy": 5.0, "ml_assessed": True, "iforest_score": -0.10, "iforest_flag": False},
            {"date": pd.Timestamp("2020-01-06"), "energy": 6.0, "ml_assessed": False, "iforest_score": None, "iforest_flag": None},
            {"date": pd.Timestamp("2020-01-07"), "energy": 7.0, "ml_assessed": None, "iforest_score": -0.60, "iforest_flag": None},
            {"date": pd.Timestamp("2020-01-08"), "energy": 8.0, "ml_assessed": True, "iforest_score": None, "iforest_flag": None},
        ])

    def test_only_explicitly_assessed_rows_with_scores_are_included(self):
        result = build_score_threshold_sensitivity(self.frame)
        meta = result["metadata"]
        self.assertEqual(meta["eligible_scored_records"], 5)
        self.assertEqual(meta["not_assessed_records"], 1)
        self.assertEqual(meta["assessment_status_unknown_records"], 1)
        self.assertEqual(meta["assessed_records_without_finite_score"], 1)

    def test_reference_5_percent_is_always_included(self):
        result = build_score_threshold_sensitivity(self.frame, contamination_levels=[0.10])
        levels = result["summary"]["Score threshold setting (%)"].tolist()
        self.assertEqual(levels, [5.0, 10.0])

    def test_lower_score_is_flagged_and_threshold_scenarios_are_nested(self):
        result = build_score_threshold_sensitivity(self.frame, contamination_levels=[0.05, 0.20, 0.40])
        summary = result["summary"].set_index("Score threshold setting (%)")
        self.assertLessEqual(summary.loc[5.0, "Records flagged"], summary.loc[20.0, "Records flagged"])
        self.assertLessEqual(summary.loc[20.0, "Records flagged"], summary.loc[40.0, "Records flagged"])
        detail = result["event_detail"]
        self.assertEqual(detail.loc[0, "Flag at 40% setting"], "Yes")
        self.assertEqual(detail.loc[4, "Flag at 40% setting"], "No")

    def test_unassessed_unknown_and_missing_score_stay_explicit(self):
        detail = build_score_threshold_sensitivity(self.frame)["event_detail"]
        self.assertEqual(detail.loc[5, "Threshold-study eligibility"], "Not assessed")
        self.assertEqual(detail.loc[6, "Threshold-study eligibility"], "Assessment status unknown")
        self.assertEqual(detail.loc[7, "Threshold-study eligibility"], "Score unavailable")
        self.assertEqual(detail.loc[5, "Flag at 5% setting"], "Not assessed")

    def test_tied_scores_at_cutoff_are_not_forced_to_be_flagged(self):
        tied = pd.DataFrame({
            "ml_assessed": [True] * 4,
            "iforest_score": [-1.0, -1.0, -1.0, 0.0],
            "iforest_flag": [True, True, True, False],
        })
        result = build_score_threshold_sensitivity(tied, contamination_levels=[0.05])
        self.assertEqual(int(result["summary"].iloc[0]["Records flagged"]), 0)

    def test_5_percent_saved_flag_disagreement_is_audit_only(self):
        result = build_score_threshold_sensitivity(self.frame)
        self.assertIsInstance(result["metadata"]["reference_saved_flag_disagreements"], int)
        table = build_sensitivity_summary_table(self.frame)
        method_row = table.loc[table["Metric"] == "Method scope"].iloc[0]
        self.assertEqual(method_row["Value"], "Threshold sensitivity only")
        self.assertIn("does not refit", method_row["Interpretation"])

    def test_invalid_levels_raise_value_error(self):
        with self.assertRaises(ValueError):
            build_score_threshold_sensitivity(self.frame, contamination_levels=[0, 0.05])
        with self.assertRaises(ValueError):
            build_score_threshold_sensitivity(self.frame, contamination_levels=[0.75])

    def test_no_eligible_rows_returns_clear_unavailable_result(self):
        frame = pd.DataFrame({"ml_assessed": [False, None], "iforest_score": [None, -0.1]})
        result = build_score_threshold_sensitivity(frame)
        self.assertTrue(result["summary"].empty)
        self.assertEqual(len(result["event_detail"]), 2)
        table = build_sensitivity_summary_table(frame)
        availability = table.loc[table["Metric"] == "Study availability", "Value"].iloc[0]
        self.assertEqual(availability, "Not available")


if __name__ == "__main__":
    unittest.main()
