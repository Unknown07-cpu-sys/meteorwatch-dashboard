# Deploy METEORWATCH v9

This release adds a multi-sheet Excel workbook export in Event Explorer. It also introduces the documentation convention requested for the project: `README.md` is the stable project/agent overview, and `CHANGELOG.md` is where release-by-release changes are recorded.

## Files to add or replace

1. Replace `app.py` with the v9 copy.
2. Add `meteorwatch_exports.py` in the same repository folder as `app.py`.
3. Add/update the project-root `README.md` and `CHANGELOG.md` supplied in this package.
4. Replace `requirements.txt` with the supplied copy so Streamlit installs `XlsxWriter`.
5. Keep `meteorwatch_agent.py`, `meteorwatch_full_review_report.csv`, `.gitignore`, and existing Streamlit secrets unchanged unless you have independent changes to preserve. Do not commit API keys or secrets.
6. Optionally add `test_meteorwatch_exports.py` to keep the workbook tests in the repository. The dashboard does not need the test file to run.
7. Commit the changes to GitHub and allow Streamlit Community Cloud to redeploy.

## What's new

The Event Explorer offers a workbook with six sheets: `Start Here`, `Event Review`, `Technical Data`, `Data Quality`, `Review Status`, and `Agent Tests`. It reflects the currently filtered view. The existing structured review CSV and technical data CSV remain available.

## Validation performed

- Python syntax compilation passed for the application and modules.
- All 10 automated unit tests passed, including workbook structure and sheet checks.
- The workbook was opened and inspected programmatically in the local test environment.
- The live Streamlit UI was not launched or changed by this environment. After redeployment, download the XLSX from your live app and open it in Excel or Google Sheets to confirm the live route.
