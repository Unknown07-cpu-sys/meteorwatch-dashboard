# METEORWATCH v12 — Deployment instructions

This release redesigns the interface. The analysis, agent, evaluation, sensitivity and export code is unchanged.

## Replace these existing files

- `app.py`
- `README.md`
- `CHANGELOG.md`

## Add these new files

- `meteorwatch_ui.py`
- `.streamlit/config.toml` (create the `.streamlit` folder if it does not exist)
- `test_meteorwatch_ui.py`

## Keep these files unchanged

- `meteorwatch_full_review_report.csv`
- `meteorwatch_agent.py`, `meteorwatch_evaluation.py`, `meteorwatch_exports.py`, `meteorwatch_sensitivity.py`
- all other `test_*.py` files
- `requirements.txt` (v12 adds no dependency)
- Streamlit secrets and deployment settings

## Check before you push

```bash
pip install -r requirements.txt
python -m unittest -v
streamlit run app.py
```

Fonts (Bricolage Grotesque and Instrument Sans) load from Google Fonts. Offline, the page falls back to the system sans-serif.
