from __future__ import annotations

from datetime import date, time, timedelta
from typing import Optional

import pandas as pd
import streamlit as st

import importlib.util
import sys
from pathlib import Path


CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))


def _load_module(name: str, filename: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, CURRENT_DIR / filename)
    if not spec or not spec.loader:
        raise ModuleNotFoundError(f"Cannot load module '{name}'")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


try:
    import constants  # type: ignore
except ModuleNotFoundError:
    constants = _load_module("constants", "constants.py")

try:
    import services  # type: ignore
except ModuleNotFoundError:
    services = _load_module("services", "services.py")

try:
    import style  # type: ignore
except ModuleNotFoundError:
    style = _load_module("style", "style.py")

style.apply_theme()
services.init_db()


def _time_text_input(
    label: str, default: Optional[time] = None, *, key: Optional[str] = None
) -> str:
    return st.text_input(label, value=services.format_time_value(default), key=key)


def _get_date_range() -> tuple[date, date]:
    end_date = services.current_time().date()
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


def render_tracker() -> None:
    st.header("Daily Tracker")
    today = services.current_time().date()
    st.subheader(f"Today: {today.isoformat()}")

    active_session = services.get_active_session()

    col1, col2 = st.columns(2)

    with col1:
        if active_session:
            if st.button("Stop Day", type="primary"):
                services.end_session(active_session.id)
                st.toast("Day stopped")
                st.rerun()
        else:
            if st.button("Start Day", type="primary"):
                services.start_session()
                st.toast("New workday started")
                st.rerun()

    with col2:
        if active_session:
            start_dt = services.parse_iso(active_session.start_time)
            st.metric(
                "Day Started",
                f"{start_dt.strftime('%I:%M %p')} CST" if start_dt else "",
            )
        else:
            st.info("No active workday. Start the day to begin tracking time.")

    st.divider()
    if active_session:
        st.subheader("Project Time Tracking")
        active_entry = services.get_active_project_entry(active_session.id)

        if active_entry:
            entry_duration = services.format_duration_hours(
                active_entry.start_time, active_entry.end_time
            )
            st.success(
                f"Tracking '{active_entry.project_name}' in {active_entry.category}"
            )
            started_at = services.parse_iso(active_entry.start_time)
            if started_at:
                st.write(
                    f"Started at: {started_at.strftime('%I:%M %p')} CST"
                )
            st.write(f"Elapsed hours: {entry_duration}")
            if st.button("Stop Project Entry"):
                services.end_project_entry(active_entry.id)
                st.toast("Project entry stopped")
                st.rerun()
        else:
            with st.form("project_entry"):
                project_name = st.text_input("Project name")
                categories = services.get_categories()
                if categories:
                    default_index = (
                        categories.index("Programming")
                        if "Programming" in categories
                        else 0
                    )
                    category = st.selectbox(
                        "Category", categories, index=default_index
                    )
                else:
                    category = st.selectbox("Category", categories)
                submitted = st.form_submit_button("Start Project Entry")

                if submitted:
                    if not project_name.strip():
                        st.warning("Project name is required")
                    else:
                        services.start_project_entry(
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
    today_entries = services.get_today_entries_display(today)
    if today_entries is not None:
        st.dataframe(today_entries, use_container_width=True)
    else:
        st.write("No project entries logged yet today.")


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

    chart_data, total_hours = services.fetch_daily_hours_summary(start_date, end_date)

    if not chart_data.empty:
        st.subheader("Daily Hours Worked")
        st.write(f"Total Hours: {total_hours:.2f}")
        if show_raw:
            st.caption("Raw database view")
            display_df = chart_data[["session_label", "hour_total"]].rename(
                columns={"session_label": "Date", "hour_total": "Hours"}
            )
            st.dataframe(display_df, use_container_width=True)
        else:
            fig = services.build_daily_hours_chart(chart_data)
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No work sessions in the selected range.")

    st.divider()

    per_category = services.fetch_category_breakdown(start_date, end_date)
    st.subheader("Work Categories")
    if per_category is not None and not per_category.empty:
        if show_raw:
            st.caption("Raw database view")
            display_categories = per_category[["category", "hours"]].rename(
                columns={"category": "Category", "hours": "Hours"}
            )
            display_categories.loc[:, "Hours"] = display_categories["Hours"].round(2)
            st.dataframe(display_categories, use_container_width=True)
        else:
            fig = services.build_category_pie(per_category)
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No project entries in the selected range for category chart.")


def render_admin() -> None:
    st.header("Admin Dashboard")
    st.write("Make manual adjustments to your data and manage categories.")

    st.subheader("Categories")
    categories_all = services.get_categories(include_inactive=True)
    active_categories = set(services.get_categories(include_inactive=False))

    col1, col2 = st.columns(2)
    with col1:
        new_category = st.text_input("Add new category")
        if st.button("Add Category"):
            if not new_category.strip():
                st.warning("Category name cannot be empty")
            else:
                services.add_category(new_category.strip())
                st.toast("Category added")
                st.rerun()

    with col2:
        if categories_all:
            selected_category = st.selectbox("Select category", categories_all)
            is_active = selected_category in active_categories
            st.write(f"Status: {'Active' if is_active else 'Inactive'}")
            if is_active:
                if st.button("Deactivate", key="deactivate_category"):
                    services.set_category_active(selected_category, False)
                    st.toast("Category deactivated")
                    st.rerun()
            else:
                if st.button("Activate", key="activate_category"):
                    services.set_category_active(selected_category, True)
                    st.toast("Category activated")
                    st.rerun()
            new_name = st.text_input("Rename category", value=selected_category)
            if st.button("Rename", key="rename_category_btn"):
                if not new_name.strip():
                    st.warning("New category name cannot be empty")
                elif new_name.strip() != selected_category:
                    services.rename_category(selected_category, new_name.strip())
                    st.toast("Category renamed")
                    st.rerun()
        else:
            st.info("No categories found.")

    st.divider()

    st.subheader("Work Sessions")
    sessions = services.get_all_sessions()
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
            start_dt = services.parse_iso(row["start_time"])
            end_dt = services.parse_iso(row["end_time"])
            with st.form(f"session_edit_{row['id']}"):
                base_date = start_dt.date() if start_dt else services.current_time().date()
                edit_date = st.date_input("Session date", value=base_date)
                start_time_raw = _time_text_input(
                    "Start time",
                    default=services.time_from_datetime(start_dt),
                    key=f"session_start_time_{row['id']}",
                )
                running = end_dt is None
                running = st.checkbox("Session in progress", value=running)
                end_time_raw: Optional[str] = None
                if not running:
                    end_time_raw = _time_text_input(
                        "End time",
                        default=services.time_from_datetime(end_dt)
                        or services.time_from_datetime(start_dt),
                        key=f"session_end_time_{row['id']}",
                    )
                notes_val = st.text_area("Notes", value=row.get("notes") or "")
                submitted = st.form_submit_button("Update Session")
                if submitted:
                    try:
                        start_time_val = services.parse_time_text(start_time_raw)
                        end_time_val = (
                            services.parse_time_text(end_time_raw) if not running else None
                        )
                    except ValueError:
                        st.error("Time must be in HH:MM format.")
                        st.stop()
                    start_iso = services.combine_date_time(edit_date, start_time_val)
                    end_iso = None if running else services.combine_date_time(edit_date, end_time_val)
                    services.update_session(
                        session_id=row["id"],
                        session_date=edit_date.isoformat(),
                        start_time=start_iso,
                        end_time=end_iso,
                        notes=notes_val or None,
                    )
                    st.toast("Session updated")
                    st.rerun()
            if st.button("Delete Session", key=f"delete_session_{row['id']}"):
                services.delete_session(row["id"])
                st.toast("Session deleted")
                st.rerun()
    else:
        st.info("No sessions recorded yet.")

    st.divider()
    st.subheader("Project Entries")
    entries = services.get_all_project_entries()
    if entries:
        df_entries = pd.DataFrame(entries)
        st.dataframe(df_entries, use_container_width=True)
    else:
        st.info("No project entries recorded yet.")

    st.subheader("Add Manual Entry")
    sessions_for_manual = services.get_all_sessions()
    if sessions_for_manual:
        session_map = {
            f"#{row['id']} - {row['session_date']}": row
            for row in sessions_for_manual
        }
        selected_session_label = st.selectbox(
            "Session", list(session_map.keys()), key="manual_session_select"
        )
        with st.form("manual_entry_form"):
            project_name = st.text_input("Project name", key="manual_project")
            categories_for_manual = services.get_categories(include_inactive=True)
            category = st.selectbox(
                "Category", categories_for_manual, key="manual_category"
            )
            entry_date = st.date_input("Entry date", value=services.current_time().date())
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
                        start_time_val = services.parse_time_text(start_time_raw)
                        end_time_val = (
                            services.parse_time_text(end_time_raw) if ended else None
                        )
                    except ValueError:
                        st.error("Time must be in HH:MM format.")
                        st.stop()
                    session_id = session_map[selected_session_label]["id"]
                    start_iso = services.combine_date_time(entry_date, start_time_val)
                    end_iso = None
                    if ended:
                        end_iso = services.combine_date_time(entry_date, end_time_val)
                    services.add_manual_project_entry(
                        session_id=session_id,
                        project_name=project_name.strip(),
                        category=category,
                        start_time=start_iso,
                        end_time=end_iso,
                    )
                    st.toast("Manual entry added")
                    st.rerun()
    else:
        st.warning("Create a work session before adding project entries.")


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
