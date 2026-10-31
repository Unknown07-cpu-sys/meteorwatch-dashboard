# Deployment

## Streamlit Community Cloud

1. Push the repository to GitHub with `app.py` at the **root** of the repository (not inside another folder).
2. In Streamlit Community Cloud, create the app from that repository and branch.
3. Set **Main file path** to `app.py`.
4. Deploy. Dependencies come from `requirements.txt`.

Do not add API keys, OAuth client secrets, cookie secrets, passwords, or `.env` files to the repository. Configure hosted secrets in the app's **Settings → Secrets** panel.

## Optional Google sign-in setup

METEORWATCH remains public when Google authentication is not configured. Visitors can continue to explore the dashboard without logging in. The sidebar's **Team access** panel is only an optional sign-in entry point.

### 1. Create a Google OAuth client

1. Open the [Google Cloud Console](https://console.cloud.google.com/).
2. Select or create a Google Cloud project.
3. Open **Google Auth Platform → Clients** and create an OAuth client.
4. Choose **Web application** as the application type.
5. Add the following authorised redirect URI for the hosted app:

   `https://meteorwatch.streamlit.app/oauth2callback`

6. For local testing, also add:

   `http://localhost:8501/oauth2callback`

7. Save the client and keep its client ID and client secret private.

The redirect URI must match the URL configured in Streamlit secrets exactly, including the `/oauth2callback` path.

### 2. Configure Streamlit secrets

Use `.streamlit/secrets.toml.example` as a template. For local development, copy it to `.streamlit/secrets.toml`. For Streamlit Community Cloud, paste the completed values into **App → Settings → Secrets**.

The required structure is:

```toml
[auth]
redirect_uri = "https://meteorwatch.streamlit.app/oauth2callback"
cookie_secret = "REPLACE_WITH_A_LONG_RANDOM_SECRET"
client_id = "REPLACE_WITH_GOOGLE_CLIENT_ID"
client_secret = "REPLACE_WITH_GOOGLE_CLIENT_SECRET"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"

[access]
team_emails = [
  "member1@example.com",
  "member2@example.com",
  "member3@example.com",
  "member4@example.com"
]
admin_emails = [
  "project-owner@example.com"
]
```

Replace every example email with the real Google account email for that person. Add administrator accounts to `admin_emails`; admins automatically inherit team-member access. Keep both lists private in Streamlit secrets.

Generate a random cookie secret locally, for example:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Do not paste OAuth credentials or cookie secrets into GitHub, source files, chat messages, or the public README. The repository's `.gitignore` excludes `.streamlit/secrets.toml`.

### 3. Configure Google's test users

While the Google OAuth consent configuration is in **Testing** mode, add the team accounts that need to sign in as test users in Google Auth Platform. Follow Google's publishing and verification requirements before making the OAuth application available more broadly.

### 4. Verify access

After saving the secrets, restart or redeploy the Streamlit app, then test these cases:

- A visitor who is not signed in can still access the complete public dashboard.
- An approved, verified team email signs in and receives the `team_member` role.
- An approved, verified admin email receives the `admin` role.
- A signed-in but unlisted account receives no team role and can still use the public dashboard.
- Signing out returns the user to the public dashboard.

This release does not yet include private team tools or private data. The role checks are the foundation for adding those features later. Any future restricted operation must call the role-check helper on the server side; hiding a button alone is not authorisation.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
python -m unittest discover -s tests -v
```

For local sign-in, use the local redirect URI in Google Cloud and set `redirect_uri` to `http://localhost:8501/oauth2callback` in your local secrets file.

## If the app does not start

- **`ModuleNotFoundError: No module named 'meteorwatch'`**: the `meteorwatch/` folder must sit next to `app.py`. Check that it was pushed (it contains `__init__.py`).
- **Nothing on the page except "Add the report to get started"**: the CSV is missing. It belongs at `data/meteorwatch_full_review_report.csv`.
- **A page of plain text with no styling**: the app expects Streamlit 1.42 or later for authentication support and the current layout. Run `pip install --upgrade streamlit`.
- **Google reports `redirect_uri_mismatch`**: confirm the authorised redirect URI in Google Cloud exactly matches `redirect_uri` in Streamlit secrets.
- **A team member can sign in but receives public access only**: check that their email is spelled correctly in `team_emails` or `admin_emails`, and that Google reports the email as verified.
- **Everything is in a nested folder on GitHub**: if the repository shows a single folder such as `meteorwatch-dashboard-main/` and `app.py` is inside it, move the contents up one level, or set Main file path to `meteorwatch-dashboard-main/app.py`.

## Browsers

The scroll-driven motion runs in Chrome, Edge and Safari 26 or later. Other browsers show the same content without it.
Fonts (Bricolage Grotesque and Instrument Sans) load from Google Fonts and fall back to the system sans-serif offline.
