"""Plotly figures and the shared dark chart template."""
from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from meteorwatch.ui.design import (
    DECK_2,
    DIM,
    FAINT,
    LAND,
    LINE,
    OCEAN,
    PLOT_DISPLAY_FONT,
    PLOT_FONT,
    SKY,
    TEXT,
    esc,
    fmt_amount,
    fmt_day,
    fmt_stamp,
    is_hollow,
    is_missing,
    ordered_statuses,
    status_color,
)


# ---------------------------------------------------------------------------
# Plotly
# ---------------------------------------------------------------------------

def _build_template() -> go.layout.Template:
    axis = dict(
        gridcolor="rgba(124,134,179,0.16)",
        linecolor="rgba(124,134,179,0.45)",
        zeroline=False,
        ticks="outside",
        tickcolor="rgba(124,134,179,0.45)",
        tickfont=dict(size=12, color=DIM),
        title=dict(font=dict(size=12.5, color=DIM)),
        automargin=True,
    )
    layout = go.Layout(
        font=dict(family=PLOT_FONT, color=TEXT, size=13),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        colorway=[TEXT, DIM, FAINT, "#8FA0E0"],
        xaxis=axis,
        yaxis=axis,
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=12, color=DIM)),
        hoverlabel=dict(
            bgcolor=DECK_2,
            bordercolor=LINE,
            font=dict(family=PLOT_FONT, size=13, color=TEXT),
            align="left",
        ),
        margin=dict(l=76, r=24, t=20, b=28),
        title=dict(font=dict(family=PLOT_DISPLAY_FONT, size=16, color=TEXT)),
    )
    return go.layout.Template(layout=layout)


TEMPLATE = _build_template()
PLOT_CONFIG = {"displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d"]}


def _new_fig() -> go.Figure:
    return go.Figure(layout=go.Layout(template=TEMPLATE))


def _marker(status: Any, size: Any, opacity: float = 0.92) -> dict[str, Any]:
    color = status_color(status)
    if is_hollow(status):
        return dict(size=size, color="rgba(0,0,0,0)", opacity=0.95, line=dict(color=color, width=1.7))
    return dict(size=size, color=color, opacity=opacity, line=dict(color="rgba(18,26,51,0.9)", width=0.6))


def _column(frame: pd.DataFrame, name: str) -> pd.Series:
    if name in frame.columns:
        return frame[name]
    return pd.Series(np.nan, index=frame.index, dtype="float64")


def _hover_texts(frame: pd.DataFrame) -> list[str]:
    def val(value: Any, unit: str, digits: int | None = None) -> str:
        text = fmt_amount(value, digits)
        return f"{text} {unit}".strip() if text is not None else "not reported"

    out = []
    for ts, energy, impact, alt, speed, status in zip(
        _column(frame, "date"),
        _column(frame, "energy"),
        _column(frame, "impact-e"),
        _column(frame, "alt"),
        _column(frame, "component_speed"),
        _column(frame, "review_status"),
    ):
        out.append(
            f"<b>{esc(fmt_stamp(ts))}</b><br>"
            f"Energy: {val(energy, '×10¹⁰ J')}<br>"
            f"Impact energy: {val(impact, 'kt')}<br>"
            f"Altitude: {val(alt, 'km', 1)}<br>"
            f"Speed: {val(speed, 'km/s', 1)}<br>"
            f"{esc(str(status))}"
        )
    return out


def _log_ticks(low: float, high: float) -> tuple[list[float], list[str]]:
    start = math.floor(math.log10(low))
    stop = math.ceil(math.log10(high))
    values = [10.0 ** k for k in range(start, stop + 1)]
    labels = [f"{v:,.0f}" if v >= 1 else f"{v:g}" for v in values]
    return values, labels


def timeline_figure(frame: pd.DataFrame) -> go.Figure | None:
    """Hero chart: every record by date (x) and reported energy (y, log)."""
    data = frame.dropna(subset=["date", "energy"])
    data = data[data["energy"] > 0].copy()
    if data.empty:
        return None
    data["_hover"] = _hover_texts(data)
    fig = _new_fig()
    for status in ordered_statuses(data["review_status"]):
        sub = data[data["review_status"].astype(str) == status]
        fig.add_trace(
            go.Scatter(
                x=sub["date"],
                y=sub["energy"],
                mode="markers",
                name=status,
                text=sub["_hover"],
                hovertemplate="%{text}<extra></extra>",
                marker=_marker(status, 8),
            )
        )

    top = data.loc[data["energy"].idxmax()]
    span_start, span_end = data["date"].min(), data["date"].max()
    span = (span_end - span_start).total_seconds()
    fraction = (top["date"] - span_start).total_seconds() / span if span > 0 else 0.5
    to_left = fraction > 0.6
    fig.add_annotation(
        x=top["date"].strftime("%Y-%m-%d %H:%M:%S"),
        y=math.log10(float(top["energy"])),
        text=f"Highest energy in view: {fmt_amount(top['energy'])} ×10¹⁰ J, {fmt_day(top['date'])}",
        showarrow=True,
        arrowhead=0,
        arrowwidth=1,
        arrowcolor=FAINT,
        ax=-46 if to_left else 46,
        ay=6,
        xanchor="right" if to_left else "left",
        yanchor="middle",
        font=dict(size=12, color=DIM),
    )

    tick_values, tick_text = _log_ticks(float(data["energy"].min()), float(data["energy"].max()))
    fig.update_layout(
        height=470,
        hovermode="closest",
        margin=dict(l=104, r=28, t=28, b=30),
        legend=dict(orientation="h", x=0, y=-0.12, yanchor="top"),
        xaxis=dict(title=dict(text=""), showgrid=False),
        yaxis=dict(
            type="log",
            tickvals=tick_values,
            ticktext=tick_text,
            title=dict(text="Reported energy (×10¹⁰ J), log scale"),
        ),
    )
    return fig


def energy_histogram_figure(frame: pd.DataFrame) -> go.Figure | None:
    """Quarter-decade bins so the bars match the logarithmic idea of the axis."""
    energy = frame["energy"].dropna()
    energy = energy[energy > 0]
    if energy.empty:
        return None
    logs = np.log10(energy.to_numpy(dtype=float))
    step = 0.25
    low = math.floor(logs.min() / step) * step
    high = max(math.ceil(logs.max() / step) * step, low + step)
    edges = np.arange(low, high + step / 2, step)
    counts, _ = np.histogram(logs, bins=edges)
    centers = edges[:-1] + step / 2
    labels = [
        f"{fmt_amount(10 ** a)} to {fmt_amount(10 ** b)} ×10¹⁰ J"
        for a, b in zip(edges[:-1], edges[1:])
    ]
    fig = _new_fig()
    fig.add_trace(
        go.Bar(
            x=centers,
            y=counts,
            width=step * 0.9,
            customdata=labels,
            marker=dict(color=DIM, line=dict(width=0)),
            hovertemplate="%{customdata}<br>%{y} records<extra></extra>",
        )
    )
    ticks = list(range(math.ceil(low), math.floor(high) + 1))
    fig.update_layout(
        height=300,
        bargap=0.05,
        xaxis=dict(
            tickvals=ticks,
            ticktext=[f"{10.0 ** k:,.0f}" if k >= 0 else f"{10.0 ** k:g}" for k in ticks],
            title=dict(text="Reported energy (×10¹⁰ J), log scale"),
            showgrid=False,
        ),
        yaxis=dict(title=dict(text="Records")),
    )
    return fig


def _size_from_energy(energy: pd.Series) -> np.ndarray:
    values = np.clip(energy.to_numpy(dtype=float), 0.01, None)
    return np.clip(5 + 3 * np.log10(values / 0.1), 5, 22)


def _style_geo(fig: go.Figure, **extra: Any) -> None:
    fig.update_geos(
        showland=True,
        landcolor=LAND,
        showocean=True,
        oceancolor=OCEAN,
        showlakes=False,
        showcountries=True,
        countrycolor=LINE,
        showcoastlines=True,
        coastlinecolor="#4A5A9C",
        coastlinewidth=0.6,
        showframe=False,
        bgcolor="rgba(0,0,0,0)",
        lonaxis_showgrid=True,
        lonaxis_gridcolor="rgba(124,134,179,0.18)",
        lonaxis_dtick=30,
        lataxis_showgrid=True,
        lataxis_gridcolor="rgba(124,134,179,0.18)",
        lataxis_dtick=30,
        **extra,
    )


def map_figure(frame: pd.DataFrame, globe: bool = False, centre_lon: float = 0.0) -> go.Figure | None:
    """Flat map, or a globe turned to ``centre_lon``."""
    rows = frame.dropna(subset=["map_latitude", "map_longitude"]).copy()
    if rows.empty:
        return None
    rows["_hover"] = _hover_texts(rows)
    fig = _new_fig()
    for status in ordered_statuses(rows["review_status"]):
        sub = rows[rows["review_status"].astype(str) == status]
        sizes = _size_from_energy(sub["energy"]) if "energy" in sub.columns else 8
        fig.add_trace(
            go.Scattergeo(
                lat=sub["map_latitude"],
                lon=sub["map_longitude"],
                mode="markers",
                name=status,
                text=sub["_hover"],
                hovertemplate="%{text}<extra></extra>",
                marker=_marker(status, sizes, opacity=0.85),
            )
        )
    if globe:
        _style_geo(fig, projection_type="orthographic", projection_rotation=dict(lon=centre_lon, lat=15))
    else:
        _style_geo(fig, projection_type="natural earth")
    fig.update_layout(
        height=620 if globe else 560,
        margin=dict(l=0, r=0, t=0, b=0),
        legend=dict(orientation="h", x=0, y=-0.02, yanchor="top"),
    )
    return fig


def locator_figure(lat: float, lon: float, status: Any) -> go.Figure:
    """A small globe centred on one record."""
    fig = _new_fig()
    fig.add_trace(
        go.Scattergeo(
            lat=[lat],
            lon=[lon],
            mode="markers",
            marker=_marker(status, 14, opacity=1.0),
            hoverinfo="skip",
            showlegend=False,
        )
    )
    _style_geo(
        fig,
        projection_type="orthographic",
        projection_rotation=dict(lon=lon, lat=lat),
    )
    fig.update_layout(height=300, margin=dict(l=0, r=0, t=0, b=0))
    return fig


def outcome_figure(outcomes: pd.DataFrame) -> go.Figure:
    """Pairwise detector outcomes, coloured by the status each outcome corresponds to."""
    names = outcomes["Pairwise outcome"].astype(str).tolist()
    counts = outcomes["Comparable records"].astype(int).tolist()
    fig = _new_fig()
    fig.add_trace(
        go.Bar(
            y=names,
            x=counts,
            orientation="h",
            marker=dict(color=[status_color(n) for n in names]),
            text=[f"{c:,}" for c in counts],
            textposition="outside",
            textfont=dict(color=TEXT),
            cliponaxis=False,
            hovertemplate="%{y}<br>%{x:,} comparable records<extra></extra>",
        )
    )
    fig.update_layout(
        height=max(240, 62 * len(names)),
        margin=dict(l=210, r=52, t=14, b=30),
        xaxis=dict(title=dict(text="Comparable records"), showgrid=True),
        yaxis=dict(autorange="reversed", showgrid=False, ticks="", automargin=True),
    )
    return fig


def sensitivity_figure(summary: pd.DataFrame) -> go.Figure:
    x_col, y_col = "Score threshold setting (%)", "Records flagged"
    fig = _new_fig()
    fig.add_trace(
        go.Scatter(
            x=summary[x_col],
            y=summary[y_col],
            mode="lines+markers",
            line=dict(color=DIM, width=2),
            marker=dict(size=9, color=SKY, line=dict(color=TEXT, width=2)),
            hovertemplate="%{x}% cutoff<br>%{y:,} records selected<extra></extra>",
            showlegend=False,
        )
    )
    reference = summary[summary[x_col] == 5]
    if not reference.empty:
        fig.add_trace(
            go.Scatter(
                x=reference[x_col],
                y=reference[y_col],
                mode="markers",
                name="5% reference setting",
                marker=dict(size=13, color=TEXT),
                hovertemplate="5% reference<br>%{y:,} records selected<extra></extra>",
            )
        )
    fig.update_layout(
        height=340,
        legend=dict(orientation="h", x=0, y=1.12, yanchor="bottom"),
        xaxis=dict(title=dict(text="Contamination-style score threshold (%)")),
        yaxis=dict(title=dict(text="Records selected for review"), rangemode="tozero", automargin=True),
    )
    return fig


def completeness_figure(completeness: pd.DataFrame) -> go.Figure:
    data = completeness.sort_values("Missing (%)", ascending=False)
    fig = _new_fig()
    fig.add_trace(
        go.Bar(
            y=data["Field"],
            x=data["Missing (%)"],
            orientation="h",
            marker=dict(color=DIM),
            text=[f"{v:.1f}%" for v in data["Missing (%)"]],
            textposition="outside",
            textfont=dict(color=TEXT),
            cliponaxis=False,
            hovertemplate="%{y}<br>%{x:.1f}% missing<extra></extra>",
        )
    )
    fig.update_layout(
        height=max(340, 34 * len(data) + 60),
        margin=dict(l=160, r=58, t=14, b=30),
        xaxis=dict(range=[0, 108], title=dict(text="Missing values (%)")),
        yaxis=dict(autorange="reversed", showgrid=False, ticks=""),
    )
    return fig
