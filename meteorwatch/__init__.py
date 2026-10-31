"""METEORWATCH: a review desk for historical NASA/JPL fireball records.

Analysis modules (no Streamlit dependency):
    agent        saved-flag interpretation, explanations, structured export, self-tests
    evaluation   detector agreement statistics
    sensitivity  Isolation Forest score-threshold sensitivity study
    exports      multi-sheet Excel workbook
    data         report loading and normalisation
    briefing     optional AI briefing prompt and provider calls

Interface:
    ui           design system: theme CSS, HTML components, scroll-story sections, Plotly charts
"""
