"""Regression tests for robust CSV loading and missing-value handling."""
from __future__ import annotations

import unittest

import pandas as pd

from meteorwatch.data import ReportLoadError, load_report


HEADER = "date,energy,review_status,lat,lat-dir,lon,lon-dir,vx,vy,vz,baseline_flag,ml_assessed,iforest_flag"


class ReportLoadingTests(unittest.TestCase):
    def test_empty_and_binary_files_are_rejected_clearly(self):
        for payload in (b"", b"\x00\x01\x02"):
            with self.subTest(payload=payload):
                with self.assertRaises(ReportLoadError):
                    load_report(payload)

    def test_required_columns_are_checked(self):
        with self.assertRaisesRegex(ReportLoadError, "review_status"):
            load_report(b"date,energy\n2020-01-01,2\n")

    def test_utf8_bom_and_semicolon_delimiter_are_supported(self):
        payload = "\ufeffdate;energy;review_status\n2020-01-01;2;Not flagged by either method\n".encode()
        frame = load_report(payload)
        self.assertEqual(len(frame), 1)
        self.assertEqual(float(frame.loc[0, "energy"]), 2.0)

    def test_mixed_dates_are_normalised_to_naive_utc(self):
        payload = (
            f"{HEADER}\n"
            "2020-01-01T00:00:00Z,2,Not flagged by either method,10,N,20,E,3,4,12,False,True,False\n"
            "2020-02-01 01:00:00,3,Not flagged by either method,10,N,20,E,3,4,12,False,True,False\n"
        ).encode()
        frame = load_report(payload)
        self.assertEqual(frame["date"].dt.tz, None)
        self.assertEqual(len(frame), 2)

    def test_missing_and_unrecognised_boolean_values_remain_unknown(self):
        payload = (
            f"{HEADER}\n"
            "2020-01-01,, ,,,, ,,,,maybe,maybe,maybe\n"
        ).encode()
        frame = load_report(payload)
        self.assertTrue(pd.isna(frame.loc[0, "energy"]))
        self.assertTrue(pd.isna(frame.loc[0, "baseline_flag"]))
        self.assertTrue(pd.isna(frame.loc[0, "ml_assessed"]))
        self.assertEqual(frame.loc[0, "review_status"], "Status unavailable")

    def test_coordinates_and_component_speed_are_derived_safely(self):
        payload = (
            f"{HEADER}\n"
            "2020-01-01,2,Not flagged by either method,10,S,20,W,3,4,12,False,True,False\n"
            "2020-01-02,2,Not flagged by either method,95,N,20,E,3,,12,False,True,False\n"
        ).encode()
        frame = load_report(payload)
        self.assertEqual(frame.loc[0, "map_latitude"], -10)
        self.assertEqual(frame.loc[0, "map_longitude"], -20)
        self.assertEqual(frame.loc[0, "component_speed"], 13)
        self.assertTrue(pd.isna(frame.loc[1, "map_latitude"]))
        self.assertTrue(pd.isna(frame.loc[1, "component_speed"]))


if __name__ == "__main__":
    unittest.main()
