from __future__ import annotations

import os
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DEFAULT_TIMEZONE = "America/Chicago"
DEFAULT_DB_FILENAME = "time_tracker.db"


def get_db_path() -> Path:
    raw = os.getenv("TIME_TRACKER_DB_PATH", "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return Path(__file__).resolve().parent / DEFAULT_DB_FILENAME


def get_app_timezone() -> ZoneInfo:
    tz_name = os.getenv("TIME_TRACKER_TZ", DEFAULT_TIMEZONE).strip() or DEFAULT_TIMEZONE
    try:
        return ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        return ZoneInfo(DEFAULT_TIMEZONE)
