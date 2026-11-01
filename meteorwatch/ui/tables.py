"""Arrow-safe preparation for Streamlit dataframe rendering."""
from __future__ import annotations

import pandas as pd


def prepare_display_table(frame: pd.DataFrame) -> pd.DataFrame:
    """Return a display copy with mixed-type object columns normalized to text.

    Streamlit/PyArrow cannot always infer a single Arrow type for object columns
    that mix values such as integers and percentage strings. Converting only
    those mixed columns to pandas' nullable string dtype preserves numeric
    columns, keeps missing values missing, and avoids mutating the source frame.
    """
    if not isinstance(frame, pd.DataFrame):
        raise TypeError("prepare_display_table expects a pandas DataFrame")

    display = frame.copy()
    for column_name in display.columns:
        column = display[column_name]
        if not pd.api.types.is_object_dtype(column.dtype):
            continue
        if column.dropna().map(type).nunique() > 1:
            display[column_name] = column.astype("string")
    return display
