# METEORWATCH v2 dashboard update

This update adds a world map using only coordinates reported in the source data, a more complete event explorer, rule-generated event briefings, a data-quality snapshot, and a Methods & Limitations tab.

## How to update the deployed app

1. Keep `meteorwatch_full_review_report.csv` in the same GitHub repository as `app.py`.
2. Download and extract `meteorwatch_v2_update.zip`.
3. Upload the new `app.py` to the existing GitHub repository, replacing the previous `app.py`.
4. Upload `requirements.txt` if you want to keep dependencies documented. It should contain Streamlit, pandas, NumPy, and Plotly.
5. Commit changes. Streamlit Community Cloud should redeploy the app automatically.
6. Open the live app and verify the Overview, Event Map, Event Explorer, and Methods & Limitations tabs.

## Notes

- The app uses the existing `meteorwatch_full_review_report.csv`. Do not delete that file from the repository.
- The Event Map derives signed coordinates from `lat`, `lat-dir`, `lon`, and `lon-dir`. It maps peak-brightness locations, not confirmed ground impact sites.
- Event briefings are rule-generated, transparent summaries, not text produced by a large language model.
- Isolation Forest flags are review prompts, not danger ratings or future-impact predictions.
- Keep secrets and API keys out of GitHub. This version does not need an API key.
