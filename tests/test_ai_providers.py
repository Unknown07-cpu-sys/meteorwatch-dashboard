"""Security and contract tests for OpenAI-compatible provider endpoints."""
from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

import pandas as pd

from meteorwatch.briefing import make_ai_briefing


class ProviderEndpointSecurityTests(unittest.TestCase):
    def setUp(self):
        self.event = pd.Series({"date": pd.Timestamp("2020-01-01"), "energy": 2.0})
        self.success = Mock(status_code=200)
        self.success.json.return_value = {"choices": [{"message": {"content": "Summary"}}]}

    def call(self, url):
        return make_ai_briefing(
            self.event, "Explain this record", "OpenAI-compatible API",
            "test-key", "test-model", base_url=url,
        )

    def test_supported_https_hosts_are_accepted(self):
        for host in (
            "https://openrouter.ai/api/v1",
            "https://api.groq.com/openai/v1",
            "https://api.deepseek.com/v1",
            "https://api.mistral.ai/v1",
            "https://api.together.xyz/v1",
            "https://api.cerebras.ai/v1",
            "https://api.openai.com/v1",
            "https://api.x.ai/v1",
            "https://api.perplexity.ai",
            "https://api.fireworks.ai/inference/v1",
        ):
            with self.subTest(host=host), patch("meteorwatch.briefing.requests.post", return_value=self.success):
                self.assertEqual(self.call(host), "Summary")

    def test_unknown_host_plain_http_credentials_and_custom_ports_are_rejected(self):
        for url in (
            "http://api.groq.com/openai/v1",
            "https://example.com/v1",
            "https://api.groq.com.evil.example/v1",
            "https://user:pass@api.groq.com/v1",
            "https://api.groq.com:8443/v1",
            "https://api.groq.com/v1?redirect=https://example.com",
            "https://api.groq.com/v1#fragment",
            "https://api.groq.com:bad/v1",
        ):
            with self.subTest(url=url), patch("meteorwatch.briefing.requests.post") as post:
                with self.assertRaises(ValueError):
                    self.call(url)
                post.assert_not_called()

    def test_redirect_response_is_not_followed(self):
        redirect = Mock(status_code=302)
        with patch("meteorwatch.briefing.requests.post", return_value=redirect) as post:
            with self.assertRaisesRegex(RuntimeError, "redirect"):
                self.call("https://api.groq.com/openai/v1")
            self.assertFalse(post.call_args.kwargs["allow_redirects"])


if __name__ == "__main__":
    unittest.main()
