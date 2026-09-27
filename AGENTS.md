# AGENTS.md — Marina's Wisdom

Self-hosted OSINT app for analyzing YouTube and Rumble videos using AI-powered analysis patterns (Fabric CLI → OpenRouter API).

```
React 19 (Vite 8, port 5173) → FastAPI (port 8000) → fabric CLI → OpenRouter API
                                                                ↕
                                                           SQLite (marina_jacobi.db)
```

**Freemium model:** Rumble (Marina Jacobi) analysis is **free** — no signup required. YouTube analysis requires **$7/month subscription** via mock PayPal. No passwords, no emails — just a first name and an auto-assigned user ID number. Shared history visible to all users.

Two separate dev servers; frontend proxies to backend via `VITE_API_BASE` (default `http://localhost:8000/api`). No authentication for Rumble — designed for local/self-hosted use with a lightweight token-based auth for YouTube subscribers.

---

## Quick Start

**Prerequisites** (outside repo): Python 3.12+, Node.js 20+, [Fabric CLI](https://github.com/danielmiessler/fabric) on PATH, OpenRouter API key in `~/.config/fabric/.env`.

```bash
# Backend
cd backend
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
./run.sh                              # uvicorn on 0.0.0.0:8000 --reload

# Frontend (separate terminal)
cd frontend && npm install && npm run dev  # Vite on localhost:5173
```

Open http://localhost:5173 — root redirects to `/analysis/rumble` (free, no signup). Clicking YouTube triggers a subscription modal prompting registration + payment.

---

## Project Structure

```
backend/
├── main.py                    # FastAPI entry, CORS, lifespan (calls init_db), /health, /v1/models
├── database.py                # Async SQLite engine + session + init_db migration (users table + analyst columns)
├── models.py                  # SQLAlchemy models: AnalysisJob, CacheEntry, User (freemium: display_id, first_name, subscription_status)
├── schemas.py                 # Shared Pydantic schemas: JobStatusResponse + Auth schemas (RegisterRequest, LoginRequest, TokenResponse)
├── requirements.txt
├── run.sh                     # cd into dir, source .venv, cd .., uvicorn --reload
├── auth/                      # Authentication package
│   ├── __init__.py
│   ├── router.py              # POST /register (first_name only), POST /login (display_id + first_name), GET /me
│   └── dependencies.py        # get_current_user (optional, returns User|None) + require_subscriber (raises 401/402)
├── payments/                  # Mock PayPal payment
│   ├── __init__.py
│   └── router.py              # POST /mock-subscribe — activates 30-day subscription
├── youtube/                   # YouTube feature package
│   ├── __init__.py
│   ├── router.py              # POST /analyze, GET /jobs/{id}, GET /check-result (all require subscriber)
│   ├── schemas.py             # YouTubeRequest, JobStatusResponse
│   ├── service.py             # youtube-transcript-api subtitle fetching
│   ├── orchestrator.py        # Analysis pipeline (async task) — accepts analyst_name, analyst_display_id
│   └── db_helpers.py          # CRUD, duplicate detection, transcript caching
├── rumble/                    # Rumble feature package
│   ├── __init__.py
│   ├── router.py              # POST /analyze, GET /jobs/{id}, GET /check-result (all PUBLIC — no auth)
│   ├── schemas.py             # RumbleRequest, JobStatusResponse
│   ├── service.py             # cloudscraper → embed parse → audio download → ffmpeg → OpenRouter transcription
│   ├── orchestrator.py        # Analysis pipeline + channel validation — accepts analyst_name, analyst_display_id
│   ├── db_helpers.py          # CRUD, duplicate detection, transcript caching, cache_store
│   ├── channel_router.py      # GET /api/channel/videos (PUBLIC — no auth)
│   └── channel_service.py     # Scrapes Rumble channel page(s), paginates, DB-caches
├── history/                   # History feature package
│   ├── __init__.py
│   ├── router.py              # /api/health, /api/jobs/{id}, /api/history, /api/patterns, /api/models (all PUBLIC)
│   ├── schemas.py             # JobStatusResponse, HistoryFilter
│   └── db_helpers.py          # list_jobs (filtered, paginated, no user isolation), get_job
└── services/                  # Shared infrastructure
    ├── auth_service.py        # JWT (HS256), user CRUD, display_id auto-increment, subscription management
    ├── fabric_service.py      # Fabric CLI subprocess calls (asyncio.create_subprocess_exec) + 71 curated patterns
    ├── openrouter_service.py  # Audio chunking via ffmpeg + OpenRouter transcription via gpt-audio-mini
    ├── cost_service.py        # tiktoken counting + live OpenRouter pricing (5-min cache) → USD estimate
    └── metadata_service.py    # Video metadata: oEmbed API for Rumble, yt-dlp for YouTube

frontend/
├── index.html                 # Title still says "OSINT-1" (not yet rebranded)
├── package.json               # React 19, Vite 8, Tailwind 4, react-router-dom 7
├── vite.config.js             # react() + tailwindcss() plugins
├── src/
│   ├── main.jsx               # React entry with BrowserRouter
│   ├── App.jsx                # Routes: /login, /register, / → /analysis/rumble, freemium YouTube route
│   ├── index.css              # Tailwind global styles
│   ├── api/
│   │   ├── client.js          # Shared request() helper, pollJob(), getPatterns()
│   │   ├── youtube.js         # startYouTubeAnalysis(), checkYouTubeResult()
│   │   ├── rumble.js          # startRumbleAnalysis(), checkRumbleResult(), getChannelVideos()
│   │   └── history.js         # getHistory()
│   ├── context/
│   │   ├── AuthContext.jsx    # AuthProvider + useAuth — login (display_id+name), register (name), mockSubscribe, logout
│   │   └── JobContext.jsx     # JobProvider + useJob — locks navigation while job is running
│   ├── auth/
│   │   ├── LoginPage.jsx      # /login — User ID number + First Name form, redirects on success
│   │   ├── RegisterPage.jsx   # /register — 3-step flow: name → mock PayPal payment → success + redirect
│   │   ├── ProtectedRoute.jsx # Auth gate — redirects to /login if not authenticated
│   │   └── SubscriptionGuard.jsx # YouTube gate — shows SubscriptionModal if not subscribed
│   ├── hooks/
│   │   └── usePersistedState.js  # sessionStorage-backed useState (per-tab, survives refresh)
│   ├── utils/
│   │   ├── markdown.js        # Heuristic markdown detection (scoring system, threshold >= 3)
│   │   └── metadata.js        # Shared metadata formatting utilities
│   ├── youtube/
│   │   └── YouTubeAnalysisPage.jsx  # YouTube URL input + PatternSelector + auto-check + analyze button
│   ├── rumble/
│   │   ├── RumbleAnalysisPage.jsx   # VideoPicker + URL input + PatternSelector + auto-check + analyze button
│   │   └── VideoPicker.jsx          # Searchable dropdown, ~400-450 videos, S/E sorted, paste-to-select
│   ├── history/
│   │   └── HistoryPage.jsx          # Filter by source + free-text search + expandable rows + copy/export (shows analyst info)
│   └── components/
│       ├── Layout.jsx               # Nav bar (Shield icon + "Marina's Wisdom"), user info + logout, mobile hamburger
│       ├── AnalysisRunner.jsx       # Polls /api/jobs/{id} every 2s, renders result (metadata + markdown)
│       ├── MarkdownResult.jsx       # react-markdown renderer with styled components + plain text fallback
│       ├── PatternSelector.jsx      # Search dropdown, 71 patterns, single-click highlight, double-click/Enter confirm, auto-check trigger
│       └── SubscriptionModal.jsx    # Modal for non-subscribers: subscribe or login
```

---

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | Public | Health check |
| GET | `/v1/models` | Public | OpenAI-compat stub (returns empty list) |
| POST | `/api/auth/register` | Public | `{first_name}` → `{access_token, user}` |
| POST | `/api/auth/login` | Public | `{display_id, first_name}` → `{access_token, user}` |
| GET | `/api/auth/me` | Required | Current user info |
| POST | `/api/payments/mock-subscribe` | Required | Mock PayPal — activates 30-day subscription |
| POST | `/api/youtube/analyze` | Subscriber | `{video_url, pattern}` → `{job_id, status}` |
| GET | `/api/youtube/jobs/{id}` | Subscriber | Poll YouTube job status + result |
| GET | `/api/youtube/check-result` | Subscriber | Duplicate check for YouTube |
| POST | `/api/rumble/analyze` | Public | `{video_url, pattern}` → `{job_id, status}` |
| GET | `/api/rumble/jobs/{id}` | Public | Poll Rumble job status + result |
| GET | `/api/rumble/check-result` | Public | Duplicate check for Rumble |
| GET | `/api/channel/videos` | Public | Cached channel video list |
| GET | `/api/jobs/{id}` | Public | Generic job poll (shared history — no user isolation) |
| GET | `/api/history` | Public | Paginated, filterable job history (shared — all users see all jobs) |
| GET | `/api/patterns` | Public | 71 curated Fabric patterns |
| GET | `/api/models` | Public | `{models: [], default: "..."}` |

---

## Key Environment Variables

| Variable | Default | Used In |
|---|---|---|
| `FABRIC_MODEL` | `deepseek/deepseek-v4-flash` | Fabric analysis (hard-wired, no model selector in UI) |
| `FABRIC_VENDOR` | `OpenRouter` | Fabric `-V` flag |
| `FABRIC_TIMEOUT` | `600` | Per-attempt timeout (seconds) |
| `FABRIC_MAX_RETRIES` | `3` | Max retries on 429 rate limit |
| `FABRIC_RETRY_BASE_DELAY` | `2.0` | Exponential backoff base (seconds) |
| `TRANSCRIPTION_MODEL` | `openai/gpt-audio-mini` | OpenRouter audio transcription model |
| `TRANSCRIPTION_CHUNK_SECONDS` | `600` | Audio chunk duration (10 min) |
| `OPENROUTER_API_BASE_URL` | `https://openrouter.ai/api/v1` | OpenRouter API base URL |
| `RUMBLE_CHANNEL` | `MarinaJacobi` | Only allow Rumble videos from this channel |
| `RUMBLE_CHANNEL_URL` | `https://rumble.com/c/MarinaJacobi` | Channel page URL for video listing |
| `CHANNEL_MAX_RESULTS` | `500` | Max channel videos to fetch |
| `CHANNEL_BATCH_SIZE` | `3` | Parallel page fetches for channel scraping |
| `CHANNEL_REFRESH_INTERVAL` | `3600` | Cache refresh interval (seconds, default 1 hour) |
| `VITE_API_BASE` | `http://localhost:8000/api` | Frontend API base |
| `JWT_SECRET` | Auto-generated (`.jwt_secret`) | HMAC key for JWT signing |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `JWT_EXPIRE_MINUTES` | `1440` (24 hours) | Token lifetime before expiry |

---

## Execution Model

**Analysis is async end-to-end:**

1. Frontend calls `POST /api/{source}/analyze` with `{video_url, pattern}`
2. Backend checks for **duplicate** by `source + video_url + pattern + model` → returns existing `job_id` if found
3. Otherwise: creates DB row (`status: "pending"`), spawns `asyncio.Task` for pipeline, returns `job_id` immediately
4. Frontend polls `GET /api/jobs/{id}` every 2 seconds via AnalysisRunner
5. Pipeline runs: `pending → running → completed/failed`
6. In-memory `_jobs` dict (`{job_id: asyncio.Task}`) tracks running tasks; cleaned up in `finally` blocks
7. Navigation is locked while a job is running (via JobContext)

### Pipeline Steps per Source

| Step | YouTube | Rumble |
|------|---------|--------|
| URL validation | `youtube.com` or `youtu.be` | `rumble.com` |
| Auth check | Requires active subscription (`require_subscriber`) | **None** — fully public |
| Metadata | yt-dlp (`--impersonate Chrome-133`, 10s timeout) | oEmbed API (primary) + cloudscraper page scrape (fallback) |
| Channel check | None | Must match `RUMBLE_CHANNEL` (env var, default `MarinaJacobi`) |
| Transcript | `youtube-transcript-api` (subtitles, no audio) | cloudscraper → parse embed JSON (`"ua"`/`"u"` blocks) → download audio → ffmpeg compress (mono 32k) → OpenRouter `gpt-audio-mini` transcription (chunked 10 min) |
| Analysis | `fabric -p <pattern> -m <model>` via stdin | Same |
| Cost estimate | tiktoken counting + live OpenRouter pricing (5-min cache) | Same (plus transcript cost from OpenRouter response) |
| Save | `update_job_status("completed", transcript, result, metadata_json, channel_*, video_*)` with analyst name + ID | Same |

### Duplicate Detection (Three Layers)

1. **Backend on submission** (`run_*_analysis`): matches `source + video_url + pattern + stored_model` on existing completed job → returns existing `job_id`
2. **Frontend on pattern confirm** (`GET /api/{source}/check-result`): proactive check before user clicks analyze — if found, AnalysisRunner displays existing result immediately
3. **Transcript caching** (`find_existing_transcript`): reuses previously-fetched transcript for same `source + video_url`

### Error Recovery

- Fabric calls retry up to 3× on HTTP 429 (exponential backoff: 2s, 4s, 8s)
- Metadata fetch has 10s timeout; failures are soft (empty metadata, analysis continues)
- Pipeline exceptions caught in `_pipeline()`: updates job to `failed` with error message
- Background channel cache refresh failures are silently swallowed (stale cache is served)
- Transcription cost from OpenRouter is best-effort (caught if missing)

---

## Database

- **File:** `marina_jacobi.db` (ignored by git, SQLite via aiosqlite)
- **Auto-created** on first run (`init_db` in `main.py` lifespan)

### Tables

**`analysis_jobs`**
| Column | Type | Notes |
|--------|------|-------|
| id | TEXT (UUID PK) | Auto-generated |
| source | TEXT NOT NULL | `youtube` or `rumble` |
| video_url | TEXT nullable | Source URL (renamed from `url` via migration) |
| file_path | TEXT nullable | Legacy — from removed file-upload feature |
| video_id | VARCHAR nullable | Extracted video ID |
| channel_id | VARCHAR nullable | Channel handle/ID |
| channel_title | TEXT nullable | Display name of channel |
| video_title | TEXT nullable | Video title from metadata |
| analyst_name | VARCHAR DEFAULT 'Anonymous' | First name of analyst who ran the job |
| analyst_display_id | INTEGER nullable | Display ID (#1, #2, etc.) of analyst |
| pattern | TEXT NOT NULL | Fabric pattern name |
| status | TEXT | `pending` → `running` → `completed` / `failed` |
| transcript | TEXT nullable | Extracted transcript text |
| result | TEXT nullable | LLM analysis output |
| error | TEXT nullable | Error message |
| metadata_json | JSON nullable | Model, cost, duration, processing time, video metadata |
| created_at | DATETIME | UTC (auto-generated) |
| updated_at | DATETIME | UTC (auto-updated) |

**`cache_store`**
| Column | Type | Notes |
|--------|------|-------|
| key | TEXT (PK) | e.g. `channel_videos` |
| value | TEXT | JSON-serialized data |
| updated_at | DATETIME | UTC |

**`users`**
| Column | Type | Notes |
|--------|------|-------|
| id | TEXT (UUID PK) | Auto-generated |
| display_id | INTEGER UNIQUE nullable | Auto-incrementing (#1, #2, #3...) |
| first_name | VARCHAR NOT NULL | User's first name (no email, no password!) |
| subscription_status | VARCHAR DEFAULT 'free' | `free` → `active` → `expired` |
| subscription_expires_at | DATETIME nullable | When the 30-day subscription expires |
| created_at | DATETIME | UTC |
| updated_at | DATETIME | UTC |

---

## External Dependencies (CLI Tools)

| Tool | Purpose | Source |
|------|---------|--------|
| **fabric** | AI pattern analysis (`fabric -p <pattern> -m <model>`) | Must be on `$PATH` |
| **yt-dlp** | Video metadata (`--impersonate Chrome-133`) | Used for YouTube metadata only |
| **ffmpeg / ffprobe** | Audio compression, duration detection, HLS stream download | Required for Rumble transcription |

### Python Packages (pip)
`fastapi`, `uvicorn`, `sqlalchemy`, `aiosqlite`, `pydantic`, `httpx`, `tiktoken`, `youtube-transcript-api`, `python-multipart`, `cloudscraper`, `python-jose[cryptography]`

### NPM Packages
`react@19`, `react-dom@19`, `react-router-dom@7`, `react-markdown@10`, `tailwindcss@4`, `@tailwindcss/vite@4`, `lucide-react`, `jspdf`, `vite@8`, `@vitejs/plugin-react@6`, `oxlint`

---

## User Flow Details

### Rumble Analysis (`/analysis/rumble`) — Free, No Login Required
1. Open `http://localhost:5173` → lands on Rumble analysis page
2. **VideoPicker** shows searchable dropdown of ~400-450 channel videos (fetched from Rumble, DB-cached, S/E sorted)
   - Pick a video → URL auto-fills, input turns green (title-resolved)
   - Paste a title or URL → auto-matches to channel video if found
   - Double-click input to clear selection
3. PatternSelector: search patterns (71 curated), single-click to highlight, double-click or Enter to confirm
4. On pattern confirmation → auto-check fires → checks for existing result via `/api/rumble/check-result`
   - **Found:** displays existing result immediately (AnalysisRunner)
   - **Not found:** shows red inline box "No prior analysis found — just click the button or press the Enter key"
5. Channel restriction: only `MarinaJacobi` allowed (configurable via `RUMBLE_CHANNEL` env var)
6. Click "Analyze Rumble Video" or press Enter → analysis starts (no auth needed!)
7. AnalysisRunner polls every 2s, renders result + metadata + copy/export/transcript buttons
8. Every result shows the analyst's first name + ID (#7), or "Anonymous" if no user was signed in

### YouTube Analysis (`/analysis/youtube`) — Subscription Required
1. Click the **YouTube** nav tab
2. If not authenticated: **SubscriptionModal** appears
   - Not logged in: shows info + [Subscribe $7/month] (→ `/register`) + [Already a subscriber] (→ `/login`)
   - Logged in but not subscribed: shows inline mock PayPal payment → mockSubscribe → redirects to YouTube
3. Once subscribed: YouTube analysis page appears
   - Enter YouTube URL in text input
   - Same PatternSelector + auto-check flow as Rumble
   - Press Enter (when pattern is green/confirmed) or click "Analyze YouTube Video" → analysis starts
4. AnalysisRunner polls every 2s, renders result + metadata + copy/export/transcript buttons
5. Every result shows the analyst's first name + ID (#1, #2, etc.)

### Registration & Subscription (`/register`)
1. Enter your **first name only** (no email, no password)
2. Account created with `subscription_status: "free"`
3. Mock PayPal UI: shows gray PayPal card with $7/month details
4. Click "Confirm $7/month" → activates 30-day subscription
5. Success screen → auto-redirects to YouTube analysis

### Login (`/login`)
1. Enter your **User ID number** (e.g. 7) + **First Name**
2. On success → redirected to YouTube analysis
3. Forgot your ID? Check your previous analysis results — they show `Analyst: Sarah (#7)`

### History (`/history`) — Public, No Login Required
1. Filter by source: All / Youtube / Rumble (buttons)
2. Free-text search: searches across URL, title, channel, analyst name, pattern, result, transcript, UTC date
3. Expandable rows: click to expand/collapse
4. Collapsed view shows: analyst name + ID, video URL, source, pattern, UTC time
5. Expanded view: metadata header + result (markdown-rendered) + transcript + error (if failed)
6. Action buttons: Copy Result, Copy Transcript, Open This Video (external link)

### State Persistence
- `usePersistedState` stores: active URL inputs, pattern confirmation in `sessionStorage`
- Survives page refresh but not cross-tab (sessionStorage is per-tab)
- RumbleAnalysisPage explicitly clears pattern persistence on mount (`sessionStorage.removeItem`)

---

## Routing

| Path | Component | Auth | Description |
|------|-----------|------|-------------|
| `/login` | LoginPage | No | Login form (User ID + First Name) |
| `/register` | RegisterPage | No | Registration (name → mock PayPal → success) |
| `/` | `Navigate to /analysis/rumble` | — | Root redirect — Rumble is the landing page |
| `/analysis/youtube` | SubscriptionGuard + ProtectedRoute + Layout + YouTubeAnalysisPage | Subscriber | YouTube analysis |
| `/analysis/rumble` | Layout + RumbleAnalysisPage | Public | Rumble analysis — **free, no login** |
| `/history` | Layout + HistoryPage | Public | Shared history — **no login needed** |

---

## Frontend UI Patterns

### Pattern Selection (PatternSelector)
- **Search:** typing filters dropdown in real-time (71 curated patterns)
- **Numbered prefixes:** each pattern shown as `N: name` in dropdown for easy reference
- **Single click:** highlights violet, does NOT confirm
- **Double-click** (within 400ms): confirms → input turns green, dropdown closes, `onConfirm` fires (auto-check)
- **Enter** (dropdown visible): selects highlighted (or first match), confirms, fires `onConfirm`, closes dropdown
- **Enter** (pattern already green): runs analysis immediately via `onEnter`
- **Arrow keys:** navigate with scroll-into-view
- **Confirmed pattern shows green number prefix** in input field

### Video Picker (VideoPicker)
- Search across ~400-450 channel videos
- Season/episode extracted from title (regex: `S5 E3`, `Season 5 Episode 3`, `S5E3`, etc.)
- Sorted by (season, episode) for precise ordering, unknown at end (999, 999)
- Search normalizes spaces in S/E patterns so "S8 E11" matches "S8E11"
- Arrow key navigation with scroll-into-view
- Enter to select, paste-to-match (by title)
- Shows video number, duration, view count, upload date
- Double-click input to clear selection

### Analysis Metadata Display (inline in AnalysisRunner + History)
Displayed fields (when present in metadata_json):
- Title, Title URL, Channel, Channel URL
- Views (locale-formatted), Video Length (H:MM:SS or M:SS)
- Published date + relative time ("2 years ago")
- Fabric Pattern, Model used, Processing Time (seconds)
- Input/Output tokens (via tiktoken), Estimated cost (USD)
- Pricing Source

### Subscriber's Nav Bar
- Logo (Shield + "Marina's Wisdom") links to `/analysis/rumble`
- Shows user info when authenticated: `Sarah (#7)`
- Shows "Subscribe" link when not authenticated
- Mobile menu shows "Subscribe for YouTube Access" link + nav items

---

## Known Quirks & Gotchas

### Backend
- **`sys.path.insert(0, ...)` hack** in `main.py` — needed for absolute `from backend...` imports when run as `uvicorn backend.main:app`. Do NOT remove.
- **run.sh** CDs into `backend/`, activates `.venv`, then `cd ..` so `backend.main` resolves as a package. `.venv` is inside `backend/`.
- **JWT auth:** Token-based (HS256), auto-generated secret persisted to `.jwt_secret` at repo root. Token expires after 24h (configurable via `JWT_EXPIRE_MINUTES`). Frontend stores token in `localStorage`.
- **No passwords:** Users register with just a first name. Login requires display ID + first name. No bcrypt/passlib — JWT tokens are the only auth mechanism.
- **`is_subscription_active` timezone handling:** SQLite stores naive datetimes. The comparison strips tzinfo from `datetime.now(timezone.utc)` via `.replace(tzinfo=None)` to match the naive stored value.
- **Freemium enforcement:** `require_subscriber` dependency returns HTTP 401 if no token, HTTP 402 if subscription expired. Used only on YouTube routes. Rumble routes have zero auth checks.
- **Subscription model:** Mock PayPal activates 30-day subscription. No auto-renewal. No real payment processing.
- **Shared history:** ALL analysis is visible to everyone. No user isolation. Every job stores `analyst_name` and `analyst_display_id` for attribution.
- **`_next_display_id` safety:** Falls back to 1 if the users table query fails (handles race condition at first registration).
- **UTC time serialization:** Pydantic `field_serializer` appends `+00:00` to naive datetimes from SQLite. Frontend defensively appends `Z`.
- **Channel cache datetime bug (fixed):** Naive vs aware datetime comparison in cache age check (Python 3.12+). Fixed by stripping tzinfo before comparison.
- **Stuck-job bug (fixed):** `update_job_status("running")` was outside the try block in orchestrators — silent death left status at `pending`. Now inside try block.
- **Rumble metadata:** Uses oEmbed API (`rumble.com/api/Media/oembed.json`) as primary source (bypasses Cloudflare), falls back to cloudscraper page scrape for additional fields (view count, upload date).
- **Rumble transcription:** Downloads raw audio from embed JSON (`"ua"` / `"u"` blocks), selects best format (prefers aac/mp3/m4a over mp4/webm, uses bitrate as tiebreaker). Falls back to ffmpeg for HLS (m3u8) streams. Rejects `.tar` format.
- **OpenRouter API key:** Read from `~/.config/fabric/.env` at runtime (not from environment variables). Both `openrouter_service.py` and `cost_service.py` read it independently.
- **No cancellation mechanism:** Running background tasks cannot be cancelled. The `_jobs` dict tracks task lifecycle but provides no cancel interface.

### Frontend
- **`index.html` title** still shows "OSINT-1" — not rebranded to "Marina's Wisdom"
- **MetadataDisplay.jsx** referenced in earlier docs does not exist in current code — metadata display is inlined in AnalysisRunner.jsx and HistoryPage.jsx
- **Duplicated `request()` helper** in each API module (youtube.js, rumble.js, history.js) — identical code repeated 3 times
- **Double-click detection** uses click-timing detector (400ms threshold) rather than native `ondblclick` — because Chrome DevTools responsive/touch mode doesn't fire `ondblclick`
- **Dropdown overlay bug (fixed):** Replaced `fixed inset-0` overlay with `onBlur` on input to prevent interception of clicks
- **TestClient vs ASGITransport:** When running tests, use Starlette/httpx `TestClient` (which triggers the async lifespan) rather than raw `AsyncClient + ASGITransport` (which may not run the lifespan).

### Rumble Channel Video Service
- Uses `cloudscraper` to bypass Cloudflare on Rumble channel pages
- Parses `<rum-videos-grid><script type="application/json">` for video list data
- Follows `rel=next` pagination links across all pages (~17 pages, ~400-450 videos)
- Season/episode parsing: flexible regex handles "S5 E3", "S5E3", "Season 5 Episode 3", "S 5  E 3"
- DB-persisted cache via `cache_store` table — survives restarts, refreshed hourly in background
- First-ever fetch is synchronous (~20s); subsequent requests instant from DB

---

## Removed Features (Not Coming Back Without Rewrite)

- **Web scraping** (`/api/analyze` with `source=web` + Jina Reader API) — deleted
- **File upload** (`/api/analyze/file` + multipart upload) — deleted
- **Model selector** in UI — removed; only `FABRIC_MODEL` env var controls the model
- **`/api/models` endpoint** — returns empty list (hard-wired model)
- **Old DB** (`cve_osint.db`) — replaced by `marina_jacobi.db`; no auto-migration
- **Password auth** (bcrypt/passlib) — removed; no passwords, just first name + display ID
- **User-isolated history** — removed; all jobs are shared in one public history

---

## Possible Next Steps (Not Planned)

1. **YouTube channel video picker** — no equivalent of Rumble's VideoPicker for YouTube
2. **Multiple channels** — currently hard-wired to `MarinaJacobi`; could support channel selector
3. **Analysis cancellation** — no way to stop a running analysis
4. **Delete jobs from history** — no delete functionality
5. **Real PayPal integration** — currently uses mock payment; needs production PayPal setup
6. **Subscription auto-renewal** — mock payment grants 30 days with no renewal
7. **Tests** — no test framework exists anywhere in the codebase

---

## Developer Commands

```bash
# Frontend
cd frontend && npm run dev            # Dev server with HMR on localhost:5173
cd frontend && npm run build           # Production build
cd frontend && npm run lint            # oxlint (no ESLint)
cd frontend && npm run preview         # Preview production build

# Backend (from backend/ dir with .venv active)
./run.sh                               # uvicorn 0.0.0.0:8000 --reload
```

No test framework is set up for either backend or frontend.

---

## .claude/settings.local.json

Located at repo root. Currently configures OpenRouter as the AI provider for Claude Code itself (not for the app):
```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "https://openrouter.ai/api",
    "ANTHROPIC_AUTH_TOKEN": "sk-or-v1-...",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "deepseek/deepseek-v4-flash"
  }
}
```