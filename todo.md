# Docker-Ready Refactor TODO

## Assessment (current state)
- App is a single-process Streamlit UI (`app.py`) with a local SQLite DB (`db.py`) stored at a fixed path next to the code (`time_tracker.db`).
- No container artifacts exist (no `Dockerfile`, `.dockerignore`, or `docker-compose.yml`).
- Timezone uses `ZoneInfo("America/Chicago")`, which requires system tzdata in slim images.
- Streamlit defaults will bind to localhost, so container needs explicit server config or CLI flags.

## Refactor plan (code changes)
- [x] Make the database path configurable via env var (`TIME_TRACKER_DB_PATH`) with a local default and container override.
- [x] Ensure the DB parent directory exists at startup (create if missing) using the configured path.
- [x] Add a small config module to centralize env parsing and defaults (DB path, timezone).
- [x] Remove the `importlib` fallback loader in `app.py` and use normal imports.

## Containerization artifacts
- [x] Add `Dockerfile` (python 3.11-slim) that installs `tzdata`, copies app code, installs `requirements.txt`, sets a non-root user, and exposes port `8501`.
- [x] Add `.dockerignore` (exclude `.venv`, `__pycache__`, `time_tracker.db`, `*.pyc`, local assets not required, etc.).
- [x] Add `.streamlit/config.toml` to bind `server.address = "0.0.0.0"` and `server.port = 8501`.
- [x] Add `docker-compose.yml` for local runs with a named volume mounted to `/data` and environment variables for DB path and timezone.

## Docs & usability
- [x] Update `README.md` with Docker build/run commands and volume mount instructions.
- [x] Document how to migrate an existing local `time_tracker.db` into the container volume.
- [x] Add a short troubleshooting note about timezones and permissions for `/data`.

## Validation checklist
- [ ] Build the image locally and run the container with a mounted volume.
- [ ] Verify Streamlit loads at `http://localhost:8501` and can create/write `time_tracker.db` in the volume.
- [ ] Start/stop a work session; confirm data persists after container restart.
