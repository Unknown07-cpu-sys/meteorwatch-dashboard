# Deployment

## Streamlit Community Cloud

1. Push the repository to GitHub with `app.py` at the **root** of the repository (not inside another folder).
2. In Streamlit Community Cloud, create the app from that repository and branch.
3. Set **Main file path** to `app.py`.
4. Deploy. Dependencies come from `requirements.txt`.

Do not add API keys or secrets to the repository. If you use secrets, set them in the app settings on Streamlit Community Cloud.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
python -m unittest discover -s tests -v
```

## If the app does not start

- **`ModuleNotFoundError: No module named 'meteorwatch'`**: the `meteorwatch/` folder must sit next to `app.py`. Check that it was pushed (it contains `__init__.py`).
- **Nothing on the page except "Add the report to get started"**: the CSV is missing. It belongs at `data/meteorwatch_full_review_report.csv`.
- **A page of plain text with no styling**: the app expects Streamlit 1.39 or later for the full layout. Run `pip install --upgrade streamlit`.
- **Everything is in a nested folder on GitHub**: if the repository shows a single folder such as `meteorwatch-dashboard-main/` and `app.py` is inside it, move the contents up one level, or set Main file path to `meteorwatch-dashboard-main/app.py`.

## Browsers

The scroll-driven motion runs in Chrome, Edge and Safari 26 or later. Other browsers show the same content without it.
Fonts (Bricolage Grotesque and Instrument Sans) load from Google Fonts and fall back to the system sans-serif offline.
