# METEORWATCH

**AI-Powered Fireball Event Analysis & Space-Impact Awareness Agent**

METEORWATCH is a student-built educational prototype that organises and analyses historical fireball records from NASA/JPL. It presents recorded measurements in an interactive dashboard, explains existing statistical/model flags, and helps a person decide which records to inspect more closely.

> **Scope boundary:** METEORWATCH is a historical analysis and education tool. It does not predict future impacts, issue operational warnings, or determine whether an event is dangerous. A flag is a prompt for human review, not proof of a physical anomaly; an unflagged event is not proven safe.

## What the project does

- **Historical event explorer:** Search and filter records, inspect individual events, and view available measurements.
- **Energy-based baseline:** Uses a documented statistical IQR rule applied to log-transformed reported energy to identify records for review.
- **Experimental anomaly detector:** Uses the saved Isolation Forest results where the required inputs were available. Its flags and scores are not danger ratings.
- **Transparent agent explanations:** Interprets the saved baseline and model outputs, states the basis for the current review label, surfaces missing fields, and distinguishes `Not assessed` from `Not flagged`.
- **Agent Test Lab:** Runs deterministic synthetic tests for the agent's software logic. Passing tests show that specified rules behaved as expected; they do not prove scientific accuracy.
- **Data Quality panel:** Shows field completeness, missing values, model coverage, and selected structural checks.
- **Exports:** Provides a human-oriented structured CSV, a technical CSV, and a multi-sheet Excel workbook for the current filtered view.
- **Optional event briefing:** Can generate a rule-based briefing without an external AI API, or use a configured supported provider. Such a briefing does not retrain the detectors or independently verify source measurements.

## How the agent works

METEORWATCH's transparent agent is a **decision-support and explanation layer** over the outputs saved in the report CSV. It is not a self-directed spacecraft system and does not perform live hazard monitoring.

1. **Observe:** Read the event's reported measurements and saved fields, including `baseline_flag`, `ml_assessed`, and `iforest_flag`.
2. **Interpret:** Combine the available saved flags into a human-readable status, such as a baseline-only flag, an Isolation Forest-only flag, both methods flagging, neither method flagging, or an incomplete/not-assessed state.
3. **Explain:** State which result was present, identify missing measurements or model inputs, and attach appropriate limitations.
4. **Organise review:** Place records into a review workflow. Queue order is for investigation, not a physical-risk ranking.
5. **Test:** Use documented synthetic cases to verify that missing model results are not misread as negative results and that scientific caution remains visible.

The agent does not independently recalculate all detector outputs from raw NASA records. It explains the saved outputs in the loaded report. Where an output or assessment status is missing or inconsistent, the app should surface that uncertainty rather than silently treating it as `False`.

## Data source and interpretation

Primary source: [NASA/JPL Fireball Data API documentation](https://ssd-api.jpl.nasa.gov/doc/fireball.html).

The dashboard consumes the prepared report `meteorwatch_full_review_report.csv`. Common fields include event time, reported radiated energy, estimated impact energy, altitude, velocity components, coordinates, saved detector flags, and a saved review status. Field availability varies by record.

- Missing values are not equivalent to zero.
- The experimental Isolation Forest requires a complete set of its configured inputs; some records are therefore marked `Not assessed`.
- Reported coordinates, where available, represent the reported peak-brightness location, not necessarily a ground-impact site.
- The detector experiment has no independently verified ground-truth labels in this project. Do not claim validated anomaly-detection accuracy from synthetic software tests.
- Energy values and velocity values should be described using the units shown in the app and exported reports.

## Run locally

Use Python 3.10 or later, then install the listed dependencies:

```bash
pip install -r requirements.txt
streamlit run app.py
```

Keep `meteorwatch_full_review_report.csv` beside `app.py`, or upload the report through the dashboard if the local file is unavailable. The report CSV is input data used by the app; it is not included in this update package.

## Main files

| File | Purpose |
|---|---|
| `app.py` | Streamlit dashboard and user interface |
| `meteorwatch_agent.py` | Transparent decision interpretation, explanations, structured review export, status audit, and synthetic self-tests |
| `meteorwatch_exports.py` | Multi-sheet Excel workbook builder |
| `test_meteorwatch_agent.py` | Automated tests for agent decisions, explanations and structured CSV exports |
| `test_meteorwatch_exports.py` | Automated workbook export checks |
| `requirements.txt` | Python dependencies |
| `CHANGELOG.md` | Version-by-version project history |

## Test the agent and exports

Run tests from the project directory:

```bash
python -m unittest -v
```

These tests are software checks on synthetic or controlled examples. They are not evidence of scientific validity or real-world prediction performance.

## API keys and secrets

Never commit API keys, passwords, `.env` files, or Streamlit secrets to GitHub. If using an optional external briefing provider, check the provider's current terms and account limits. A key entered into a hosted app is sent through that app's server to make the requested provider call; only enter a key when you trust the app operator and understand the provider's terms.

## Project history

Release-by-release changes belong in [`CHANGELOG.md`](CHANGELOG.md). Keep this README focused on the project's purpose, architecture, setup, and limitations; do not rewrite it for every small release.
