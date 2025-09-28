# Time Tracker

A self-hosted Streamlit application for capturing work sessions, tracking project time, and exploring reports backed by a local SQLite database. The app is tuned for Central Time (America/Chicago) and keeps your data on your machine.

## Demo

![Time Tracker Demo](https://pbrazeale.github.io/images/time_tracker.gif)

## Highlights

- **Workday control** start or stop a session with a single click and the app records CST timestamps plus total hours worked.
- **Project-level tracking** log what you are working on, assign a category, and update entries manually with HH:MM time fields.
- **Live dashboards** review daily hours in an interactive bar chart (or a raw table view) and see average daily hours per category via pie or table breakdowns.
- **Full history editing** use the Admin tab to adjust sessions, edit project entries, add manual records, and manage categories.
- **Local-first storage** all information is stored in `time_tracker.db`; no network connection or external account is required.

## Getting Started

1. (Optional) create and activate a virtual environment.
   ```powershell
   # Create virtual enviroment
   python -m venv .venv
   # Activate virtual enviroment
   # PowerShell
   .venv\Scripts\Activate.ps1
   # bash
   source .venv/bin/activate
   ```
2. Install the dependencies.
   ```powershell
   pip install -r requirements.txt
   ```
3. Launch the Streamlit app.
   ```powershell
   streamlit run app.py
   ```
   The SQLite database file (`time_tracker.db`) is created the first time the app runs.

## Using the App

### Tracker tab

- Shows todays date in CST and indicates whether a workday is in progress.
- Click **Start Day** to begin a session, then log project work as you go. Only one session and one active project entry can be running at a time.
- Use **Project Time Tracking** to enter a project name, pick a category, and the tracker records the elapsed hours until you stop it. Manual time edits accept `HH:MM` (seconds default to `:00`).
- The **Todays Entries** table summarizes the days projects and hours.

### Reports tab

- Choose a date range to analyze. Daily totals can be viewed either as a chart or as the exact data table via the `chart / table` toggle.
- The **Daily Hours Worked** visualization highlights total hours per day, while the **Average Daily Hours by Category** section breaks down the same range by project category.

### Admin tab

- Browse and edit the full session and project history with text fields for time entry (`HH:MM`).
- Add manual entries, update categories, or deactivate/rename categories without leaving the app.
- Edits automatically recalculate stored totals so reports remain accurate.

## Why Self-Host Your Time Tracker?

- **Own your data** everything stays in a local SQLite database that you control.
- **Privacy by default** no cloud service, logins, or third-party processors.
- **Customizable workflow** modify categories, adjust reports, or extend the codebase to match your teams processes.
- **Offline friendly** track hours even without internet access; ideal for secure or air-gapped environments.
- **Cost transparency** avoid per-seat subscription fees and tailor storage/backup strategies to your needs.
- **Rich insights** hours-worked summaries and project/category breakdowns help you understand how time is allocated without exposing sensitive client data elsewhere.

## Additional Notes

- Times are stored and displayed in America/Chicago (CST/CDT). Adjustments may be required if you operate across multiple time zones.
- Back up `time_tracker.db` regularly to preserve your history.

## Contributing (quick + kind)

Want to help? Amazing. Here’s the shortest path to a good PR:

1. **Fork → branch**

   - Fork the repo; create a feature branch:
     ```bash
     git checkout -b feat/your-idea
     ```

2. **Dev setup** (clean room; reproducible)

   - Python 3.11+; fresh venv; install deps:
     ```bash
     python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
     pip install -r requirements.txt
     # if present:
     pip install -r requirements-dev.txt
     ```
   - Run the app locally:
     ```bash
     streamlit run app.py
     ```
   - **Do not** commit your `time_tracker.db`; add to your `.gitignore`.

3. **Style & sanity** (make it easy to review)

   - Keep functions small; single responsibility.
   - Type hints + docstrings (why it exists; what it returns).
   - Name things clearly.

4. **DB changes** (handle with care)

   - Any schema change must be handled in `init_db()` (safe migrations; no data loss).
   - Keep timestamps **timezone-aware** (America/Chicago; ISO strings).
   - Backfill defaults for new columns (don’t break old installs).

5. **UX consistency**

   - Business rules stay in `services.py`; UI remains thin.
   - Reuse existing helpers (`parse_time_text`, `combine_date_time`) instead of re-implementing.

6. **Run checks** (before you push)

   - Start/stop a session, edit in Admin, verify Reports (chart ↔ table show same numbers).

7. **Open the PR**
   - Clear title + 1–2 paragraph summary (what changed; why it matters).
   - Include screenshots/gifs for UI changes; note any migration logic.
