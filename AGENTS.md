# AGENTS.md — Marina's Wisdom

OSINT multimedia analysis app: React (Vite) → FastAPI (Python) → Fabric CLI → OpenRouter API.

## Architecture

```
React (Vite, port 5173)   ←→   FastAPI (port 8000)   ←→   fabric CLI   ←→   OpenRouter API
                                       ↕
                                  SQLite (marina_jacobi.db)
```

Two separate dev servers; frontend proxies to backend via `VITE_API_BASE` (default `http://localhost:8000/api`). No authentication — designed for local/self-hosted use.

## Quick Start

**Prerequisites** (outside repo): Python 3.12+, Node.js 20+, Fabric CLI, OpenRouter API key in `~/.config/fabric/.env`.

```bash
# Backend
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
./run.sh                              # uvicorn on 0.0.0.0:8000 --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev                           # Vite on localhost:5173
```

**Note:** `run.sh` activates `.venv` from the `backend/` directory. If .venv exists at the repo root instead, adjust the path or recreate it inside `backend/`.

## Project Structure

- `backend/main.py` — FastAPI entry point, CORS, lifespan (calls `init_db`)
- `backend/routers/*.py` — One router per source (`youtube`, `rumble`) + `shared_router` for health/history/patterns/models/jobs
- `backend/services/*.py` — Orchestrators (`*_orchestrator.py`) and leaf services (`fabric_service.py`, `openrouter_service.py`, etc.)
- `frontend/src/App.jsx` — Route definitions (`/analysis/youtube`, `/analysis/rumble`, `/history`)
- `fabric_service.py` — Shells out to `fabric` CLI via `asyncio.create_subprocess_exec`

## API Endpoints

| Method | Path | Notes |
|--------|------|-------|
| POST | `/api/{source}/analyze` | YouTube/Rumble — returns `{job_id, status}` |
| GET | `/api/jobs/{id}` | Poll job status (shared router) |
| GET | `/api/{source}/check-result` | Duplicate detection by `source+url+pattern+model` |
| GET | `/api/history` | `?source=&pattern=&limit=50&offset=0` |
| GET | `/api/patterns` | `fabric --listpatterns` |
| GET | `/api/models` | `fabric --listmodels` + default |

## Key Environment Variables

| Variable | Default | Used In |
|---|---|---|
| `FABRIC_MODEL` | `deepseek/deepseek-v4-flash` | Fabric analysis |
| `FABRIC_VENDOR` | `OpenRouter` | Fabric —V flag |
| `TRANSCRIPTION_MODEL` | `openai/gpt-audio-mini` | OpenRouter audio transcription |
| `TRANSCRIPTION_CHUNK_SECONDS` | `600` | Audio chunk duration |
| `FABRIC_TIMEOUT` | `600` | Per-attempt timeout |
| `VITE_API_BASE` | `http://localhost:8000/api` | Frontend API base |
| `RUMBLE_CHANNEL` | `MarinaJacobi` | Only allow Rumble videos from this channel |

## Developer Commands

```bash
# Frontend
cd frontend && npm run dev            # Dev server with HMR
cd frontend && npm run build           # Production build
cd frontend && npm run lint            # oxlint
cd frontend && npm run preview         # Preview production build

# Backend (from backend/ dir with .venv active)
./run.sh                               # uvicorn with --reload
```

No test framework is set up for either backend or frontend.

## Execution Model (Important)

**Analysis is async:** Each source endpoint creates a DB job row (`pending`), spawns an `asyncio.Task` for the pipeline, and returns immediately with a `job_id`. The frontend polls `GET /api/jobs/{id}` every 2 seconds.

Orchestrators (`*_orchestrator.py`) follow this pattern:
1. Check for existing completed job (duplicate detection by `source+url+pattern+model`)
2. Create new job, launch pipeline as background task
3. Pipeline: update status to `running` → fetch transcript (cached per source+url) → run Fabric → estimate cost → save result

**In-memory task tracking:** Each orchestrator holds a `_jobs: dict[str, asyncio.Task]`. Tasks are cleaned up in `finally` blocks. This means completed/failed analysis state lives only in SQLite; the in-memory dict is just for task lifecycle (e.g., to avoid orphaned tasks, but there is no cancellation mechanism).

## Source-Specific Flows

| Source | Transcript Method | Default Pattern |
|---|---|---|
| **YouTube** | `youtube-transcript-api` (subtitles, no audio) | `create_micro_summary` |
| **Rumble** | `cloudscraper` → parse embed → pick best audio URL → download → ffmpeg compress → OpenRouter transcription (chunked) | `create_micro_summary` |

**Rumble channel restriction:** Only videos from the configured channel (default: `MarinaJacobi`, overridable via `RUMBLE_CHANNEL` env var) are accepted. Videos from other channels are rejected with a clear error.

**Rumble gotcha:** Uses `cloudscraper` to bypass Cloudflare. Parses embedded JSON (`"ua"` / `"u"` blocks) for audio URLs. Falls back to ffmpeg for HLS streams.

**Transcription:** Rumble and File sources chunk audio via ffmpeg (default 10 min chunks, mono, 32k bitrate) and transcribe each chunk via `openai/gpt-audio-mini` over OpenRouter. YouTube bypasses this entirely (uses API transcripts).

## Duplicate Detection (Two Layers)

1. **Backend on submission** (`run_*_analysis`): checks `source + url + pattern + model` match on existing completed job → returns existing `job_id` instead of creating new
2. **Frontend on pattern confirm** (`GET /api/{source}/check-result`): proactive auto-check before user clicks analyze
3. **Transcript caching** (`find_existing_transcript`): reuses previously-fetched transcript for same `source+url`

## Frontend Quirks

- **Pattern selection:** Single click highlights, double-click (or Enter) confirms and triggers auto-check. Confirmed pattern turns green. Enter on a green pattern starts analysis immediately.
- **State persistence:** `usePersistedState` stores tab, URL inputs, pattern, model in `sessionStorage` (per-tab, survives page refresh).
- **Frontend routes:** Each source type has its own route (`/analysis/youtube`, `/analysis/rumble`)

## External Dependencies (CLI Tools)

- **fabric** — AI pattern analysis (`fabric -p <pattern> -m <model>`) — must be on PATH
- **yt-dlp** — Video metadata (`--impersonate Chrome-133`) — for YouTube and Rumble metadata
- **ffmpeg / ffprobe** — Audio compression and duration detection — required for Rumble & File transcription
- **cloudscraper** (Python) — Bypasses Cloudflare for Rumble pages — installed via pip

## Database

- File: `marina_jacobi.db` (ignored by git, SQLite via aiosqlite)
- Single table `analysis_jobs` with columns: id, source, url, pattern, status, transcript, result, error, metadata_json (JSON), created_at, updated_at
- Auto-created on first run (`init_db` in `main.py` lifespan)

## Notes & Gotchas

- DB is in `.gitignore` — always present locally after first run
- Backend uses absolute imports from `backend.services.*`
- `sys.path.insert(0, ...)` in `main.py` is a hack to make `from backend...` imports work when run as `uvicorn backend.main:app` — do not remove it
No tests exist anywhere in the repo
- The frontend ships `oxlint` (no ESLint), configured via `.oxlintrc.json`
- `.venv` is currently at repo root (not `backend/.venv` as `run.sh` expects) — may need symlink or recreation