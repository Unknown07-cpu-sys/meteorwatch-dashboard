# METEORWATCH v8 — Structured CSV Exports

This update improves the Event Explorer's CSV downloads without changing the underlying detector results.

## What's new

- **Structured review report:** one event per row, with a stable record reference based on the source row, readable field names and units, saved review status, agent-derived interpretation, detector flags, explanations, missing-data notes, and a suggested review action.
- **Review queue ordering:** records flagged by both methods appear first, followed by other flagged records and coverage/status checks. This is only a review workflow order; it is **not** a danger ranking.
- **Explicit assessment state:** when ML is marked as not assessed, the structured report displays `Not assessed`, not `No` under the Isolation Forest flag.
- **Model-score context:** when available, the score gets an interpretation note; it is not described as a danger score.
- **Technical export preserved:** a separate download retains the filtered source/technical columns for analysis and reproducibility.
- **Excel-friendly encoding:** CSV downloads use UTF-8 with BOM so labels such as units and symbols are more likely to display correctly in Excel.

## Files to add or replace

1. Replace `app.py` with the v8 version.
2. Replace `meteorwatch_agent.py` with the v8 version; the app imports the new export function from this file.
3. Optionally keep `test_meteorwatch_agent.py` in your repository for reproducibility; Streamlit does not need it to run.
4. Keep your existing `requirements.txt` unless you changed it independently. The provided copy matches the current app's imports.
5. Keep the existing `meteorwatch_full_review_report.csv` unchanged in the repository beside `app.py`. The update ZIP does not include this data file.
6. Keep your `.gitignore`; merge it with existing rules rather than overwriting any custom rules.
7. Commit the changes to GitHub and wait for Streamlit Community Cloud to redeploy.

## Downloads after deployment

In **Event Explorer**, the two options are:

- `meteorwatch_structured_review_report.csv` — human-readable review report with explanations and review actions.
- `meteorwatch_filtered_technical_data.csv` — filtered source/technical columns.

The structured file is sorted by review workflow category, not physical risk. A flag is a prompt for human review, not proof of a danger or confirmed anomaly. An unflagged event is not proven safe, and METEORWATCH does not predict future impacts.

## Validation performed

- Python syntax compilation passed for `app.py`, `meteorwatch_agent.py`, and `test_meteorwatch_agent.py`.
- All 6 Python unit tests passed.
- All 9 synthetic Agent Test Lab cases passed through the test suite.
- A synthetic export smoke test confirmed the column layout, priority ordering, and explicit `Not assessed` label.
- The live Streamlit interface was not launched in this environment. Confirm both download buttons in the deployed dashboard after redeployment.

Run tests locally from the project folder with:

```bash
python -m unittest -v
```
