"""Responsive smoke tests for the deployed Streamlit page, using real Chromium.

Run with:
    playwright install chromium
    RUN_BROWSER_TESTS=1 python -m unittest discover -s tests/browser -v
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
import unittest
import urllib.request
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

ROOT = Path(__file__).resolve().parents[2]
SHOTS = Path(__file__).resolve().parent / "screenshots"
PORT = 8599
URL = f"http://127.0.0.1:{PORT}"
ENABLED = HAS_PLAYWRIGHT and os.environ.get("RUN_BROWSER_TESTS") == "1"


def wait_for_server(timeout: int = 90) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{URL}/_stcore/health", timeout=2) as response:
                if response.status == 200:
                    return
        except Exception:
            time.sleep(1)
    raise RuntimeError("Streamlit did not start in time")


@unittest.skipUnless(ENABLED, "set RUN_BROWSER_TESTS=1 and install Playwright")
class ResponsiveSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        SHOTS.mkdir(exist_ok=True)
        cls.server = subprocess.Popen(
            [sys.executable, "-m", "streamlit", "run", str(ROOT / "app.py"),
             "--server.headless=true", f"--server.port={PORT}",
             "--browser.gatherUsageStats=false"],
            cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        wait_for_server()
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        cls.server.terminate()
        cls.server.wait(timeout=10)

    def test_no_horizontal_overflow_at_common_viewports(self):
        for width, height in ((390, 844), (768, 1024), (1280, 800), (1920, 1080)):
            with self.subTest(width=width):
                page = self.browser.new_page(viewport={"width": width, "height": height})
                try:
                    page.goto(URL, wait_until="domcontentloaded")
                    page.wait_for_selector(".mw-hero", timeout=60000)
                    page.wait_for_timeout(500)
                    page.screenshot(path=str(SHOTS / f"viewport-{width}.png"), full_page=True)
                    if width == 390:
                        outcome_section = page.locator(".mw-section").filter(
                            has_text="Outcomes among comparable records"
                        )
                        outcome_section.scroll_into_view_if_needed()
                        outcome_chart = outcome_section.locator(
                            "xpath=following::*[@data-testid='stPlotlyChart'][1]"
                        )
                        outcome_chart.wait_for(state="visible", timeout=60000)
                        outcome_chart.scroll_into_view_if_needed()
                        page.wait_for_timeout(400)
                        chart_box = outcome_chart.bounding_box()
                        self.assertIsNotNone(chart_box)
                        self.assertGreaterEqual(chart_box["width"], 340, chart_box)
                        outcome_chart.screenshot(path=str(SHOTS / "viewport-390-outcomes.png"))
                    metrics = page.evaluate("""() => ({
                        viewport: document.documentElement.clientWidth,
                        document: document.documentElement.scrollWidth,
                        main: (document.querySelector('[data-testid="stMain"]') || document.body).scrollWidth
                    })""")
                    self.assertLessEqual(metrics["document"] - metrics["viewport"], 2, metrics)
                    self.assertLessEqual(metrics["main"] - metrics["viewport"], 2, metrics)
                finally:
                    page.close()


if __name__ == "__main__":
    unittest.main()
