# METEORWATCH v6 — Data Quality & Model Coverage

This update adds a **Data Quality** tab to the existing v5 app. It makes field completeness, ML coverage, structural checks, and status counts easier to inspect and export.

## What's added

- Summary of total rows, ML-assessed rows, ML-not-assessed rows, and records with valid map coordinates.
- Field completeness table and chart, including missing counts and percentages for source and derived measurements available in the report.
- Structural checks for missing dates, unavailable/invalid map coordinates, missing/non-positive energy, incomplete Isolation Forest feature rows (when components are present), and exact duplicate rows.
- Downloadable CSVs for field completeness and review-status breakdown.
- More visible caveats: completeness is not measurement accuracy, and an ML-not-assessed record is not an ML-negative record.
- `.gitignore` excludes `__pycache__`, Python bytecode, secrets files, and common local editor/OS files.

## Install on the existing GitHub + Streamlit deployment

1. Download and extract the ZIP.
2. In the repository connected to Streamlit, replace `app.py` and `requirements.txt` with the provided files.
3. Add the provided `.gitignore` at the repository root (merge with an existing `.gitignore` rather than replacing unrelated rules).
4. Keep `meteorwatch_full_review_report.csv` in the repository unchanged.
5. Remove any accidentally committed `__pycache__/` directory or `.pyc` files. If they exist in the GitHub repository, delete them from the repository and commit that deletion. `.gitignore` prevents them from being added again going forward, but does not untrack files already committed.
6. Do not commit `.streamlit/secrets.toml`, API keys, or `.env` files.
7. Commit the update and allow Streamlit Community Cloud to redeploy.
8. Open the **Data Quality** tab. Check the four summary metrics, field completeness table, structural checks, and both CSV download buttons.

## Important interpretation notes

- Quality diagnostics are structural checks; they do not validate the physical accuracy of every reported value.
- Exact duplicate counts compare complete loaded rows only, so differently formatted versions of the same event may not be detected.
- The model-coverage count reflects the `ml_assessed` field in the supplied exported report. It is not recomputed in the dashboard.
- The map displays reported peak-brightness locations, not confirmed impact sites.
- Anomaly flags are review prompts, not danger predictions.

## Validation performed

- Python syntax compilation completed.
- ZIP contents checked to exclude `__pycache__/` and `.pyc` files.
- The Streamlit interface has not been launched against the live website from this environment. Run the manual checks above after deploying.
