# Marina's Wisdom — Application Analysis

## Overview

Marina's Wisdom is a multimedia OSINT (Open Source Intelligence) analysis web application. It allows a user to submit content from four sources — YouTube videos, Rumble videos, uploaded audio/video files, and web page URLs — and run AI-powered analysis patterns against the extracted text content. The analysis is performed by the [Fabric](https://github.com/danielmiessler/fabric) CLI, which routes prompts to LLMs via OpenRouter.

---

## Architecture

```
Browser (React + Vite)
      ↕  HTTP (fetch)
FastAPI (Python)
      ↕  subprocess
 Fabric CLI ──→ OpenRouter API
      ↕
 SQLite (aiosqlite)
```

The frontend and backend are separate processes communicating over HTTP.

---

## Tech Stack

### Frontend
| Technology | Purpose |
|---|---|
| **React 19** | UI framework |
| **Vite 8** | Build tool / dev server |
| **React Router DOM 7** | Client-side routing |
| **Tailwind CSS 4** | Utility-first CSS |
| **Lucide React** | SVG icon library |
| **jsPDF** | Client-side PDF export of results |
| **Oxlint** | Linter |

### Backend
| Technology | Purpose |
|---|---|
| **Python 3.12+** | Runtime |
| **FastAPI** | Web framework |
| **SQLAlchemy (async)** | ORM |
| **aiosqlite** | Async SQLite driver |
| **Pydantic** | Request/response validation |
| **httpx** | Async HTTP client |
| **tiktoken** | LLM token counting |
| **youtube-transcript-api** | YouTube subtitle fetching |
| **python-multipart** | File upload parsing |

### External Dependencies (CLI tools)
| Tool | Purpose |
|---|---|
| **fabric** | AI pattern analysis CLI (calls OpenRouter) |
| **yt-dlp** | Downloads video metadata and audio |
| **ffmpeg / ffprobe** | Audio compression and duration detection |

### External Services
| Service | Purpose |
|---|---|
| **OpenRouter API** | LLM inference (analysis + audio transcription) |
| **Jina Reader API** | Web page text extraction (`r.jina.ai/{url}`) |

---

## Backend Structure

```
backend/
├── main.py                  # FastAPI app entry, CORS, lifespan
├── routers.py               # All API route definitions
├── models.py                # SQLAlchemy ORM model
├── schemas.py               # Pydantic schemas
├── database.py              # Async SQLite engine & session
├── requirements.txt         # Python dependencies
├── run.sh                   # Backend launch script
└── services/
    ├── job_manager.py           # Analysis orchestration, CRUD, dedup
    ├── fabric_service.py        # Fabric CLI subprocess calls
    ├── youtube_service.py       # YouTube transcript fetching
    ├── rumble_service.py        # Rumble audio download + transcription
    ├── file_service.py          # Local file audio transcription
    ├── web_scraper.py           # Web page text scraping (Jina)
    ├── metadata_service.py      # Video metadata extraction (yt-dlp)
    ├── cost_service.py          # Token counting + OpenRouter pricing
    └── openrouter_service.py    # Audio transcription via OpenRouter
```

---

## API Endpoints

| Method | Path | Parameters | Description |
|---|---|---|---|
| `GET` | `/api/health` | — | Health check |
| `POST` | `/api/analyze` | `source`, `url`, `pattern`, `model?` | Start analysis (YouTube/Rumble/Web) |
| `POST` | `/api/analyze/file` | `file` (multipart), `pattern`, `model?` | Upload file for analysis |
| `GET` | `/api/jobs/{job_id}` | — | Poll job status & result |
| `GET` | `/api/history` | `source?`, `pattern?`, `limit=50`, `offset=0` | List past analysis jobs |
| `GET` | `/api/check-result` | `source`, `url`, `pattern`, `model?` | Check for existing completed result |
| `GET` | `/api/patterns` | — | List available Fabric patterns |
| `GET` | `/api/models` | — | List available LLM models |

---

## Database Schema

**Table: `analysis_jobs`**

| Column | Type | Notes |
|---|---|---|
| `id` | `TEXT` (UUID PK) | Auto-generated |
| `source` | `TEXT` NOT NULL | `youtube`, `rumble`, `file`, `web` |
| `url` | `TEXT` nullable | Source URL |
| `file_path` | `TEXT` nullable | Path to uploaded file |
| `pattern` | `TEXT` NOT NULL | Fabric pattern name |
| `status` | `TEXT` | `pending` → `running` → `completed` / `failed` |
| `transcript` | `TEXT` nullable | Extracted transcript/scraped text |
| `result` | `TEXT` nullable | LLM analysis output |
| `error` | `TEXT` nullable | Error message |
| `metadata_json` | `JSON` nullable | Model name, cost, duration, video metadata |
| `created_at` | `DATETIME` | UTC |
| `updated_at` | `DATETIME` | UTC |

---

## Frontend Structure

```
frontend/
├── index.html
├── package.json
├── vite.config.js
└── src/
    ├── main.jsx                   # App entry (BrowserRouter)
    ├── App.jsx                    # Route definitions
    ├── index.css                  # Global styles (Tailwind)
    ├── App.css
    ├── api/
    │   └── client.js              # HTTP client for all API calls
    ├── hooks/
    │   └── usePersistedState.js   # sessionStorage-backed useState
    ├── pages/
    │   ├── AnalysisPage.jsx       # Main analysis view
    │   └── HistoryPage.jsx        # Past results browser
    ├── components/
    │   ├── Layout.jsx             # Nav bar + page wrapper
    │   ├── PatternSelector.jsx    # Pattern search/confirm dropdown
    │   ├── AnalysisRunner.jsx     # Polls & displays analysis results
    │   ├── MetadataDisplay.jsx    # Video metadata table (modal)
    │   ├── YouTubeTab.jsx         # YouTube URL input + analyze
    │   ├── RumbleTab.jsx          # Rumble URL input + analyze
    │   ├── FileUploadTab.jsx      # File picker + analyze
    │   └── WebScrapeTab.jsx       # Web URL input + analyze
    └── assets/
        ├── hero.png
        ├── react.svg
        └── vite.svg
```

---

## Routing

| Path | Component | Description |
|---|---|---|
| `/` | Redirect → `/analysis` | Root redirect |
| `/analysis` | `<Layout>` + `<AnalysisPage>` | Main analysis UI |
| `/history` | `<Layout>` + `<HistoryPage>` | Browse past results |

---

## Feature Tabs (AnalysisPage)

All four tabs share a **PatternSelector** component and a **Model** dropdown at the page level. The selected model applies to all tabs.

### YouTube Tab
- **Input**: YouTube URL
- **Default pattern**: `create_micro_summary`
- **Flow**: URL → extract video ID → fetch transcript via `youtube-transcript-api` → run Fabric pattern
- **Button**: "Analyze YouTube Video"

### Rumble Tab
- **Input**: Rumble URL
- **Default pattern**: `create_micro_summary`
- **Flow**: URL → download audio via `yt-dlp` → compress with ffmpeg → transcribe via OpenRouter (gpt-audio-mini, chunked at 10 min) → run Fabric pattern
- **Button**: "Analyze Rumble Video"

### File Upload Tab
- **Input**: Audio/video file picker (accepts `audio/*,video/*`)
- **Default pattern**: `create_micro_summary`
- **Flow**: File → transcribe via OpenRouter (gpt-audio-mini, chunked) → run Fabric pattern
- **Button**: "Upload & Analyze"

### Web Scraping Tab
- **Input**: Web URL
- **Default pattern**: `analyze_claims`
- **Flow**: URL → scrape text via `r.jina.ai/{url}` → run Fabric pattern
- **Button**: "Scrape & Analyze"

---

## Key User Flows

### New Analysis
1. User selects a tab (YouTube / Rumble / File / Web)
2. Enters URL (or picks file)
3. Searches and confirms a Fabric pattern (double-click or Enter in dropdown)
4. On pattern confirmation, an **auto-check** fires: hits `GET /api/check-result` with `source` + `url` + `pattern` + `model`
   - If a completed result exists with all three matching → displays it immediately (no analysis)
   - If not → shows a red "Analysis has not been done before." message
5. User presses Enter (or clicks the button) → analysis begins:
   - Frontend calls `POST /api/analyze` (or `/api/analyze/file`)
   - Returns a `job_id` immediately
   - `AnalysisRunner` polls `GET /api/jobs/{job_id}` every 2 seconds
   - When complete, displays result, transcript (togglable), copy button, PDF export

### History Browsing
1. User navigates to `/history`
2. Can filter by source (All / YouTube / Rumble / File / Web)
3. Can search by URL, title, channel, pattern, result text
4. Each job is collapsible — expand to see result + transcript
5. Actions: Copy Result, Copy Transcript, Open Original URL, Show Meta (modal)

---

## State Management

- **No global state library** — all state local to components
- **`usePersistedState`** — custom hook that mirrors state to `sessionStorage`:
  - Active tab, model selection, URL inputs per tab, pattern per tab, confirmed pattern name
  - Survives page refreshes but not cross-tab — `sessionStorage` is per-tab

---

## External Configuration

- **OpenRouter API key**: read from `~/.config/fabric/.env` (shared with Fabric CLI)
- **Fabric model**: env var `FABRIC_MODEL` (default: `deepseek/deepseek-v4-flash`)
- **Fabric vendor**: env var `FABRIC_VENDOR` (default: `OpenRouter`)
- **Transcription model**: env var `TRANSCRIPTION_MODEL` (default: `openai/gpt-audio-mini`)
- **Audio chunk duration**: env var `TRANSCRIPTION_CHUNK_SECONDS` (default: 600)
- **API base URL**: frontend env var `VITE_API_BASE` (default: `http://localhost:8000/api`)

---

## Authentication

None. The app is designed for local/self-hosted use. The OpenRouter API key is read from the local filesystem.

---

## Key UI Interactions

### Pattern Selection
- **Search**: typing filters the dropdown in real-time
- **Single click**: highlights a pattern (violet background), does **not** confirm — dropdown stays open
- **Double-click** (within 400ms): confirms the pattern — input text turns green, dropdown closes, `onConfirm` fires (triggers auto-check)
- **Enter** (dropdown visible): selects highlighted pattern (or first match), confirms it, fires `onConfirm`, closes dropdown
- **Enter** (pattern already green): runs analysis immediately via `onEnter`
- **Arrow keys**: navigate dropdown with scroll-into-view

### Auto-Check Flow
When a pattern is confirmed (green), the frontend calls `GET /api/check-result` with `source`, `url`, `pattern`, and `model`:
- **Result found** → `AnalysisRunner` displays the existing job
- **Not found** → small red inline box: "Analysis has not been done before."
- **Enter or button click** → clears the red box, starts a new analysis

### Analysis Runner
- Polls `GET /api/jobs/{id}` every 2 seconds
- Spins loader while `pending` / `running`
- **Completed**: metadata header + result body, Copy Result, Export PDF, Show Transcript buttons
- **Failed**: red error message
- Metadata includes: title, URL, channel, views, duration, publish date, pattern, model, processing time, tokens, cost

### History Page
- Filter by source: All / YouTube / Rumble / File / Web
- Free-text search across URL, file path, pattern, source, status, error, result, transcript, title, channel
- Expandable rows with Copy Result, Copy Transcript, Open Original, Show Meta (modal)
- Meta modal shows full metadata table

---

## Duplicate Detection

Two layers:

1. **On analysis submission** (`start_analysis` in `job_manager.py`): checks for an existing completed job matching `source` + `url` + `pattern` + `model`. If found, returns the existing `job_id` instead of creating a new job.

2. **On pattern confirm** (frontend auto-check): `GET /api/check-result` uses the same logic to proactively display existing results before the user even clicks analyze.

3. **Transcript caching** (`_find_existing_transcript`): reuses previously fetched transcripts for the same source + URL to avoid re-downloading.

---

## Cost Estimation

After each completed analysis, the backend estimates:
- Input/output token counts via `tiktoken`
- Live pricing from OpenRouter API (cached for 5 minutes)
- Estimated cost in USD stored in `metadata_json.estimated_cost`