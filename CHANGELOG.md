# Changelog

## Post-v13 maintenance — chart readability, endpoint hardening, and filter completeness

- Increased Plotly chart margins and enabled automatic axis margins so numerical and category tick labels have room to render, including in narrow dashboard columns.
- Added chart-layout regression tests for shared axis behaviour, the timeline, detector outcomes, and data completeness chart.
- Restricted OpenAI-compatible briefing requests to HTTPS endpoints on explicitly supported provider hosts and blocked redirects to reduce the risk of arbitrary server-side requests.
- Kept records with missing reported energy visible when the minimum-energy filter is used; the filter now applies only to records with a reported value, and the sidebar explains this behaviour.
- Updated the Streamlit theme comment to point to the reorganised UI stylesheet and ignored local virtual-environment folders.


Notable project changes are recorded here. This file tracks releases; `README.md` remains the stable overview of the project's purpose, transparent agent design, setup, and scientific limits.

## v13 — Scroll story and project reorganisation

- The app is now one scrolling story instead of tabs. It opens on a sky built from the catalogue itself: each star is one record, placed by date and log energy and coloured by review status. Six chapters follow (Sky, Map, Two ways to look closer, Look at a single fireball, Briefing, Check the checks), then a closing statement.
- Scroll motion, with no JavaScript: a hero that fades as you leave it, counters that count up, a statement whose words brighten as they scroll in, charts and cards that rise into view, a pinned title beside three scrolling steps, and falling meteors. Scroll-driven effects run in Chrome, Edge and Safari 26 or later; other browsers show the same content without them. All motion is off under reduced-motion settings.
- Map chapter: a flat map or a globe you can turn.
- The sidebar filters start collapsed and are described in the chapters they affect.
- Detector lab tabs, data quality and method and limits now sit together in the last chapter.
- Reorganised the files: analysis code moved into the `meteorwatch/` package (`agent`, `evaluation`, `sensitivity`, `exports`), the data loader and AI briefing code moved out of `app.py` (`data`, `briefing`, `records`), the interface moved into `meteorwatch/ui/`, tests moved into `tests/`, and the CSV moved into `data/`. `app.py` stays at the project root, so deployment settings do not change. The app still finds the CSV beside `app.py`.
- Removed the per-release deployment notes (`DEPLOY_V9.md`, `DEPLOY_V11.md`, `DEPLOY_V12.md`) in favour of one `docs/DEPLOYMENT.md`.
- `build_ai_prompt` no longer reads a global DataFrame; the catalogue counts are passed in.
- Unchanged: all analysis, agent, evaluation, sensitivity and export logic, every download, and every scientific limitation statement.

## v12 — Interface redesign

- New visual design. A twilight palette with one rule: colour is reserved for detector status (white-hot gold = both methods, ember = IQR baseline, ultraviolet = Isolation Forest, slate = not flagged). Hollow marks mean the Isolation Forest did not assess the record, so “not assessed” can no longer be mistaken for “not flagged”.
- New layout. A masthead and status key replace the six metric tiles; the status key counts follow the sidebar filters. A coverage bar shows how much of the catalogue the Isolation Forest could assess.
- Seven tabs became six: **Sky**, **Map**, **Records**, **Briefing**, **Detector lab**, **Data and method**. The Detector lab and Data and method tabs use sub-tabs instead of one long scroll.
- Records: click a row to open a record sheet (measurements with units, saved detector results, a globe centred on the reported location) and the rule-generated briefing. The Briefing tab opens the same record.
- Filters: one set of filters in the sidebar, plus a **Reset filters** button. The duplicate per-tab pickers were removed; each tab keeps an **Order by** control. Sidebar search now covers dates, energy values, status, explanations and coordinates (it previously covered dates and explanations).
- Charts: shared dark Plotly theme, a time-by-energy hero chart with the highest-energy record labelled, quarter-decade energy bins on the logarithmic scale, marker size by energy on the map, status-coloured outcome bars.
- Faster interaction: workbook, structured export, detector evaluation, sensitivity study and self-tests are cached, so selecting a row no longer rebuilds them.
- Streamlit compatibility: uses `width="stretch"` on current Streamlit and `use_container_width=True` on older releases; row selection needs Streamlit 1.35 or later and falls back to a dropdown otherwise.
- Removed because another view already covers them: the “Review status distribution” bar chart (the status key shows the same counts), the preview table on the old Overview tab (Records has the full table), and the “Dataset quality snapshot” table (Field completeness covers the same fields).
- Unchanged: all analysis, agent, evaluation, sensitivity and export code, every download, and every scientific limitation statement.
- Added `meteorwatch_ui.py`, `.streamlit/config.toml` and `test_meteorwatch_ui.py`.

## v11 — Isolation Forest score-threshold sensitivity study

- Added a sensitivity analysis using the already-saved Isolation Forest decision scores at 1%, 2.5%, 5%, 7.5%, 10%, and 15% contamination-style percentile cutoffs.
- Added selected-record counts, actual selected shares, overlap against the 5% reference, and counts of records added/removed relative to that reference.
- Added an event-level comparison CSV that keeps `Not assessed`, unknown assessment status, and unavailable scores explicit.
- Added a consistency check comparing the score-derived 5% reference with saved Isolation Forest flags.
- Added a `Sensitivity Study` sheet to the Excel workbook. This sheet reflects the full loaded catalogue, matching the Agent Test Lab; other workbook event sheets use the current filtered view.
- The study reuses saved scores only: it does not refit Isolation Forest, change saved flags, or claim detector accuracy. Ties at the score cutoff are handled with a strict less-than comparison.
- Added automated tests for eligible-row selection, missing states, tied scores, invalid settings, and unavailable studies.

## v10 — Detector coverage and agreement evaluation

- Added a Detector Evaluation section to the Agent Test Lab with baseline/ML coverage, comparable-record counts, four pairwise outcomes, observed agreement, Cohen's kappa, and Jaccard overlap of flagged records.
- Kept all agreement statistics explicitly separate from accuracy; the project does not have independently verified anomaly labels.
- Added event-level detector-comparison and summary CSV downloads, including visible saved-field inconsistencies and explicit non-comparable states.
- Preserved an unknown `ml_assessed` value as unknown when the field exists but is blank; a legacy fallback is used only when the field is absent entirely.
- Updated overview and Data Quality counters so explicitly `Not assessed` is separated from unknown assessment status.
- Added a `Detector Evaluation` sheet to the multi-sheet Excel workbook.
- Added `meteorwatch_evaluation.py` and automated tests for paired outcomes, missing assessment states, undefined metrics, and export labels.
- Updated the README's permanent agent architecture description; version-specific changes remain recorded here.

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
