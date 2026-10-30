"""Layout helper to prevent Plotly axis labels from being clipped in Streamlit.

Add this module beside app.py, import apply_axis_visibility, and wrap each
Plotly figure immediately before passing it to st.plotly_chart.
"""
from __future__ import annotations

from typing import Any


def apply_axis_visibility(
    fig: Any,
    *,
    left_margin: int = 105,
    right_margin: int = 36,
    top_margin: int = 64,
    bottom_margin: int = 58,
) -> Any:
    """Apply responsive margins and automatic axis-label spacing to a Plotly figure.

    Args:
        fig: A Plotly Express or graph_objects Figure.
        left_margin: Space for y-axis tick values and title. Increase for long labels.
        right_margin: Right-side padding.
        top_margin: Space for the chart title.
        bottom_margin: Space for x-axis tick labels and title.

    Returns:
        The same figure, updated in place, for convenient use with Streamlit.
    """
    if not hasattr(fig, "update_layout") or not hasattr(fig, "update_yaxes"):
        raise TypeError("fig must be a Plotly Figure with update_layout/update_yaxes methods")

    # Let Plotly reserve space for long tick labels and axis titles rather than
    # drawing them outside the chart's available area.
    fig.update_xaxes(
        automargin=True,
        title_standoff=14,
        ticklabeloverflow="allow",
    )
    fig.update_yaxes(
        automargin=True,
        title_standoff=14,
        ticklabeloverflow="allow",
    )
    fig.update_layout(
        autosize=True,
        margin={
            "l": max(60, int(left_margin)),
            "r": max(20, int(right_margin)),
            "t": max(48, int(top_margin)),
            "b": max(42, int(bottom_margin)),
            "pad": 6,
        },
    )
    return fig
