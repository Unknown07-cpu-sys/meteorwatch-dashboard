"""Tests for optional Google sign-in and team/admin authorisation."""
from __future__ import annotations

import unittest

from meteorwatch.access import (
    GOOGLE_OIDC_METADATA_URL,
    get_access_context,
    read_auth_settings,
    role_allows,
)


class AccessControlTests(unittest.TestCase):
    def setUp(self):
        self.secrets = {
            "auth": {
                "redirect_uri": "https://meteorwatch.streamlit.app/oauth2callback",
                "cookie_secret": "a-long-random-cookie-secret-for-tests-only",
                "client_id": "example.apps.googleusercontent.com",
                "client_secret": "example-client-secret",
                "server_metadata_url": GOOGLE_OIDC_METADATA_URL,
            },
            "access": {
                "team_emails": ["member@example.com", "admin@example.com"],
                "admin_emails": ["admin@example.com"],
            },
        }

    def test_complete_google_configuration_is_detected(self):
        settings = read_auth_settings(self.secrets)
        self.assertTrue(settings["auth_configured"])
        self.assertIn("member@example.com", settings["team_emails"])
        self.assertIn("admin@example.com", settings["admin_emails"])

    def test_missing_secrets_keep_public_mode(self):
        settings = read_auth_settings({})
        self.assertFalse(settings["auth_configured"])
        context = get_access_context({"is_logged_in": False}, settings)
        self.assertEqual(context["role"], "public")

    def test_example_placeholders_do_not_enable_authentication(self):
        example = {
            "auth": {
                "redirect_uri": "https://example.com/oauth2callback",
                "cookie_secret": "REPLACE_WITH_RANDOM_SECRET",
                "client_id": "REPLACE_WITH_CLIENT_ID",
                "client_secret": "REPLACE_WITH_CLIENT_SECRET",
                "server_metadata_url": GOOGLE_OIDC_METADATA_URL,
            }
        }
        self.assertFalse(read_auth_settings(example)["auth_configured"])

    def test_approved_verified_team_member_gets_team_role(self):
        settings = read_auth_settings(self.secrets)
        context = get_access_context({
            "is_logged_in": True,
            "email": " MEMBER@example.com ",
            "email_verified": True,
        }, settings)
        self.assertEqual(context["role"], "team_member")
        self.assertTrue(context["is_team_member"])
        self.assertFalse(context["is_admin"])

    def test_approved_verified_admin_gets_admin_role(self):
        context = get_access_context({
            "is_logged_in": True,
            "email": "ADMIN@example.com",
            "email_verified": True,
        }, read_auth_settings(self.secrets))
        self.assertEqual(context["role"], "admin")
        self.assertTrue(context["is_team_member"])
        self.assertTrue(context["is_admin"])

    def test_unlisted_google_account_keeps_public_role(self):
        context = get_access_context({
            "is_logged_in": True,
            "email": "visitor@example.com",
            "email_verified": True,
        }, read_auth_settings(self.secrets))
        self.assertEqual(context["role"], "public")

    def test_unverified_email_is_not_authorised(self):
        context = get_access_context({
            "is_logged_in": True,
            "email": "member@example.com",
            "email_verified": False,
        }, read_auth_settings(self.secrets))
        self.assertEqual(context["role"], "public")

    def test_logged_out_identity_is_not_authorised(self):
        context = get_access_context({
            "is_logged_in": False,
            "email": "admin@example.com",
            "email_verified": True,
        }, read_auth_settings(self.secrets))
        self.assertEqual(context["role"], "public")

    def test_login_identity_without_email_is_not_authorised(self):
        context = get_access_context({
            "is_logged_in": True,
            "email_verified": True,
        }, read_auth_settings(self.secrets))
        self.assertEqual(context["role"], "public")

    def test_admin_inherits_team_permissions(self):
        context = get_access_context({
            "is_logged_in": True,
            "email": "admin@example.com",
            "email_verified": True,
        }, read_auth_settings(self.secrets))
        self.assertTrue(role_allows(context, "team_member"))
        self.assertTrue(role_allows(context, "admin"))

    def test_team_member_does_not_get_admin_permissions(self):
        context = get_access_context({
            "is_logged_in": True,
            "email": "member@example.com",
            "email_verified": True,
        }, read_auth_settings(self.secrets))
        self.assertTrue(role_allows(context, "team_member"))
        self.assertFalse(role_allows(context, "admin"))

    def test_public_role_does_not_get_team_permissions(self):
        context = get_access_context(
            {"is_logged_in": True, "email": "visitor@example.com", "email_verified": True},
            read_auth_settings(self.secrets),
        )
        self.assertTrue(role_allows(context, "public"))
        self.assertFalse(role_allows(context, "team_member"))

    def test_unknown_role_requirement_is_rejected(self):
        with self.assertRaises(ValueError):
            role_allows({"role": "admin"}, "owner")


if __name__ == "__main__":
    unittest.main()
