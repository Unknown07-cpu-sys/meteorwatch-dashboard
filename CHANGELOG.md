# Changelog

Notable project changes are recorded here. This file tracks releases; `README.md` remains the stable overview of the project's purpose, transparent agent design, setup, and scientific limits.

## v9 — Multi-sheet Excel reporting and documentation structure

- Added a formatted `.xlsx` workbook download in Event Explorer.
- Workbook contains `Start Here`, `Event Review`, `Technical Data`, `Data Quality`, `Review Status`, and `Agent Tests` sheets.
- Workbook reflects the current filtered view and explains its scope, data gaps, synthetic-test purpose, and interpretation boundaries.
- Added `meteorwatch_exports.py` and workbook export tests.
- Added XlsxWriter to the runtime dependencies.
- Established a permanent project README that describes the agent and a separate changelog for version history.
- Preserved the structured CSV and technical CSV downloads.

## v8 — Structured CSV exports

- Added a human-oriented event review CSV with readable columns, measurement units, saved detector results, explanations, missing-data notes, and suggested review action.
- Preserved a separate technical CSV export.
- Made `Not assessed` explicit when the Isolation Forest result was unavailable.
- Sorted the structured report by review workflow category, not physical danger.

## v7 — Agent explanations and test lab

- Added a transparent explanation layer for saved baseline and Isolation Forest flags.
- Added synthetic logic test cases and a saved-status consistency audit.
- Kept incomplete model assessment separate from a negative model result.

## v6 — Data quality checks

- Added a data-quality view for field completeness, missing values, model coverage and structural checks.
- Added a `.gitignore` rule set for Python cache files, virtual environments, and secrets.

## v5 — Event search and filtering

- Improved event selection with searchable event records, date/year filters, review status and energy-related sorting options.

## v4 — AI briefing provider options

- Added options for a built-in rule-based briefing and configurable external AI-provider access.
- Kept the external briefing separate from the statistical detector; an LLM response is not treated as model validation.

## v3 — Event briefing assistant

- Added an optional natural-language briefing workflow for a selected historical event.

## v2 — Map and methods context

- Added an event map where coordinates are available, an event explorer, and clearer method/limitations information.
- Clarified that mapped coordinates represent reported peak-brightness locations, not confirmed impact sites.

## v1 — Core dashboard

- Established the first historical-fireball dashboard using the prepared NASA/JPL report data, charts, event fields, and saved review outputs.
- Defined the scope as historical analysis and educational review, not future-impact prediction or operational warnings.
