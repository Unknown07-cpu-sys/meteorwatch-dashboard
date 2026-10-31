"""Tests for conservative coverage/agreement summaries (not detector accuracy)."""
import unittest

import pandas as pd

from meteorwatch_evaluation import (
    build_detector_evaluation,
    build_detector_evaluation_table,
    build_event_level_comparison,
)


class DetectorEvaluationTests(unittest.TestCase):
    def test_comparable_outcomes_and_agreement(self):
        frame = pd.DataFrame([
            {"baseline_flag": True, "ml_assessed": True, "iforest_flag": True},
            {"baseline_flag": True, "ml_assessed": True, "iforest_flag": False},
            {"baseline_flag": False, "ml_assessed": True, "iforest_flag": True},
            {"baseline_flag": False, "ml_assessed": True, "iforest_flag": False},
        ])
        metrics = build_detector_evaluation(frame)
        self.assertEqual(metrics["comparable_pairs"], 4)
        self.assertEqual(metrics["outcome_counts"]["Flagged by both methods"], 1)
        self.assertEqual(metrics["outcome_counts"]["IQR baseline only"], 1)
        self.assertEqual(metrics["outcome_counts"]["Isolation Forest only"], 1)
        self.assertEqual(metrics["outcome_counts"]["Neither method flagged"], 1)
        self.assertEqual(metrics["observed_agreement_pct"], 50.0)
        self.assertEqual(metrics["jaccard_flag_overlap_pct"], 33.33333333333333)

    def test_not_assessed_rows_are_not_compared_as_negative(self):
        frame = pd.DataFrame([
            {"baseline_flag": False, "ml_assessed": False, "iforest_flag": None},
            {"baseline_flag": False, "ml_assessed": False, "iforest_flag": False},
            {"baseline_flag": True, "ml_assessed": None, "iforest_flag": None},
        ])
        metrics = build_detector_evaluation(frame)
        self.assertEqual(metrics["comparable_pairs"], 0)
        self.assertIsNone(metrics["observed_agreement_pct"])
        self.assertIsNone(metrics["cohen_kappa"])
        self.assertEqual(metrics["ml_marked_not_assessed_but_flag_exists"], 1)

    def test_unknown_fields_reduce_comparable_count(self):
        frame = pd.DataFrame([
            {"baseline_flag": True, "ml_assessed": True, "iforest_flag": True},
            {"baseline_flag": None, "ml_assessed": True, "iforest_flag": False},
            {"baseline_flag": False, "ml_assessed": True, "iforest_flag": None},
            {"baseline_flag": False, "ml_assessed": None, "iforest_flag": True},
        ])
        metrics = build_detector_evaluation(frame)
        self.assertEqual(metrics["comparable_pairs"], 1)
        self.assertEqual(metrics["observed_agreement_pct"], 100.0)
        self.assertEqual(metrics["ml_assessment_unknown_but_flag_exists"], 1)
        self.assertEqual(metrics["ml_marked_assessed_but_flag_missing"], 1)

    def test_identical_all_negative_methods_has_undefined_kappa(self):
        frame = pd.DataFrame([
            {"baseline_flag": False, "ml_assessed": True, "iforest_flag": False},
            {"baseline_flag": False, "ml_assessed": True, "iforest_flag": False},
        ])
        metrics = build_detector_evaluation(frame)
        self.assertEqual(metrics["observed_agreement_pct"], 100.0)
        self.assertIsNone(metrics["cohen_kappa"])
        self.assertIsNone(metrics["jaccard_flag_overlap_pct"])

    def test_summary_disclaims_accuracy_without_ground_truth(self):
        table = build_detector_evaluation_table(pd.DataFrame([
            {"baseline_flag": True, "ml_assessed": True, "iforest_flag": True}
        ]))
        row = table.loc[table["Metric"] == "Ground-truth labels available"].iloc[0]
        self.assertEqual(row["Value"], "No")
        self.assertIn("precision, recall and accuracy are not estimated", row["Interpretation"])

    def test_event_level_export_explains_non_comparable_rows(self):
        frame = pd.DataFrame([
            {"date": pd.Timestamp("2020-01-01"), "energy": 1.2,
             "baseline_flag": False, "ml_assessed": False, "iforest_flag": None},
            {"date": pd.Timestamp("2021-01-01"), "energy": 2.2,
             "baseline_flag": True, "ml_assessed": True, "iforest_flag": True},
        ])
        result = build_event_level_comparison(frame)
        self.assertEqual(len(result), 2)
        self.assertEqual(result.iloc[0]["Pairwise comparison outcome"], "Flagged by both methods")
        self.assertIn("Not comparable: ML not assessed", result["Pairwise comparison outcome"].tolist())
        self.assertIn("Not assessed", result["Isolation Forest flagged"].tolist())


if __name__ == "__main__":
    unittest.main()
