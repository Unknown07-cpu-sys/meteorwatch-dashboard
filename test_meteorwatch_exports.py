"""Tests for the METEORWATCH multi-sheet Excel export."""
from __future__ import annotations

from io import BytesIO
import unittest
import xml.etree.ElementTree as ET
import zipfile

import pandas as pd

from meteorwatch_exports import build_review_workbook


class MeteorwatchWorkbookTests(unittest.TestCase):
    def setUp(self) -> None:
        self.frame = pd.DataFrame([
            {
                "date": pd.Timestamp("2020-01-01 12:00:00"),
                "energy": 2.5,
                "impact-e": 0.2,
                "lat": 10.0,
                "lat-dir": "N",
                "lon": 20.0,
                "lon-dir": "E",
                "alt": 32.0,
                "vel": None,
                "vx": 1.0,
                "vy": 2.0,
                "vz": 3.0,
                "component_speed": 3.742,
                "map_latitude": 10.0,
                "map_longitude": 20.0,
                "baseline_flag": True,
                "iforest_flag": True,
                "ml_assessed": True,
                "iforest_score": -0.21,
                "review_status": "Flagged by both methods",
            },
            {
                "date": pd.Timestamp("2021-01-01 12:00:00"),
                "energy": 1.0,
                "impact-e": 0.1,
                "lat": None,
                "lat-dir": None,
                "lon": None,
                "lon-dir": None,
                "alt": None,
                "vel": None,
                "vx": None,
                "vy": None,
                "vz": None,
                "component_speed": None,
                "map_latitude": None,
                "map_longitude": None,
                "baseline_flag": False,
                "iforest_flag": None,
                "ml_assessed": False,
                "iforest_score": None,
                "review_status": "ML not assessed; baseline did not flag",
            },
        ])

    def test_workbook_is_valid_xlsx_container(self):
        data = build_review_workbook(self.frame, self.frame)
        self.assertTrue(data.startswith(b"PK"))
        self.assertGreater(len(data), 5000)
        with zipfile.ZipFile(BytesIO(data)) as archive:
            self.assertIn("xl/workbook.xml", archive.namelist())
            self.assertIn("[Content_Types].xml", archive.namelist())

    def test_workbook_contains_expected_sheets(self):
        data = build_review_workbook(self.frame, self.frame)
        with zipfile.ZipFile(BytesIO(data)) as archive:
            root = ET.fromstring(archive.read("xl/workbook.xml"))
        ns = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        names = [node.attrib["name"] for node in root.findall("x:sheets/x:sheet", ns)]
        self.assertEqual(names, [
            "Start Here", "Event Review", "Technical Data", "Data Quality",
            "Review Status", "Agent Tests",
        ])

    def test_workbook_includes_review_caveats(self):
        data = build_review_workbook(self.frame, self.frame)
        with zipfile.ZipFile(BytesIO(data)) as archive:
            shared_strings = archive.read("xl/sharedStrings.xml").decode("utf-8")
        self.assertIn("not proven safe", shared_strings)
        self.assertIn("Not assessed", shared_strings)

    def test_technical_sheet_excludes_derived_map_coordinates(self):
        # Confirm the technical export convention used in this workbook function.
        data = build_review_workbook(self.frame, self.frame)
        with zipfile.ZipFile(BytesIO(data)) as archive:
            workbook_xml = ET.fromstring(archive.read("xl/workbook.xml"))
            rels_xml = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
            ns = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
                  "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
                  "p": "http://schemas.openxmlformats.org/package/2006/relationships"}
            rel_map = {node.attrib["Id"]: node.attrib["Target"] for node in rels_xml.findall("p:Relationship", ns)}
            tech_sheet = next(node for node in workbook_xml.findall("x:sheets/x:sheet", ns) if node.attrib["name"] == "Technical Data")
            target = "xl/" + rel_map[tech_sheet.attrib[f"{{{ns['r']}}}id"]]
            sheet_root = ET.fromstring(archive.read(target))
            shared_root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            shared_values = [
                "".join(text_node.text or "" for text_node in item.findall(".//x:t", ns))
                for item in shared_root.findall("x:si", ns)
            ]
            first_row = sheet_root.find("x:sheetData/x:row[@r='1']", ns)
            self.assertIsNotNone(first_row)
            header_values = []
            for cell in first_row.findall("x:c", ns):
                value_node = cell.find("x:v", ns)
                if value_node is None:
                    header_values.append("")
                elif cell.attrib.get("t") == "s":
                    header_values.append(shared_values[int(value_node.text)])
                else:
                    header_values.append(value_node.text or "")
            self.assertNotIn("map_latitude", header_values)
            self.assertNotIn("map_longitude", header_values)


if __name__ == "__main__":
    unittest.main()
