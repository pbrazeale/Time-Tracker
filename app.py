from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Optional

import re

import pandas as pd
import plotly.express as px
import streamlit as st

import db


PRIMARY_RED = "#c62828"
ACCENT_BLUE = "#1e3a8a"
ROYAL_PURPLE = "#7b1fa2"
LIGHT_TEXT = "#f5f5f7"
CATEGORY_COLORS = [
    PRIMARY_RED,
    ACCENT_BLUE,
    ROYAL_PURPLE,
    "#ff7043",
    "#2563eb",
    "#a855f7",
]

THEME_STYLE = f"""
<style>
:root {{
    --primary-red: {{PRIMARY_RED}};
    --accent-blue: {{ACCENT_BLUE}};
    --royal-purple: {{ROYAL_PURPLE}};
    --text-light: {{LIGHT_TEXT}};
}}

[data-testid="stAppViewContainer"] {{
    background: radial-gradient(circle at top, rgba(198, 40, 40, 0.92), rgba(11, 17, 34, 0.98));
    color: var(--text-light);
}}

[data-testid="stHeader"] {{
    background: rgba(7, 10, 18, 0.85);
    border-bottom: 1px solid var(--accent-blue);
}}

[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, rgba(30, 63, 128, 0.96), rgba(123, 31, 162, 0.88));
}}

[data-testid="stSidebar"] * {{
    color: var(--text-light) !important;
}}

.sidebar-app-title {{
    text-align: center;
    font-weight: 700;
    font-size: 1.4rem;
    margin: 0.5rem 0 0.75rem;
    letter-spacing: 0.03em;
}}

.sidebar-divider {{
    height: 1px;
    margin: 0.75rem 0 1.25rem;
    background: linear-gradient(90deg, transparent, var(--accent-blue), transparent);
}}

.stButton>button, .stDownloadButton>button {{
    background-color: var(--primary-red);
    color: #ffffff;
    border: 1px solid rgba(37, 99, 235, 0.55);
    border-radius: 6px;
    transition: background-color 0.2s ease, border-color 0.2s ease, transform 0.2s ease;
}}

.stButton>button:hover, .stDownloadButton>button:hover {{
    background-color: var(--royal-purple);
    border-color: var(--royal-purple);
    transform: translateY(-1px);
}}

.stButton>button:focus, .stDownloadButton>button:focus {{
    box-shadow: 0 0 0 0.2rem rgba(123, 31, 162, 0.35);
    outline: none;
}}

h1, h2, h3, h4 {{
    color: var(--accent-blue);
}}

h1 {{
    text-shadow: 0 0 12px rgba(198, 40, 40, 0.45);
}}

h2 {{
    border-left: 4px solid var(--primary-red);
    padding-left: 0.6rem;
    margin-top: 0.75rem;
}}

[data-testid="stMetricLabel"], [data-testid="stMetricValue"] {{
    color: var(--text-light) !important;
}}

[data-testid="stDataFrame"] div[data-testid="styled-table"] {{
    background-color: rgba(30, 63, 128, 0.08);
    border-radius: 6px;
}}

div[data-testid="stAlert"] {{
    border-radius: 8px;
    border-left: 4px solid var(--royal-purple);
}}

.stTabs [data-baseweb="tab-list"] button[role="tab"] {{
    color: var(--text-light);
}}
</style>
"""

st.set_page_config(
    page_title="Time Tracker",
    layout="wide",
    page_icon="time_tracker_logo_300.jpg",
)

st.sidebar.image("time_tracker_logo_300.jpg", use_column_width=True)
st.sidebar.markdown(
    "<div class='sidebar-app-title'>Time Tracker</div>"
    "<div class='sidebar-divider'></div>",
    unsafe_allow_html=True,
)

st.markdown(THEME_STYLE, unsafe_allow_html=True)


db.init_db()


def _now() -> datetime:
    return datetime.now(db.CENTRAL_TZ)


def _parse_iso(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    return datetime.fromisoformat(ts)


def _format_duration_hours(start_iso: str, end_iso: Optional[str]) -> float:
    start_dt = _parse_iso(start_iso)
    end_dt = _parse_iso(end_iso) or _now()
    if not start_dt or not end_dt:
        return 0.0
    delta = end_dt - start_dt
    return round(delta.total_seconds() / 3600, 2)


def _format_time_value(value: Optional[time]) -> str:
    base = (value or time(hour=0, minute=0)).replace(second=0, microsecond=0)
    return base.strftime("%H:%M")


_TIME_INPUT_PATTERN = re.compile(r"^\s*(\d{1,2}):(\d{2})(?::(\d{2}))?\s*$")


def _time_text_input(label: str, default: Optional[time] = None, *, key: Optional[str] = None) -> str:
    return st.text_input(label, value=_format_time_value(default), key=key)



def _parse_time_text(raw: str) -> time:
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



def _time_from_datetime(value: Optional[datetime]) -> Optional[time]:
    if not value:
        return None
    localized = value.astimezone(db.CENTRAL_TZ) if value.tzinfo else value
    return localized.timetz().replace(tzinfo=None, second=0, microsecond=0)


def render_tracker() -> None:
    st.header("Daily Tracker")
    today = _now().date()
    st.subheader(f"Today: {today.isoformat()}")

    active_session = db.get_active_session()

    col1, col2 = st.columns(2)

    with col1:
        if active_session:
            if st.button("Stop Day", type="primary"):
                db.end_session(active_session.id)
                st.toast("Day stopped")
                st.rerun()
        else:
            if st.button("Start Day", type="primary"):
                db.start_session()
                st.toast("New workday started")
                st.rerun()

    with col2:
        if active_session:
            start_dt = _parse_iso(active_session.start_time)
            st.metric(
                "Day Started",
                f"{start_dt.strftime('%I:%M %p')} CST" if start_dt else "",
            )
        else:
            st.info("No active workday. Start the day to begin tracking time.")

    st.divider()
    if active_session:
        st.subheader("Project Time Tracking")
        active_entry = db.get_active_project_entry(session_id=active_session.id)

        if active_entry:
            entry_duration = _format_duration_hours(
                active_entry.start_time, active_entry.end_time
            )
            st.success(
                f"Tracking '{active_entry.project_name}' in {active_entry.category}"
            )
            started_at = _parse_iso(active_entry.start_time)
            if started_at:
                st.write(
                    f"Started at: {started_at.strftime('%I:%M %p')} CST"
                )
            st.write(f"Elapsed hours: {entry_duration}")
            if st.button("Stop Project Entry"):
                db.end_project_entry(active_entry.id)
                st.toast("Project entry stopped")
                st.rerun()
        else:
            with st.form("project_entry"):
                project_name = st.text_input("Project name")
                categories = db.get_categories()
                if categories:
                    default_index = categories.index("Programming") if "Programming" in categories else 0
                    category = st.selectbox("Category", categories, index=default_index)
                else:
                    category = st.selectbox("Category", categories)
                submitted = st.form_submit_button("Start Project Entry")

                if submitted:
                    if not project_name.strip():
                        st.warning("Project name is required")
                    else:
                        db.start_project_entry(
                            session_id=active_session.id,
                            project_name=project_name.strip(),
                            category=category,
                        )
                        st.toast("Project tracking started")
                        st.rerun()
    else:
        st.info("Start your day to begin logging project time.")

    st.divider()

    st.subheader("Today's Entries")
    today_entries = db.list_project_entries_between(today, today)
    if today_entries:
        entries = pd.DataFrame(db.entries_as_dicts(today_entries))
        entries["hours"] = entries.apply(
            lambda row: _format_duration_hours(row["start_time"], row["end_time"]),
            axis=1,
        )
        entries["start_display"] = entries["start_time"].apply(
            lambda x: _parse_iso(x).strftime("%H:%M") if x else ""
        )
        entries["end_display"] = entries["end_time"].apply(
            lambda x: _parse_iso(x).strftime("%H:%M") if x else "Running"
        )
        display_df = entries[
            ["project_name", "category", "start_display", "end_display", "hours"]
        ].rename(
            columns={
                "start_display": "Start",
                "end_display": "End",
                "hours": "Hours",
            }
        )
        st.dataframe(display_df, use_container_width=True)
    else:
        st.write("No project entries logged yet today.")

def _get_date_range() -> tuple[date, date]:
    end_date = _now().date()
    days_since_sunday = (end_date.weekday() + 1) % 7
    start_date = end_date - timedelta(days=days_since_sunday)
    col1, col2 = st.columns(2)
    with col1:
        selected_start = st.date_input("Start date", value=start_date)
    with col2:
        selected_end = st.date_input(
            "End date", value=end_date, min_value=selected_start
        )
    if selected_start > selected_end:
        st.warning("Start date is after end date; using a single-day range")
        selected_end = selected_start
    return selected_start, selected_end


def render_reports() -> None:
    st.header("Reports")

    if "reports_view_mode" not in st.session_state:
        st.session_state["reports_view_mode"] = "chart"

    controls_col = st.columns([3, 1])
    with controls_col[1]:
        view_mode = st.radio(
            "View mode",
            ["chart", "table"],
            key="reports_view_mode",
            horizontal=True,
            label_visibility="collapsed",
        )
    show_raw = view_mode == "table"

    start_date, end_date = _get_date_range()

    sessions = db.list_sessions_between(start_date, end_date)
    df_sessions = pd.DataFrame(db.sessions_as_dicts(sessions))

    if not df_sessions.empty:
        if "total_hours" in df_sessions.columns:
            df_sessions["hours"] = df_sessions["total_hours"]
        else:
            df_sessions["hours"] = None
        missing_hours = df_sessions["hours"].isna()
        if missing_hours.any():
            df_sessions.loc[missing_hours, "hours"] = df_sessions.loc[missing_hours].apply(
                lambda row: _format_duration_hours(row["start_time"], row["end_time"]),
                axis=1,
            )
        df_sessions["hours"] = pd.to_numeric(df_sessions["hours"], errors="coerce")
        chart_data = df_sessions.groupby("session_date")["hours"].sum().reset_index()
        chart_data["session_date"] = pd.to_datetime(chart_data["session_date"])
        chart_data["hour_total"] = chart_data["hours"].fillna(0)
        chart_data["session_label"] = chart_data["session_date"].dt.strftime("%b %d, %Y")
        st.subheader("Daily Hours Worked")
        total_hours = chart_data["hour_total"].fillna(0).sum()
        st.write(f"Total Hours: {total_hours:.2f}")
        if show_raw:
            st.caption("Raw database view")
            display_df = chart_data[["session_label", "hour_total"]].rename(
                columns={"session_label": "Date", "hour_total": "Hours"}
            )
            st.dataframe(display_df, use_container_width=True)
        else:
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
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No work sessions in the selected range.")

    st.divider()

    entries = db.list_project_entries_between(start_date, end_date)
    df_entries = pd.DataFrame(db.entries_as_dicts(entries))
    st.subheader("Work Categories")
    if not df_entries.empty:
        df_entries["hours"] = df_entries.apply(
            lambda row: _format_duration_hours(row["start_time"], row["end_time"]),
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
        if show_raw:
            st.caption("Raw database view")
            display_categories = per_category[["category", "hours"]].rename(
                columns={"category": "Category", "hours": "Hours"}
            )
            display_categories.loc[:, "Hours"] = display_categories["Hours"].round(2)
            st.dataframe(display_categories, use_container_width=True)
        else:
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
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No project entries in the selected range for category chart.")


def _combine_date_time(selected_date: date, selected_time: time) -> str:
    dt = datetime.combine(selected_date, selected_time)
    return dt.replace(tzinfo=db.CENTRAL_TZ).isoformat()


def render_admin() -> None:
    st.header("Admin Dashboard")
    st.write("Make manual adjustments to your data and manage categories.")

    st.subheader("Categories")
    categories_all = db.get_categories(include_inactive=True)
    active_categories = set(db.get_categories(include_inactive=False))

    col1, col2 = st.columns(2)
    with col1:
        new_category = st.text_input("Add new category")
        if st.button("Add Category"):
            if not new_category.strip():
                st.warning("Category name cannot be empty")
            else:
                db.add_category(new_category.strip())
                st.toast("Category added")
                st.rerun()

    with col2:
        if categories_all:
            selected_category = st.selectbox("Select category", categories_all)
            is_active = selected_category in active_categories
            st.write(f"Status: {'Active' if is_active else 'Inactive'}")
            if is_active:
                if st.button("Deactivate", key="deactivate_category"):
                    db.set_category_active(selected_category, False)
                    st.toast("Category deactivated")
                    st.rerun()
            else:
                if st.button("Activate", key="activate_category"):
                    db.set_category_active(selected_category, True)
                    st.toast("Category activated")
                    st.rerun()
            new_name = st.text_input("Rename category", value=selected_category)
            if st.button("Rename", key="rename_category_btn"):
                if not new_name.strip():
                    st.warning("New category name cannot be empty")
                elif new_name.strip() != selected_category:
                    db.rename_category(selected_category, new_name.strip())
                    st.toast("Category renamed")
                    st.rerun()
        else:
            st.info("No categories found.")

    st.divider()

    st.subheader("Work Sessions")
    sessions = db.sessions_as_dicts(db.list_all_sessions())
    if sessions:
        df_sessions = pd.DataFrame(sessions)
        st.dataframe(df_sessions, use_container_width=True)
        session_options = {
            f"#{row['id']} - {row['session_date']}": row for row in sessions
        }
        selected_label = st.selectbox(
            "Select session to edit", [""] + list(session_options.keys())
        )
        if selected_label:
            row = session_options[selected_label]
            start_dt = _parse_iso(row["start_time"])
            end_dt = _parse_iso(row["end_time"])
            with st.form(f"session_edit_{row['id']}"):
                base_date = start_dt.date() if start_dt else _now().date()
                edit_date = st.date_input("Session date", value=base_date)
                start_time_raw = _time_text_input(
                    "Start time",
                    default=_time_from_datetime(start_dt),
                    key=f"session_start_time_{row['id']}",
                )
                running = end_dt is None
                running = st.checkbox("Session in progress", value=running)
                end_time_raw: Optional[str] = None
                if not running:
                    end_time_raw = _time_text_input(
                        "End time",
                        default=_time_from_datetime(end_dt) or _time_from_datetime(start_dt),
                        key=f"session_end_time_{row['id']}",
                    )
                notes_val = st.text_area("Notes", value=row.get("notes") or "")
                submitted = st.form_submit_button("Update Session")
                if submitted:
                    try:
                        start_time_val = _parse_time_text(start_time_raw)
                        end_time_val = _parse_time_text(end_time_raw) if not running else None
                    except ValueError:
                        st.error("Time must be in HH:MM format.")
                        st.stop()
                    start_iso = _combine_date_time(edit_date, start_time_val)
                    end_iso = None if running else _combine_date_time(edit_date, end_time_val)
                    db.update_session(
                        session_id=row["id"],
                        session_date=edit_date.isoformat(),
                        start_time=start_iso,
                        end_time=end_iso,
                        notes=notes_val or None,
                    )
                    st.toast("Session updated")
                    st.rerun()
            if st.button("Delete Session", key=f"delete_session_{row['id']}"):
                db.delete_session(row["id"])
                st.toast("Session deleted")
                st.rerun()
    else:
        st.info("No sessions recorded yet.")

    st.divider()
    st.subheader("Project Entries")
    entries = db.entries_as_dicts(db.list_all_project_entries())
    if entries:
        df_entries = pd.DataFrame(entries)
        st.dataframe(df_entries, use_container_width=True)
        entry_options = {
            f"#{row['id']} - {row['project_name']}": row for row in entries
        }
        selected_entry_label = st.selectbox(
            "Select entry to edit", [""] + list(entry_options.keys())
        )
        if selected_entry_label:
            row = entry_options[selected_entry_label]
            start_dt = _parse_iso(row["start_time"])
            end_dt = _parse_iso(row["end_time"])
            categories_for_select = db.get_categories(include_inactive=True)
            default_index = (
                categories_for_select.index(row["category"])
                if row["category"] in categories_for_select
                else 0
            )
            with st.form(f"entry_edit_{row['id']}"):
                project_name = st.text_input("Project name", value=row["project_name"])
                category = st.selectbox(
                    "Category", categories_for_select, index=default_index
                )
                entry_date = (
                    start_dt.date() if start_dt else _now().date()
                )
                start_time_raw = _time_text_input(
                    "Start time",
                    default=_time_from_datetime(start_dt),
                    key=f"entry_start_time_{row['id']}",
                )
                running = end_dt is None
                running = st.checkbox("Entry in progress", value=running)
                end_time_raw: Optional[str] = None
                if not running:
                    end_time_raw = _time_text_input(
                        "End time",
                        default=_time_from_datetime(end_dt) or _time_from_datetime(start_dt),
                        key=f"entry_end_time_{row['id']}",
                    )
                submitted = st.form_submit_button("Update Entry")
                if submitted:
                    try:
                        start_time_val = _parse_time_text(start_time_raw)
                        end_time_val = _parse_time_text(end_time_raw) if not running else None
                    except ValueError:
                        st.error("Time must be in HH:MM format.")
                        st.stop()
                    start_iso = _combine_date_time(entry_date, start_time_val)
                    end_iso = None if running else _combine_date_time(entry_date, end_time_val)
                    db.update_project_entry(
                        entry_id=row["id"],
                        project_name=project_name,
                        category=category,
                        start_time=start_iso,
                        end_time=end_iso,
                    )
                    st.toast("Entry updated")
                    st.rerun()
            if st.button("Delete Entry", key=f"delete_entry_{row['id']}"):
                db.delete_project_entry(row["id"])
                st.toast("Entry deleted")
                st.rerun()
    else:
        st.info("No project entries recorded yet.")

    st.subheader("Add Manual Entry")
    sessions_for_manual = db.sessions_as_dicts(db.list_all_sessions())
    if not sessions_for_manual:
        st.info("Create a session before adding manual entries.")
        return
    session_map = {
        f"#{row['id']} - {row['session_date']}": row for row in sessions_for_manual
    }
    selected_session_label = st.selectbox(
        "Session", list(session_map.keys()), key="manual_session_select"
    )
    with st.form("manual_entry_form"):
        project_name = st.text_input("Project name", key="manual_project")
        categories_for_manual = db.get_categories(include_inactive=True)
        category = st.selectbox(
            "Category", categories_for_manual, key="manual_category"
        )
        entry_date = st.date_input("Entry date", value=_now().date())
        start_time_raw = _time_text_input(
            "Start", default=time(hour=9, minute=0), key="manual_start_time"
        )
        ended = st.checkbox("Set end time", value=True, key="manual_end_checkbox")
        end_time_raw: Optional[str] = None
        if ended:
            end_time_raw = _time_text_input(
                "End", default=time(hour=17, minute=0), key="manual_end_time"
            )
        submitted = st.form_submit_button("Add Entry")
        if submitted:
            if not project_name.strip():
                st.warning("Project name is required")
            else:
                try:
                    start_time_val = _parse_time_text(start_time_raw)
                    end_time_val = _parse_time_text(end_time_raw) if ended else None
                except ValueError:
                    st.error("Time must be in HH:MM format.")
                    st.stop()
                session_id = session_map[selected_session_label]["id"]
                start_iso = _combine_date_time(entry_date, start_time_val)
                end_iso = None
                if ended:
                    end_iso = _combine_date_time(entry_date, end_time_val)
                db.add_manual_project_entry(
                    session_id=session_id,
                    project_name=project_name.strip(),
                    category=category,
                    start_time=start_iso,
                    end_time=end_iso,
                )
                st.toast("Manual entry added")
                st.rerun()


def main() -> None:
    st.title("Time Tracker")
    page = st.sidebar.radio("Navigate", ("Tracker", "Reports", "Admin"))

    if page == "Tracker":
        render_tracker()
    elif page == "Reports":
        render_reports()
    else:
        render_admin()


if __name__ == "__main__":
    main()
