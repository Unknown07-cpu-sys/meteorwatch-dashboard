# Testing

The test suite checks that METEORWATCH handles incomplete input honestly, that the dashboard and downloadable reports use the same definitions, and that the interface remains usable across screen sizes.

## Run locally

```bash
pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

For browser layout checks:

```bash
playwright install chromium
RUN_BROWSER_TESTS=1 python -m unittest discover -s tests/browser -v
```

Live provider checks are opt-in and require a provider API key. Never commit keys or put them in test fixtures:

```bash
OPENROUTER_API_KEY=... python -m unittest discover -s tests/live -v
```

## Test layers

| Layer | What it checks | What it does not establish |
|---|---|---|
| Analysis logic | Saved flags, assessment states, sensitivity and evaluation calculations | Real-world detector accuracy |
| Input handling | CSV structure, dates, numeric values, coordinates and missing data | Validity of the original scientific measurements |
| Export consistency | CSV/XLSX contents against the filtered view and catalogue summaries | Scientific correctness of source data |
| AI provider contract | Request shape, endpoint restrictions, safe prompt fields and response handling | That a provider is online or accepts a model name today |
| Charts | Plotted records, status encoding, hover text and layout settings | Actual visual quality in every browser |
| Streamlit page | The real app script with real Streamlit and Plotly on normal and unusual reports | Visual quality |
| Browser | Overflow and clipping at phone, tablet, laptop and wide viewports | Whether the design is aesthetically successful |
| Live providers | An opt-in request using the user's own provider key | Quality across many events |

A passing software test means the code behaved as expected for that test case. It does not mean an anomaly flag is a verified physical anomaly or hazard.

## CI

GitHub Actions runs the standard tests on pushes and pull requests using Python 3.11 and 3.12. The browser job runs after the unit job and uploads screenshots as an artifact. Review those screenshots manually after a successful run.
