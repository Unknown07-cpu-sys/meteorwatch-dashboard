"""Run a lightweight smoke test against the real Streamlit script."""
from __future__ import annotations

import unittest

try:
    from streamlit.testing.v1 import AppTest
    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False


@unittest.skipUnless(HAS_STREAMLIT, "requires Streamlit")
class StreamlitSmokeTests(unittest.TestCase):
    def test_shipped_catalogue_renders_without_uncaught_exception(self):
        from pathlib import Path
        app = Path(__file__).resolve().parents[1] / "app.py"
        result = AppTest.from_file(str(app), default_timeout=120).run()
        self.assertFalse(result.exception, [item.value for item in result.exception])
        self.assertFalse(result.error, [item.value for item in result.error])


if __name__ == "__main__":
    unittest.main()
