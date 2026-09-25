# Session Report — September 25, 2026

## App Overview

**Marina's Wisdom** (formerly CVE-OSINT-1, then Marina Jacobi AI Extracts) — a self-hosted OSINT app for analyzing Rumble and YouTube videos using AI (Fabric CLI + OpenRouter).

**Stack:** React 19 (Vite 8) → FastAPI (Python) → Fabric CLI → OpenRouter API
**DB:** SQLite (`marina_jacobi.db`)

---

## Current Status (at session end)

- Backend: **Working** — starts cleanly with `./run.sh`
- Frontend: **Working** — `npm run dev` serves on localhost:5173
- Rumble analysis: **Functional** — channel-restricted to MarinaJacobi, fetches metadata via oEmbed API, downloads audio, transcribes via OpenRouter, runs Fabric pattern analysis
- YouTube analysis: **Functional** — fetches subtitles via youtube-transcript-api, runs Fabric pattern analysis
- **No tests exist** in the entire codebase

---

## Project Structure

```
├── AGENTS.md                      # Repo guidance doc
├── App-Analysis.md                # Detailed architecture doc
├── README.md
├── backend/
│   ├── main.py                    # FastAPI entry, CORS, lifespan, /health, /v1/models stubs
│   ├── database.py                # Async SQLite engine + session
│   ├── models.py                  # SQLAlchemy models: AnalysisJob, CacheEntry
│   ├── schemas.py                 # Pydantic schemas (YouTubeRequest, RumbleRequest, etc.)
│   ├── requirements.txt
│   ├── run.sh                     # uvicorn 0.0.0.0:8000 --reload
│   ├── routers/
│   │   ├── youtube_router.py      # /api/youtube/*
│   │   ├── rumble_router.py       # /api/rumble/*
│   │   ├── channel_router.py      # /api/channel/videos
│   │   └── shared_router.py       # /api/health, /api/jobs, /api/history, /api/patterns
│   └── services/
│       ├── fabric_service.py      # Fabric CLI subprocess calls
│       ├── openrouter_service.py  # OpenRouter audio transcription
│       ├── youtube_service.py     # YouTube subtitle fetching
│       ├── rumble_service.py      # Rumble audio download + cloudscraper scraping
│       ├── rumble_orchestrator.py # Rumble analysis pipeline
│       ├── youtube_orchestrator.py# YouTube analysis pipeline
│       ├── channel_service.py     # Channel video listing (cloudscraper + DB cache)
│       ├── metadata_service.py    # Video metadata (oEmbed + yt-dlp)
│       ├── cost_service.py        # Token counting + OpenRouter pricing
│       └── database_helpers.py    # CRUD helpers, cache read/write
├── frontend/
│   ├── vite.config.js
│   ├── package.json
│   └── src/
│       ├── main.jsx               # React entry
│       ├── App.jsx                # Routes + JobProvider context
│       ├── api/client.js          # All API call functions
│       ├── context/JobContext.jsx  # Job-running state (locks nav while analyzing)
│       ├── pages/
│       │   ├── YouTubeAnalysisPage.jsx  # YouTube tab
│       │   ├── RumbleAnalysisPage.jsx   # Rumble tab ("Freely Analyze")
│       │   └── HistoryPage.jsx          # Past results browser
│       ├── components/
│       │   ├── Layout.jsx              # Nav bar with hamburger menu
│       │   ├── AnalysisRunner.jsx      # Job poller + result display (markdown-aware)
│       │   ├── MarkdownResult.jsx      # Markdown/plain text renderer
│       │   ├── PatternSelector.jsx     # Pattern search/confirm dropdown
│       │   ├── VideoPicker.jsx         # Channel video searchable picker
│       │   └── MetadataDisplay.jsx     # Metadata modal
│       └── utils/markdown.js           # Markdown detection heuristic
```

---

## Key Changes Made This Session

### 1. Channel Video Picker (major feature)
- `GET /api/channel/videos?limit=500` endpoint — uses cloudscraper to scrape MarinaJacobi's Rumble channel page(s)
- Parses `<rum-videos-grid><script type="application/json">` blocks for video metadata (title, url, duration, view_count)
- Follows `rel=next` pagination links across all 17 pages (~403-450 videos)
- **DB-persisted cache** — stored in `cache_store` table in SQLite, survives restarts. Refreshes hourly in background.
- Videos sorted by season then episode (S1 E1 → S1 E20 → S2 E1 → ...), unknowns at end
- Frontend `VideoPicker` component — searchable dropdown with arrow key navigation, Enter to select
- Season/episode parsed from title with flexible regex: handles "S5 E3", "S5E3", "Season 5 Episode 3", "S 5  E 3"
- Search normalizes spaces in S/E patterns so "S8 E11" matches "S8E11"
- Double-click search input or URL input to clear selection

### 2. Model hard-wired
- Model selector removed from UI. Only `deepseek/deepseek-v4-flash` (or `FABRIC_MODEL` env var) is used.
- Removed: model dropdown from Rumble/YouTube pages, `/api/models` endpoint, `list_models()` function, `model` field from request schemas

### 3. Web/File features removed
- All Web scraping and File upload code deleted (routers, services, pages, API functions)
- Only YouTube and Rumble remain

### 4. Rebranding
- App renamed from "CVE-OSINT-1" → "Marina Jacobi AI Extracts" → "Marina's Wisdom"
- DB renamed from `cve_osint.db` → `marina_jacobi.db`
- User-Agent updated accordingly

### 5. Rumble channel restriction
- Only videos from `MarinaJacobi` channel accepted (configurable via `RUMBLE_CHANNEL` env var)
- Metadata fetched via oEmbed API (`rumble.com/api/Media/oembed.json`) — bypasses Cloudflare issues
- Channel handle extracted from `author_url` (`/c/MarinaJacobi`)

### 6. Bug fixes
- **Stuck-job bug:** `update_job_status("running")` moved inside try block in all 4 orchestrators — prevents silent death leaving status at "pending"
- **UTC time bug:** Pydantic field_serializer appends `+00:00` to naive datetimes from SQLite; frontend defensively appends `Z`
- **Zero videos on reload:** Naive vs aware datetime comparison crash (Python 3.12+) in channel cache age check
- **Double-click not clearing:** `onDoubleClick` doesn't fire in Chrome DevTools responsive/touch mode. Replaced with click-timing detector
- **Dropdown overlay intercepting clicks:** Replaced `fixed inset-0` overlay with `onBlur` on input

### 7. UI enhancements
- Responsive hamburger menu on nav bar
- Navigation locked while job is running (JobContext)
- Markdown rendering for analysis results (react-markdown)
- History item labels: "Marina Jacobi's Rumble Channel", "Pattern used was:", UTC times
- Full video titles in picker (no truncation)
- Season/episode sorting in picker

---

## Important Implementation Details

### run.sh quirk
The script CDs into `backend/` then `cd ..` before running uvicorn so `backend.main` resolves as a package. `.venv` is expected inside `backend/`.

### sys.path hack
`main.py` does `sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))` — needed for `from backend...` imports when run as `uvicorn backend.main:app`.

### .venv location
Currently at repo root (`/home/cowboy/000/cve-marina-1/.venv/`), not inside `backend/`. This may need to be symlinked or recreated if `run.sh` has issues.

### OpenRouter key
Read from `~/.config/fabric/.env` at runtime (not from environment variables). App reads `OPENROUTER_API_KEY=` from that file.

### Rumble gotchas
- Uses `cloudscraper` to bypass Cloudflare
- Video page scraped then embedded JSON parsed for audio stream URLs
- Audio downloaded, compressed with ffmpeg (32k mono), then transcribed via OpenRouter's `gpt-audio-mini`
- Transcription chunked at 10 minutes

### Channel video cache
- Stored in `cache_store` table with key `channel_videos`
- Cache refreshed hourly in background task
- First-ever fetch: synchronous (~20s). Subsequent: instant from DB.

### History source filter
Filter buttons show: All, Youtube, Rumble. Web and File removed.

---

## Open Questions / Potential Next Steps

1. **YouTube channel videos** — No equivalent video picker for YouTube. User currently pastes YouTube URLs manually.
2. **Delete old DB data** — The old `cve_osint.db` data does not auto-migrate to `marina_jacobi.db`
3. **Multiple channels** — Currently hard-wired to MarinaJacobi. Could support multiple channels with a selector.
4. **Production deployment** — App has no auth layer, meant for self-hosted use only
5. **Error handling** — Some background tasks silently swallow exceptions

---

## Commits (30 most recent)

```
d941b17 Change title from 'Rumble Analysis' to 'Freely Analyze'
06f9491 Fix 500 error: removed model param from router calls
59144c2 Hard-wire deepseek/deepseek-v4-flash as the only model
4080854 Add arrow key navigation to video picker dropdown
208a338 Fix double-click not clearing in responsive/touch mode
b130536 Fix double-click not clearing picker — remove overlay that intercepts clicks
72fafcb Double-click video picker search input to clear selection
06bff8c Normalize season/episode spacing in video search
809f2db Fix season/episode parsing: prefer full S+E match
a41c228 Double-click URL input to clear selection
3b1c0cf Double-tap video picker input to clear selection
07f2ea8 Show full video titles in picker (no truncation)
0942046 Sort by season + episode for precise ordering
1dacac3 Sort channel videos by season number asc
f86cdf7 Fix: zero videos on reload — naive vs aware datetime bug
5f9af1b Persist channel video list in SQLite with background refresh
fe2bb40 Scale channel video listing to ~450 videos with caching
7e4f0aa Fix channel video listing: use cloudscraper instead of yt-dlp
76e62ca Add searchable channel video picker for Rumble tab
c9134dd Add responsive hamburger menu to nav bar
253b6f9 Remove Web and File features
09abc22 Rebrand to Marina's Wisdom
e4d9d02 Fix UTC datetime serialization: add tzinfo to Pydantic output
797b36d Add markdown rendering for analysis results
9745de4 Tweak history item labels: rumble source label, pattern label, UTC time
c2c6431 Lock navigation while job is running
23fefe2 Fix Rumble channel validation: skip yt-dlp for Rumble URLs
e10c19a Rebrand to Marina Jacobi AI Extracts + fix Rumble metadata + channel restriction
```