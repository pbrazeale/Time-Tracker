from __future__ import annotations

from datetime import date, datetime, time
from typing import Optional

import re

import pandas as pd
import plotly.express as px

import db
from constants import (
    ACCENT_BLUE,
    CATEGORY_COLORS,
    LIGHT_TEXT,
    PRIMARY_RED,
)

_TIME_INPUT_PATTERN = re.compile(r"^\s*(\d{1,2}):(\d{2})(?::(\d{2}))?\s*$")


def init_db() -> None:
    db.init_db()


def current_time() -> datetime:
    return datetime.now(db.CENTRAL_TZ)


def parse_iso(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    return datetime.fromisoformat(ts)


def format_duration_hours(start_iso: str, end_iso: Optional[str]) -> float:
    start_dt = parse_iso(start_iso)
    end_dt = parse_iso(end_iso) or current_time()
    if not start_dt or not end_dt:
        return 0.0
    delta = end_dt - start_dt
    return round(delta.total_seconds() / 3600, 2)


def format_time_value(value: Optional[time]) -> str:
    base = (value or time(hour=0, minute=0)).replace(second=0, microsecond=0)
    return base.strftime("%H:%M")


def parse_time_text(raw: str) -> time:
    match = _TIME_INPUT_PATTERN.match(raw.strip())
    if not match:
        raise ValueError
    hour = int(match.group(1))
    minute = int(match.group(2))
    second_text = match.group(3)
    if not (0 <= hour < 24 and 0 <= minute < 60):
        raise ValueError
    if second_text and int(second_text) != 0:
        raise ValueError
    return time(hour=hour, minute=minute)


def time_from_datetime(value: Optional[datetime]) -> Optional[time]:
    if not value:
        return None
    localized = value.astimezone(db.CENTRAL_TZ) if value.tzinfo else value
    return localized.timetz().replace(tzinfo=None, second=0, microsecond=0)


def combine_date_time(selected_date: date, selected_time: time) -> str:
    combined = datetime.combine(selected_date, selected_time)
    return combined.replace(tzinfo=db.CENTRAL_TZ).isoformat()


def get_active_session():
    return db.get_active_session()


def start_session() -> None:
    db.start_session()


def end_session(session_id: int) -> None:
    db.end_session(session_id)


def get_active_project_entry(session_id: int):
    return db.get_active_project_entry(session_id=session_id)


def end_project_entry(entry_id: int) -> None:
    db.end_project_entry(entry_id)


def start_project_entry(session_id: int, project_name: str, category: str) -> None:
    db.start_project_entry(
        session_id=session_id,
        project_name=project_name,
        category=category,
    )


def get_categories(*, include_inactive: bool = False) -> list[str]:
    return db.get_categories(include_inactive=include_inactive)


def add_category(name: str) -> None:
    db.add_category(name)


def set_category_active(category: str, active: bool) -> None:
    db.set_category_active(category, active)


def rename_category(old_name: str, new_name: str) -> None:
    db.rename_category(old_name, new_name)


def get_all_sessions() -> list[dict]:
    return db.sessions_as_dicts(db.list_all_sessions())


def list_sessions_between(start_date: date, end_date: date) -> list[dict]:
    return db.sessions_as_dicts(db.list_sessions_between(start_date, end_date))


def update_session(**kwargs) -> None:
    db.update_session(**kwargs)


def delete_session(session_id: int) -> None:
    db.delete_session(session_id)


def get_all_project_entries() -> list[dict]:
    return db.entries_as_dicts(db.list_all_project_entries())


def add_manual_project_entry(**kwargs) -> None:
    db.add_manual_project_entry(**kwargs)


def list_project_entries_between(start_date: date, end_date: date) -> list[dict]:
    return db.entries_as_dicts(db.list_project_entries_between(start_date, end_date))


def get_today_entries_display(target_date: date) -> Optional[pd.DataFrame]:
    entries = list_project_entries_between(target_date, target_date)
    if not entries:
        return None
    df_entries = pd.DataFrame(entries)
    df_entries["hours"] = df_entries.apply(
        lambda row: format_duration_hours(row["start_time"], row["end_time"]),
        axis=1,
    )
    df_entries["start_display"] = df_entries["start_time"].apply(
        lambda value: parse_iso(value).strftime("%H:%M") if value else "",
    )
    df_entries["end_display"] = df_entries["end_time"].apply(
        lambda value: parse_iso(value).strftime("%H:%M") if value else "Running",
    )
    return df_entries[
        ["project_name", "category", "start_display", "end_display", "hours"]
    ].rename(
        columns={
            "start_display": "Start",
            "end_display": "End",
            "hours": "Hours",
        }
    )


def fetch_daily_hours_summary(start_date: date, end_date: date) -> tuple[pd.DataFrame, float]:
    sessions = list_sessions_between(start_date, end_date)
    if not sessions:
        return pd.DataFrame(), 0.0
    df_sessions = pd.DataFrame(sessions)
    if "total_hours" in df_sessions.columns:
        df_sessions["hours"] = df_sessions["total_hours"]
    else:
        df_sessions["hours"] = None
    missing_hours = df_sessions["hours"].isna()
    if missing_hours.any():
        df_sessions.loc[missing_hours, "hours"] = df_sessions.loc[missing_hours].apply(
            lambda row: format_duration_hours(row["start_time"], row["end_time"]),
            axis=1,
        )
    df_sessions["hours"] = pd.to_numeric(df_sessions["hours"], errors="coerce")
    chart_data = df_sessions.groupby("session_date")["hours"].sum().reset_index()
    chart_data["session_date"] = pd.to_datetime(chart_data["session_date"])
    chart_data["hour_total"] = chart_data["hours"].fillna(0)
    chart_data["session_label"] = chart_data["session_date"].dt.strftime("%b %d, %Y")
    total_hours = float(chart_data["hour_total"].sum())
    return chart_data, total_hours


def build_daily_hours_chart(chart_data: pd.DataFrame):
    fig = px.bar(
        chart_data,
        x="session_label",
        y="hour_total",
        labels={"session_label": "Date", "hour_total": "Hours"},
    )
    fig.update_traces(
        width=0.6,
        marker_color=PRIMARY_RED,
        marker_line_color=ACCENT_BLUE,
        marker_line_width=1.5,
    )
    fig.update_layout(
        bargap=0.25,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color=LIGHT_TEXT,
    )
    fig.update_xaxes(
        type="category",
        linecolor=ACCENT_BLUE,
        tickfont=dict(color=LIGHT_TEXT),
    )
    fig.update_yaxes(
        gridcolor="rgba(30, 63, 128, 0.35)",
        zerolinecolor="rgba(123, 31, 162, 0.3)",
        tickfont=dict(color=LIGHT_TEXT),
    )
    return fig


def fetch_category_breakdown(start_date: date, end_date: date) -> Optional[pd.DataFrame]:
    entries = list_project_entries_between(start_date, end_date)
    if not entries:
        return None
    df_entries = pd.DataFrame(entries)
    df_entries["hours"] = df_entries.apply(
        lambda row: format_duration_hours(row["start_time"], row["end_time"]),
        axis=1,
    )
    per_category = df_entries.groupby("category")["hours"].sum().reset_index()
    per_category["hours"] = pd.to_numeric(per_category["hours"], errors="coerce").fillna(0.0)
    total_category_hours = float(per_category["hours"].sum())
    if total_category_hours:
        per_category["percent"] = per_category["hours"] / total_category_hours
    else:
        per_category["percent"] = 0.0
    per_category["legend_label"] = [
        f"{category} ({percent * 100:.1f}%)"
        for category, percent in zip(per_category["category"], per_category["percent"])
    ]
    return per_category


def build_category_pie(per_category: pd.DataFrame):
    fig = px.pie(
        per_category,
        names="legend_label",
        values="hours",
        color_discrete_sequence=CATEGORY_COLORS,
    )
    fig.update_traces(
        customdata=per_category[["category", "percent"]].values,
        hovertemplate="<b>%{customdata[0]}</b><br>Hours: %{value:.2f}<br>Share: %{customdata[1]:.1%}",
        textinfo="percent",
        textposition="inside",
    )
    fig.update_layout(
        showlegend=True,
        legend_title_text="Category",
        legend_font_color=LIGHT_TEXT,
        legend_bgcolor="rgba(11, 17, 34, 0.6)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color=LIGHT_TEXT,
    )
    return fig


