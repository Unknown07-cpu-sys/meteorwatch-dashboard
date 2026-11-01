# Deployment

## Streamlit Community Cloud

1. Push the repository to GitHub with `app.py` at the repository root.
2. In Streamlit Community Cloud, create an app from the repository and branch.
3. Set **Main file path** to `app.py`.
4. Deploy. Runtime dependencies are installed from `requirements.txt`.

Keep provider API keys out of source files and GitHub. The app accepts a key in the session for an optional AI briefing; use only your own key and review the provider's data-handling terms before sending event details.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

To use another report without replacing the shipped catalogue, set `METEORWATCH_DATA` before starting the app:

```bash
METEORWATCH_DATA=/path/to/report.csv streamlit run app.py
```

On Windows PowerShell:

```powershell
$env:METEORWATCH_DATA = "C:\path\to\report.csv"
streamlit run app.py
```

## Tests

Install development dependencies and run the test suite:

```bash
pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

Browser layout checks and their screenshot instructions are in [TESTING.md](TESTING.md). GitHub Actions runs the unit and browser jobs on pushes and pull requests.

## If the app does not start

- **`ModuleNotFoundError: No module named 'meteorwatch'`**: ensure the `meteorwatch/` folder is next to `app.py` and was committed.
- **The app asks for a report**: put `meteorwatch_full_review_report.csv` in `data/`, or upload it in the sidebar.
- **CSV rejected**: confirm the file has `date`, `energy`, and `review_status` columns. The loader accepts comma, semicolon and tab-separated files.
- **AI provider request rejected**: check that the base URL uses HTTPS and one of the supported provider hosts shown in the app's provider help. Redirects are blocked.
- **Google Gemini request fails**: check the key and model name. Live provider availability can change; run only the opt-in provider check if you want to verify a real key.

## Scientific scope

METEORWATCH analyses a supplied historical catalogue. A detector flag is a prompt for human review, not proof of a physical anomaly or hazard. An unflagged record is not established as safe. Reported coordinates indicate peak-brightness location, not necessarily a ground impact site. The app does not predict future impacts.
