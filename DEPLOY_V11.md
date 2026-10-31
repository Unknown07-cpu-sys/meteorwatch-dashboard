# METEORWATCH v11 — Deployment instructions

This release adds a threshold-sensitivity study to the Agent Test Lab. The study uses saved Isolation Forest decision scores only; it does not refit the model or overwrite the stored detector flags.

## Replace these existing files

- `app.py`
- `meteorwatch_exports.py`
- `README.md`
- `CHANGELOG.md`
- `test_meteorwatch_exports.py`

## Add these new files

- `meteorwatch_sensitivity.py`
- `test_meteorwatch_sensitivity.py`

## Keep these files unchanged

- `meteorwatch_full_review_report.csv` — the existing prepared project data.
- `meteorwatch_agent.py`
- `meteorwatch_evaluation.py`
- `test_meteorwatch_agent.py`
- `test_meteorwatch_evaluation.py`
- `requirements.txt` — v11 adds no dependency.
- `.gitignore`
- Streamlit secrets and deployment settings.

## Deploy

1. Download and extract the v11 ZIP.
2. In the repository root (beside `app.py`), replace the files in the first list and add the files in the second list.
3. Do not delete or replace the existing report CSV.
4. Commit with a message such as `Add Isolation Forest threshold sensitivity study`.
5. Allow the existing Streamlit deployment to redeploy.
6. Open **Agent Test Lab** and inspect **Isolation Forest score-threshold sensitivity**.
7. Download both sensitivity CSVs and the Excel workbook. The workbook should contain eight sheets, including `Sensitivity Study`.
8. Verify Event Explorer, the structured and technical CSVs, the AI briefing, detector evaluation, and saved-status audit still work.

## How to interpret the new study

- It uses rows with `ml_assessed = True` and a finite saved `iforest_score` only.
- Lower (more negative) saved scores are treated as more unusual, matching the event sort order used in the app.
- It applies percentile cutoffs at 1%, 2.5%, 5%, 7.5%, 10%, and 15%. The 5% threshold is the reference for overlap calculations.
- Selection uses a strict less-than comparison. Tied scores at the cutoff can make the actual selected share lower than the setting.
- The 5% threshold-derived set is compared with the saved Isolation Forest flags as a consistency check. Differences should be inspected; they are not automatically errors.
- The analysis does not vary training samples, features, random seeds, or refit the model. It does not measure accuracy, precision, recall, physical danger, or future impact risk.
- The `Sensitivity Study` Excel sheet uses the full loaded catalogue to match the Agent Test Lab. The event-level workbook sheets continue to use the current sidebar-filtered view.

## Tests

From the project root, run:

```bash
python -m unittest -v
```

The automated tests verify software behaviour with controlled examples. They are not ground-truth anomaly labels or evidence of detector accuracy.
