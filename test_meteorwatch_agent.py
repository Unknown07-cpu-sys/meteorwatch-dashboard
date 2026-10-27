"""Unit tests for METEORWATCH's transparent agent logic.

Run locally from the repository root with: python -m unittest -v
These tests check program behaviour on synthetic examples, not scientific accuracy.
"""
import unittest

import pandas as pd

from meteorwatch_agent import assess_event, run_agent_self_tests, build_agent_explanation


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


if __name__ == "__main__":
    unittest.main()
