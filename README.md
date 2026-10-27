# METEORWATCH v5 — Searchable Historical Event Picker

This update improves the long event dropdown in both **Event Explorer** and **AI Briefing Assistant**. The same underlying dataset and briefing logic are retained.

## What's added

- **Search events** by date/year, energy, impact energy, altitude, review status, explanation, and available coordinates.
- **Year filter** to narrow the list to a specific calendar year.
- **Review-status filter** to show only a category such as Isolation Forest only, IQR baseline only, flagged by both, or not assessed.
- **Event date range** with GMT dates to narrow the historical period.
- **Sorting** by newest, oldest, highest energy, lowest energy, flagged records first, or most unusual Isolation Forest score.
- A visible count of how many records match the event-picker filters.

The new filters are local to each tab's event picker and are applied on top of the dashboard's existing sidebar filters. The actual event selector now contains only the records left after these filters.

## Deploy to the existing Streamlit app

1. Download and extract the ZIP.
2. In the GitHub repository connected to your Streamlit app, replace `app.py` and `requirements.txt` with these files.
3. **Keep `meteorwatch_full_review_report.csv` unchanged** in the root of the repository.
4. Commit the changes and wait for Streamlit Community Cloud to redeploy.
5. Open the **Event Explorer** tab and **AI Briefing Assistant** tab. Search for a year such as `2013`, use the year filter, set a date range, change the sorting, and confirm the event dropdown becomes shorter.
6. Generate a built-in no-API briefing to verify the selected event still flows into the existing briefing feature.

## Notes

- Existing API-provider options and the built-in no-API briefing are unchanged.
- The event sort called “Most unusual ML score” places more-negative Isolation Forest decision scores first. Rows without an ML score are placed at the end.
- Search and filters only help navigate the stored historical report. They do not retrieve new events from NASA/JPL.
- Event locations are reported peak-brightness locations, not confirmed impact sites; anomaly flags are review prompts, not danger predictions.

## Validation performed

- Python syntax compilation passed for `app.py`.
- The Streamlit UI has not been run against the live app from this environment. After deploying, manually check both event pickers and the built-in no-API briefing as listed above.
