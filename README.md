# METEORWATCH v7 — Agent Explanation Engine & Test Lab

This update focuses on the assigned **Member 4 — Agent & Testing** responsibilities. It adds a standalone, testable agent module and an **Agent Test Lab** tab in the Streamlit dashboard.

## What's new

- **Structured event explanations:** each selected event gets an agent-derived interpretation, saved baseline/model reasoning, available measurements, missing-field notes, and a clear scientific caution.
- **Missing-value handling:** an unavailable Isolation Forest flag remains unknown; `ML not assessed` is not rewritten as `ML did not flag`. Missing measurements are never silently changed to zero.
- **Nine synthetic self-tests:** cover the combinations of flags, unassessed rows, missing model inputs, missing energy, and required scientific caution.
- **Saved-status consistency audit:** optionally compares the review status saved in the CSV with a decision reconstructed from its saved flags. Incomplete rows are recorded as not comparable rather than matches.
- **Downloadable test/audit reports:** download the synthetic test results and any status mismatches as CSV files.
- **Standalone agent logic:** `meteorwatch_agent.py` separates the logic from Streamlit so it can be unit-tested and reused.

## Files to add or replace

1. Replace `app.py` with the provided v7 version.
2. **Add `meteorwatch_agent.py` to the same repository folder as `app.py`.** This file is required by the updated app.
3. Add `test_meteorwatch_agent.py` to the repository if you'd like to keep the local unit tests with the project. The deployed dashboard does not need this test file to run.
4. Keep `requirements.txt` and merge `.gitignore` with your current ignore rules if needed.
5. Keep `meteorwatch_full_review_report.csv` unchanged in the same folder as `app.py`.
6. Do not upload API keys, `.env` files, or `.streamlit/secrets.toml` to a public repository.
7. Commit changes to GitHub and let Streamlit Community Cloud redeploy.

## Optional local test

From the repository root, run:

```bash
python -m unittest -v
```

The tests use synthetic records. They check software behaviour—not physical truth, detector accuracy, or the ability to predict future impacts.

## Verify after deployment

Open the **Agent Test Lab** tab and check that all nine synthetic self-tests pass. Then run **Run consistency audit on the loaded report**. If there are status mismatches, download the CSV and check the saved report pipeline before changing any scientific interpretation. Some rows will be not comparable because their saved model result is missing or incomplete.

## Scientific limitations

- A detector flag is a prompt for human review, not proof of danger.
- A record not flagged by either method is not proven safe or normal.
- Missing model results are not negative predictions.
- The consistency audit checks agreement between saved fields; it is not independent scientific validation.
- METEORWATCH analyses historical fireball data. It does not predict future impacts or issue operational warnings.

## Validation performed for this update

- Python syntax compilation passed for `app.py`, `meteorwatch_agent.py`, and `test_meteorwatch_agent.py`.
- All 4 `unittest` cases passed.
- All 9 synthetic Agent Test Lab scenarios passed.
- A small synthetic saved-status audit produced the expected results.
- The Streamlit interface could not be launched in this build environment because Streamlit is not installed here. Please confirm the visible UI in the deployed app after redeployment.
