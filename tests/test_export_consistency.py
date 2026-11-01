"""Check that downloadable CSVs preserve missing cells as blanks."""
from __future__ import annotations

from io import BytesIO
import unittest

import pandas as pd

from meteorwatch.exports import csv_download


class CsvDownloadTests(unittest.TestCase):
    def test_missing_values_are_empty_fields_not_text_placeholders(self):
        frame = pd.DataFrame({"event": ["A", "B"], "energy": [2.0, float("nan")], "note": [None, "known"]})
        raw = csv_download(frame)
        loaded = pd.read_csv(BytesIO(raw), dtype=str, keep_default_na=False)
        self.assertEqual(loaded.loc[1, "energy"], "")
        self.assertEqual(loaded.loc[0, "note"], "")
        self.assertFalse(loaded.astype(str).isin({"nan", "NaT", "<NA>", "None"}).any().any())

    def test_requested_columns_can_be_omitted(self):
        frame = pd.DataFrame({"a": [1], "map_latitude": [10]})
        loaded = pd.read_csv(BytesIO(csv_download(frame, ("map_latitude",))))
        self.assertEqual(list(loaded.columns), ["a"])


if __name__ == "__main__":
    unittest.main()
