# Time Tracker

A local Streamlit application for tracking work time and categorizing project work using a SQLite database. The app is designed for Central Time (America/Chicago).

## Features
- Start/stop a workday with automatic CST timestamps and daily overview
- Track detailed project entries with category selection while a day is running
- Adjustable category list with defaults: Programming, Meetings, Marketing
- Reporting tab with daily hours bar chart and average category pie chart across any date range
- Admin dashboard for editing or deleting sessions/entries and adding manual records

## Getting Started
1. Create a virtual environment (optional but recommended).
    ```powershell
    python -m venv .venv
    source .venv/bin/activate  (On Windows: .venv\Scripts\activate)
    ```

2. Install dependencies.
    ```powershell
    pip install -r requirements.txt
    ```

3. Launch the app.
    ```powershell
    streamlit run app.py
    ```
    
The SQLite database file (time_tracker.db) is created alongside the app on first run.

## Usage Notes
- The tracker tab automatically shows today's date in CST. Start the day before logging project entries.
- Only one active work session and one active project entry can exist at a time. Stop an active item before starting another.
- Use the Reports tab to select any date range and view daily totals plus the average hours spent per category within that range.
- The Admin dashboard lets you adjust historical data, manage categories, and add manual project entries when needed.
