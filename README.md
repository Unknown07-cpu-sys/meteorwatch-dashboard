# METEORWATCH

**AI-Powered Fireball Event Analysis & Space-Impact Awareness Agent**

METEORWATCH is a student-built educational prototype that organises and analyses historical fireball records from NASA/JPL. It presents recorded measurements in an interactive dashboard, explains existing statistical/model flags, and helps a person decide which records to inspect more closely.

> **Scope boundary:** METEORWATCH is a historical analysis and education tool. It does not predict future impacts, issue operational warnings, or determine whether an event is dangerous. A flag is a prompt for human review, not proof of a physical anomaly; an unflagged event is not proven safe.

## What the project does

- **Historical event explorer:** Search and filter records, inspect individual events, and view available measurements.
- **Energy-based baseline:** Uses a documented statistical IQR rule applied to log-transformed reported energy to identify records for review.
- **Experimental anomaly detector:** Uses the saved Isolation Forest results where the required inputs were available. Its flags and scores are not danger ratings.
- **Transparent agent explanations:** Interprets the saved baseline and model outputs, states the basis for the current review label, surfaces missing fields, and distinguishes `Not assessed` from `Not flagged`.
- **Detector lab (Logic tests):** Runs deterministic synthetic tests for the agent's software logic. Passing tests show that specified rules behaved as expected; they do not prove scientific accuracy.
- **Detector evaluation:** Summarises baseline/ML coverage and agreement between saved detector flags on comparable records. Observed agreement, Cohen's kappa, and Jaccard overlap are descriptive comparisons—not accuracy measures.
- **Score-threshold sensitivity study:** Reuses saved Isolation Forest decision scores to show how selected-record counts change under several contamination-style percentile cutoffs. It does not refit the detector or change saved flags.
- **Data Quality panel:** Shows field completeness, missing values, model coverage, and selected structural checks.
- **Exports:** Provides a human-oriented structured CSV, a technical CSV, event-level detector-comparison and score-threshold sensitivity CSVs, summary CSVs, and a multi-sheet Excel workbook. The workbook includes a catalogue-wide sensitivity summary.
- **Optional event briefing:** Can generate a rule-based briefing without an external AI API, or use a configured supported provider. Such a briefing does not retrain the detectors or independently verify source measurements.

## How the dashboard is organised

The app is one scrolling page rather than a set of tabs. It opens on a sky where every star is a real record (left to right is time, higher is more reported energy), then moves through chapters: **01 Sky** (every record by date and energy), **02 Map** (flat map or globe), **03 Two ways to look closer** (the two detectors and how much the Isolation Forest could assess), **04 Look at a single fireball** (select a row to open its record sheet), **05 Briefing** and **06 Check the checks** (detector agreement, threshold sensitivity, status audit, logic tests, data quality, method and limits).

Filters live in the sidebar, which starts collapsed. They apply to chapters 01, 02, 04 and 05.

Colour is reserved for detector status. A **faint or hollow** mark means the Isolation Forest did not assess the record; it is deliberately never drawn like “not flagged”.

Scroll effects (words that brighten as they scroll in, charts that rise into view, a pinned title) use CSS scroll-driven animation. They run in Chrome, Edge and Safari 26 or later. Other browsers show the same content without the scroll motion, and everything is switched off for people who ask their system for reduced motion.

## How the agent works

METEORWATCH's transparent agent is a **decision-support and explanation layer** over the outputs saved in the report CSV. It is not a self-directed spacecraft system and does not perform live hazard monitoring.

1. **Observe:** Read the event's reported measurements and saved fields, including `baseline_flag`, `ml_assessed`, and `iforest_flag`.
2. **Interpret:** Combine the available saved flags into a human-readable status, such as a baseline-only flag, an Isolation Forest-only flag, both methods flagging, neither method flagging, or an incomplete/not-assessed state.
3. **Explain:** State which result was present, identify missing measurements or model inputs, and attach appropriate limitations.
4. **Organise review:** Place records into a review workflow. Queue order is for investigation, not a physical-risk ranking.
5. **Test:** Use documented synthetic cases to verify that missing model results are not misread as negative results and that scientific caution remains visible.

The agent does not independently recalculate all detector outputs from raw NASA records. It explains the saved outputs in the loaded report. The sensitivity study reuses saved Isolation Forest decision scores to compare threshold settings; it does not refit the model or alter saved classifications. Where an output or assessment status is missing or inconsistent, the app should surface that uncertainty rather than silently treating it as `False`. If `ml_assessed` exists but is blank or unrecognised, the agent preserves it as unknown; only legacy files that lack the field entirely use the saved Isolation Forest flag as a limited fallback indicator.

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

The app reads `data/meteorwatch_full_review_report.csv`. (It also accepts the file beside `app.py`.) You can upload a different report from the sidebar.

## Project layout

```
app.py                       Streamlit entry point: page flow, filters, chapters
requirements.txt
data/
  meteorwatch_full_review_report.csv
meteorwatch/                 Python package
  agent.py                   decision interpretation, explanations, structured export, status audit, self-tests
  evaluation.py              coverage, inter-method agreement, event-level comparison
  sensitivity.py             score-threshold sensitivity study
  exports.py                 multi-sheet Excel workbook
  data.py                    report loading and normalisation
  briefing.py                rule-based briefing and optional AI briefing
  records.py                 record ordering, labels and the readable table
  ui/
    design.py                tokens, status encoding, number and date formatting
    theme.py                 the page stylesheet, including the scroll-story motion
    components.py            status key, coverage bar, callouts, record sheet
    story.py                 hero sky, scroll statement, chapter heads, pinned scene, closing
    charts.py                Plotly figures and the shared dark template
tests/                       unit tests (run with python -m unittest discover -s tests)
docs/DEPLOYMENT.md           deployment notes
.streamlit/config.toml       base theme colours
.devcontainer/               optional GitHub Codespaces setup
CHANGELOG.md                 version-by-version history
```

## Test the agent and exports

Run tests from the project directory:

```bash
python -m unittest discover -s tests -v
```

These tests are software checks on synthetic or controlled examples. They are not evidence of scientific validity or real-world prediction performance.

## Public access and optional team sign-in

METEORWATCH is public by default. Visitors can explore the dashboard, historical records, maps, explanations, evaluation views, and public exports without creating an account.

An optional **Google sign-in** panel is available in the sidebar for team access. It uses Streamlit's native OpenID Connect (OIDC) support. A successful Google login verifies identity; a separate email allowlist in Streamlit secrets determines whether the account has the `team_member` or `admin` role. Admin accounts inherit team-member permissions. Unlisted or unverified accounts retain public access but do not receive a team role.

No private team tools are enabled yet. This release establishes the sign-in and role-check foundation for future restricted features; it does not make any existing public dashboard feature private.

Authentication is disabled until the Google OIDC settings are configured in Streamlit secrets. Never commit `.streamlit/secrets.toml`, OAuth client secrets, cookie secrets, or AI-provider keys to GitHub. See [deployment and Google sign-in setup](docs/DEPLOYMENT.md).

## API keys and secrets

Never commit API keys, passwords, `.env` files, or Streamlit secrets to GitHub. If using an optional external briefing provider, check the provider's current terms and account limits. A key entered into a hosted app is sent through that app's server to make the requested provider call; only enter a key when you trust the app operator and understand the provider's terms.

## Project history

Release-by-release changes belong in [`CHANGELOG.md`](CHANGELOG.md). Keep this README focused on the project's purpose, architecture, setup, and limitations; do not rewrite it for every small release.
