"""Unit tests for METEORWATCH's transparent agent logic.

Run locally from the repository root with: python -m unittest -v
These tests check program behaviour on synthetic examples, not scientific accuracy.
"""
import unittest

import pandas as pd

from meteorwatch_agent import (
    assess_event, run_agent_self_tests, build_agent_explanation,
    build_structured_review_export,
)


class MeteorwatchAgentTests(unittest.TestCase):
    def setUp(self):
        self.complete = {
            "date": pd.Timestamp("2020-01-01"),
            "energy": 2.5,
            "impact-e": 0.2,
            "alt": 32.0,
            "vx": 1.0,
            "vy": 2.0,
            "vz": 3.0,
            "component_speed": 3.742,
            "map_latitude": 10.0,
            "map_longitude": 20.0,
        }

    def test_all_agent_self_tests_pass(self):
        report = run_agent_self_tests()
        failures = report.loc[~report["Passed"]]
        self.assertTrue(failures.empty, failures.to_string(index=False))

    def test_both_flags_are_distinguished(self):
        result = assess_event({
            **self.complete,
            "baseline_flag": True,
            "iforest_flag": True,
            "ml_assessed": True,
        })
        self.assertEqual(result["decision_label"], "Flagged by both methods")

    def test_not_assessed_is_not_a_negative_model_result(self):
        result = assess_event({
            **self.complete,
            "baseline_flag": False,
            "iforest_flag": None,
            "ml_assessed": False,
        })
        self.assertFalse(result["ml_assessed"])
        self.assertIsNone(result["iforest_flag"])
        self.assertEqual(result["decision_label"], "ML not assessed; baseline did not flag")

    def test_unknown_assessment_with_saved_flag_is_not_inferred_as_assessed(self):
        result = assess_event({
            **self.complete,
            "baseline_flag": False,
            "iforest_flag": True,
            "ml_assessed": None,
        })
        self.assertIsNone(result["ml_assessed"])
        self.assertIn("unknown", result["decision_label"].lower())
        self.assertTrue(any("assessment status is unknown" in reason.lower() for reason in result["reasons"]))

    def test_legacy_record_without_assessment_column_uses_limited_fallback(self):
        legacy = {
            **self.complete,
            "baseline_flag": False,
            "iforest_flag": True,
        }
        result = assess_event(legacy)
        self.assertTrue(result["ml_assessed"])

    def test_missing_energy_is_not_zero_filled(self):
        explanation = build_agent_explanation({
            **self.complete,
            "energy": None,
            "baseline_flag": None,
            "iforest_flag": None,
            "ml_assessed": False,
        })
        self.assertIn("Unavailable in this record", explanation)
        self.assertNotIn("0.000 × 10¹⁰ joules", explanation)


    def test_structured_export_has_readable_groups_and_units(self):
        frame = pd.DataFrame([
            {**self.complete, "baseline_flag": True, "iforest_flag": True,
             "ml_assessed": True, "review_status": "Flagged by both methods",
             "iforest_score": -0.21, "lat": 10.0, "lat-dir": "N", "lon": 20.0, "lon-dir": "E"},
            {**self.complete, "baseline_flag": False, "iforest_flag": False,
             "ml_assessed": True, "review_status": "Neither method flagged",
             "iforest_score": 0.08},
        ])
        export = build_structured_review_export(frame)
        self.assertEqual(len(export), 2)
        self.assertIn("Reported radiated energy (×10¹⁰ J)", export.columns)
        self.assertIn("IQR baseline explanation", export.columns)
        self.assertIn("Suggested review action", export.columns)
        self.assertEqual(export.iloc[0]["Agent interpretation from saved flags"], "Flagged by both methods")
        self.assertEqual(export.iloc[0]["IQR baseline flagged"], "Yes")
        self.assertEqual(export.iloc[1]["IQR baseline flagged"], "No")
        self.assertIn("not a safety clearance", export.iloc[1]["IQR baseline explanation"])

    def test_structured_export_shows_unassessed_model_explicitly(self):
        frame = pd.DataFrame([{
            **self.complete,
            "baseline_flag": False,
            "iforest_flag": None,
            "ml_assessed": False,
            "review_status": "ML not assessed; baseline did not flag",
        }])
        export = build_structured_review_export(frame)
        self.assertEqual(export.iloc[0]["Isolation Forest assessed"], "No")
        self.assertEqual(export.iloc[0]["Isolation Forest flagged"], "Not assessed")
        self.assertIn("did not assess", export.iloc[0]["Isolation Forest explanation"])
        self.assertIn("Coverage / status check", export.iloc[0]["Review queue group"])



if __name__ == "__main__":
    unittest.main()
