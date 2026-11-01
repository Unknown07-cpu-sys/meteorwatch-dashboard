"""Tests for safe, centralized preparation of dashboard dataframe displays."""
from __future__ import annotations

import ast
from pathlib import Path
import unittest

import pandas as pd

from meteorwatch.ui.tables import prepare_display_table


ROOT = Path(__file__).resolve().parents[1]


class DisplayTableTests(unittest.TestCase):
    def test_mixed_object_columns_become_nullable_text_without_mutating_source(self):
        source = pd.DataFrame({
            "Value": pd.Series([12, "100.00%", None], dtype=object),
            "Records": pd.Series([1, 2, 3], dtype="int64"),
            "Label": pd.Series(["first", "second", None], dtype=object),
        })

        display = prepare_display_table(source)

        self.assertEqual(str(display["Value"].dtype), "string")
        self.assertEqual(display.loc[0, "Value"], "12")
        self.assertEqual(display.loc[1, "Value"], "100.00%")
        self.assertTrue(pd.isna(display.loc[2, "Value"]))
        self.assertTrue(pd.api.types.is_integer_dtype(display["Records"]))
        self.assertEqual(source.loc[0, "Value"], 12)
        self.assertEqual(display["Label"].dtype, source["Label"].dtype)

    def test_evaluation_and_sensitivity_tables_use_the_same_normalization(self):
        from meteorwatch.evaluation import build_detector_evaluation_table
        from meteorwatch.sensitivity import build_sensitivity_summary_table

        evaluation_input = pd.DataFrame([
            {"baseline_flag": True, "ml_assessed": True, "iforest_flag": True}
        ])
        sensitivity_input = pd.DataFrame([
            {"ml_assessed": True, "iforest_score": -0.5, "iforest_flag": True},
            {"ml_assessed": True, "iforest_score": -0.1, "iforest_flag": False},
        ])

        for raw_table in (
            build_detector_evaluation_table(evaluation_input),
            build_sensitivity_summary_table(sensitivity_input),
        ):
            with self.subTest(columns=list(raw_table.columns)):
                display = prepare_display_table(raw_table)
                self.assertEqual(str(display["Value"].dtype), "string")
                for column_name in display.columns:
                    column = display[column_name]
                    if pd.api.types.is_object_dtype(column.dtype):
                        self.assertLessEqual(column.dropna().map(type).nunique(), 1)

    def test_every_streamlit_table_renderer_in_app_uses_the_shared_helper(self):
        app_tree = ast.parse((ROOT / "app.py").read_text(encoding="utf-8"))
        renderers = {"dataframe", "table", "data_editor"}
        calls = [
            node for node in ast.walk(app_tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "st"
            and node.func.attr in renderers
        ]

        self.assertGreater(len(calls), 0, "Expected at least one Streamlit table renderer in app.py")
        for call in calls:
            with self.subTest(renderer=ast.unparse(call.func), line=call.lineno):
                self.assertTrue(call.args, "The table renderer must receive a dataframe")
                argument = call.args[0]
                self.assertIsInstance(argument, ast.Call)
                self.assertIsInstance(argument.func, ast.Attribute)
                self.assertIsInstance(argument.func.value, ast.Name)
                self.assertEqual(argument.func.value.id, "ui")
                self.assertEqual(argument.func.attr, "prepare_display_table")


if __name__ == "__main__":
    unittest.main()
