# AGENTS.md — Marina's Wisdom

Self-hosted OSINT app for analyzing YouTube and Rumble videos using AI-powered analysis patterns (Fabric CLI → OpenRouter API).

```
React 19 (Vite 8, port 5174) → FastAPI (port 8000) → fabric CLI → OpenRouter API
                                                                ↕
                                                           SQLite (marina_jacobi.db)
```

**Freemium model:** Rumble (Marina Jacobi) analysis is **free** — no signup required, no account, and one **shared history** for everyone. YouTube analysis requires an **account** (full name + email + password) and then either a **33-use free trial** (available immediately) or a **$7/month subscription** via mock PayPal. YouTube history is **private per user** — nobody else can see it.

Every account is granted the 33 trial uses at signup, whether or not the user then subscribes, so a lapsed subscriber falls back to whatever trial uses were left rather than being locked out. **There is no password reset** — no email is ever sent — so a forgotten password permanently costs the account and its private history.

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
cd frontend && npm install && npm run dev  # Vite on localhost:5174
```

Open http://localhost:5174 — root redirects to `/analysis/rumble` (free, no signup). Clicking YouTube triggers a subscription modal prompting registration + payment.

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
│   ├── router.py              # POST /register (full_name + email + password), POST /login (email + password), GET /me
│   └── dependencies.py        # get_current_user (optional, returns User|None), require_youtube_access
│                              # (subscriber OR trial -> YouTubeAccess), require_subscriber (legacy, now unused)
├── payments/                  # Mock PayPal payment
│   ├── __init__.py
│   └── router.py              # POST /mock-subscribe — activates 30-day subscription
├── youtube/                   # YouTube feature package
│   ├── __init__.py
│   ├── router.py              # POST /analyze, GET /jobs/{id}, GET /check-result (all require_youtube_access)
│   ├── schemas.py             # YouTubeRequest, JobStatusResponse
│   ├── service.py             # youtube-transcript-api subtitle fetching
│   ├── orchestrator.py        # Analysis pipeline (async task) — accepts user_id/trial_user_id, refunds on failure
│   └── db_helpers.py          # CRUD, user-scoped duplicate detection, per-user transcript caching;
│                              # create_job consumes a trial use in the same transaction as the INSERT
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
│   ├── router.py              # /api/health, /api/jobs/{id}, /api/history, /api/patterns, /api/models
│   │                          # (Rumble stays public; /jobs/{id} + /history take OPTIONAL auth to scope YouTube)
│   ├── schemas.py             # JobStatusResponse, HistoryFilter
│   └── db_helpers.py          # list_jobs/get_job — shared-Rumble + own-YouTube visibility rules
└── services/                  # Shared infrastructure
    ├── auth_service.py        # JWT (HS256), register_user/login_by_email, display_id allocation, subscriptions
    ├── password_service.py    # bcrypt hash/verify (bcrypt directly, NOT passlib) + 72-byte truncation guard
    ├── trial_service.py       # Free-trial quota: atomic decrement_trial_use, idempotent refund_trial_use
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
│   │   ├── AuthContext.jsx    # AuthProvider + useAuth — login (email+password), register (name+email+password),
│   │   │                      # trialUsesRemaining / isTrial / hasYouTubeAccess, refreshUser, applyTrialRemaining
│   │   └── JobContext.jsx     # JobProvider + useJob — locks navigation while job is running
│   ├── auth/
│   │   ├── LoginPage.jsx      # /login — email + password; static "forgot password" notice (no reset exists)
│   │   ├── RegisterPage.jsx   # /register — one form, then choose free trial or $7/month mock PayPal
│   │   ├── ProtectedRoute.jsx # Auth gate — redirects to /login (must run BEFORE SubscriptionGuard)
│   │   └── SubscriptionGuard.jsx # YouTube gate — owns Layout; locked panel + modal, never a blank page
│   ├── hooks/
│   │   └── usePersistedState.js  # sessionStorage-backed useState (per-tab, survives refresh)
│   ├── utils/
│   │   ├── markdown.js        # Heuristic markdown detection (scoring system, threshold >= 3)
│   │   └── metadata.js        # Shared metadata formatting utilities
│   ├── youtube/
│   │   └── YouTubeAnalysisPage.jsx  # YouTube URL input + PatternSelector + auto-check + analyze button
│   │                                # + "N of 33 free analyses left" counter and exhausted panel
│   ├── rumble/
│   │   ├── RumbleAnalysisPage.jsx   # VideoPicker + URL input + PatternSelector + auto-check + analyze button
│   │   └── VideoPicker.jsx          # Searchable dropdown, ~400-450 videos, S/E sorted, paste-to-select
│   ├── history/
│   │   └── HistoryPage.jsx          # Filter by source + free-text search + expandable rows + copy/export (shows analyst info)
│   └── components/
│       ├── Layout.jsx               # Nav bar (Shield icon + "Marina's Wisdom"), user info + logout, mobile hamburger
│       │                            # + "Trial · N left" badge (amber at N <= 5)
│       ├── AnalysisRunner.jsx       # Polls /api/jobs/{id} every 2s, renders result (metadata + markdown)
│       ├── MarkdownResult.jsx       # react-markdown renderer with styled components + plain text fallback
│       ├── PatternSelector.jsx      # Search dropdown, 71 patterns, single-click highlight, double-click/Enter confirm, auto-check trigger
│       └── SubscriptionModal.jsx    # Upsell: start the free trial, subscribe $7/month, or log out
```

---

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | Public | Health check |
| GET | `/v1/models` | Public | OpenAI-compat stub (returns empty list) |
| POST | `/api/auth/register` | Public | `{full_name, email, password}` → `{access_token, user}`; 400 bad email/short or >72-byte password, 409 email taken |
| POST | `/api/auth/login` | Public | `{email, password}` → `{access_token, user}`; 401 with one message for both wrong-email and wrong-password |
| GET | `/api/auth/me` | Required | Current user info (includes `trial_uses_remaining`) |
| POST | `/api/payments/mock-subscribe` | Required | Mock PayPal — activates 30-day subscription (leaves the trial untouched) |
| POST | `/api/youtube/analyze` | Subscriber or trial | `{video_url, pattern}` → `{job_id, status, trial_uses_remaining}`; 402 `trial_exhausted` when out of uses |
| GET | `/api/youtube/jobs/{id}` | Subscriber or trial | Poll YouTube job status + result — **owner only**, 404 otherwise |
| GET | `/api/youtube/check-result` | Subscriber or trial | Duplicate check, scoped to the caller; never decrements |
| POST | `/api/rumble/analyze` | Public | `{video_url, pattern}` → `{job_id, status}` |
| GET | `/api/rumble/jobs/{id}` | Public | Poll Rumble job status + result |
| GET | `/api/rumble/check-result` | Public | Duplicate check for Rumble |
| GET | `/api/channel/videos` | Public | Cached channel video list |
| GET | `/api/jobs/{id}` | Optional user | Rumble jobs public; YouTube jobs owner-only (404 otherwise, even logged out) |
| GET | `/api/history` | Optional user | Shared Rumble history + the caller's own YouTube history |
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
| `JWT_SECRET` | Auto-generated (`backend/.jwt_secret`) | HMAC key for JWT signing. Written on first token signing, **not** at startup, and gitignored |
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
| Auth check | `require_youtube_access` — subscription **or** trial account | **None** — fully public |
| Metadata | yt-dlp (`--impersonate Chrome-133`, 10s timeout) | oEmbed API (primary) + cloudscraper page scrape (fallback) |
| Channel check | None | Must match `RUMBLE_CHANNEL` (env var, default `MarinaJacobi`) |
| Transcript | `youtube-transcript-api` (subtitles, no audio) | cloudscraper → parse embed JSON (`"ua"`/`"u"` blocks) → download audio → ffmpeg compress (mono 32k) → OpenRouter `gpt-audio-mini` transcription (chunked 10 min) |
| Analysis | `fabric -p <pattern> -m <model>` via stdin | Same |
| Cost estimate | tiktoken counting + live OpenRouter pricing (5-min cache) | Same (plus transcript cost from OpenRouter response) |
| Save | `update_job_status("completed", transcript, result, metadata_json, channel_*, video_*)` with analyst name + ID | Same |

### Duplicate Detection (Three Layers)

1. **Backend on submission** (`run_*_analysis`): matches `source + video_url + pattern + stored_model` on an existing job → returns existing `job_id`. For YouTube the match is scoped to the caller, so one user's analysis is never served to another. **Runs before the quota check**, so re-opening a result you already own is free and works even at 0 trial uses left.
2. **Frontend on pattern confirm** (`GET /api/{source}/check-result`): proactive check before user clicks analyze — if found, AnalysisRunner displays existing result immediately. Never decrements.
3. **Transcript caching** (`find_existing_transcript`): reuses a previously-fetched transcript. YouTube scopes this to the owner too; Rumble keeps one shared cache.

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
| analyst_display_id | INTEGER nullable | Display ID (#1, #2, etc.) of analyst — **not unique**, so never use it as an owner key |
| user_id | TEXT nullable (indexed) | Job owner. **NULL for Rumble** (free/shared); set for YouTube (private) |
| trial_use_consumed | BOOLEAN DEFAULT false | True when the job spent a trial use. Doubles as the claim flag that makes `refund_trial_use` idempotent |
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
| display_id | INTEGER UNIQUE nullable | Auto-incrementing (#1, #2, #3...) — display/attribution only, NOT a credential |
| first_name | VARCHAR NOT NULL | Derived from the first token of `full_name`; drives the nav bar and attribution |
| full_name | VARCHAR nullable | As typed at signup |
| email | VARCHAR NOT NULL UNIQUE | Login identity, stored lowercased (so the unique index is case-insensitive) |
| password_hash | VARCHAR NOT NULL | bcrypt; never serialized by any endpoint |
| trial_uses_remaining | INTEGER nullable | `33` at signup, counts down per new analysis. **NULL = no trial** (distinct from `0` = used up) |
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
1. Open `http://localhost:5174` → lands on Rumble analysis page
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
8. Every result shows the analyst's first name + ID (#7), or "Anonymous" if no user was signed in. Rumble results are visible to everyone via History.

### YouTube Analysis (`/analysis/youtube`) — Subscription Required
1. Click the **YouTube** nav tab
2. If not authenticated: `ProtectedRoute` sends you to `/login` first; the upsell modal appears for a logged-in user without access
   - Not logged in: [Start free trial — 33 analyses, no card] (→ `/register`) + [Subscribe $7/month] + [Already a subscriber] (→ `/login`)
   - Logged in on a trial: [Continue with free trial (N left)] + [Subscribe $7/month] (inline mock PayPal) + [Log out]
   - Trial used up: an exhausted banner, and only the subscribe path remains
   - A locked panel renders *behind* the modal, so dismissing it never leaves a blank page with no nav
3. With access (subscription or trial uses left): YouTube analysis page appears
   - A counter reads "Free trial: N of 33 analyses left" (amber at 5 or fewer); at 0 it becomes an exhausted panel and the analyze button is disabled, though auto-check can still re-open your own earlier results
   - Enter YouTube URL in text input
   - Same PatternSelector + auto-check flow as Rumble
   - Press Enter (when pattern is green/confirmed) or click "Analyze YouTube Video" → analysis starts, and the counter ticks from the response
4. AnalysisRunner polls every 2s, renders result + metadata + copy/export/transcript buttons
5. Every result shows the analyst's first name + ID (#1, #2, etc.)

### Registration & Subscription (`/register`)
1. One form: **full name, email, password** (min 8 chars, max 72 bytes). The form states plainly that there is no password reset.
2. Account created with `subscription_status: "free"` and `trial_uses_remaining: 33`
3. Choose: **Start your free trial** (straight to YouTube analysis — nothing to activate) or **Subscribe $7/month** → mock PayPal card → "Confirm $7/month" → activates a 30-day subscription
4. Either way the account keeps its 33 trial uses, so a lapsed subscriber is not worse off than a new user

### Login (`/login`)
1. Enter your **email + password**
2. On success → redirected to YouTube analysis
3. **Forgot your password?** Nothing can be done — there is no reset flow and no email is sent. The page says so instead of offering a dead-end link

### History (`/history`) — No Login Required for Rumble
1. Filter by source: All / Youtube / Rumble (buttons)
2. Free-text search: searches across URL, title, channel, analyst name, pattern, result, transcript, UTC date
3. Expandable rows: click to expand/collapse
4. Collapsed view shows: analyst name + ID, video URL, source, pattern, UTC time
5. Expanded view: metadata header + result (markdown-rendered) + transcript + error (if failed)
6. Action buttons: Copy Result, Copy Transcript, Open This Video (external link)
7. **Visibility:** `All` = every Rumble job plus only your own YouTube jobs. `Rumble` = shared timeline. `Youtube` logged out = an explicit "history is private" notice, not "no results yet". The list re-fetches on login/logout.

### State Persistence
- `usePersistedState` stores: active URL inputs, pattern confirmation in `sessionStorage`
- Survives page refresh but not cross-tab (sessionStorage is per-tab)
- RumbleAnalysisPage explicitly clears pattern persistence on mount (`sessionStorage.removeItem`)

---

## Routing

| Path | Component | Auth | Description |
|------|-----------|------|-------------|
| `/login` | LoginPage | No | Login form (email + password) |
| `/register` | RegisterPage | No | Signup (full name + email + password) → choose free trial or $7/month |
| `/` | `Navigate to /analysis/rumble` | — | Root redirect — Rumble is the landing page |
| `/analysis/youtube` | ProtectedRoute + SubscriptionGuard (owns Layout) + YouTubeAnalysisPage | Subscriber **or trial** | YouTube analysis. `ProtectedRoute` runs **first** — nested the other way its `/login` redirect is unreachable, because the guard returns before it renders |
| `/analysis/rumble` | Layout + RumbleAnalysisPage | Public | Rumble analysis — **free, no login** |
| `/history` | Layout + HistoryPage | Public | Shared Rumble history + your own YouTube history — **no login needed for Rumble** |
| `*` | `Navigate to /analysis/rumble` | — | Catch-all — an unknown path lands on the free page instead of a blank screen |

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

### Authenticated Nav Bar
- Logo (Shield + "Marina's Wisdom") links to `/analysis/rumble`
- Shows user info when authenticated: `Sarah (#7)` (`first_name` + `display_id`)
- Shows a **"Trial · N left"** badge for a trial account who is not subscribed — amber at N <= 5. Hidden for subscribers, who also still have trial uses on the account but are not using them
- Shows a "Get YouTube access" link (→ `/register`) when not authenticated
- Mobile menu mirrors both, and the label is "Get YouTube Access" there

---

## Known Quirks & Gotchas

### Backend
- **`sys.path.insert(0, ...)` hack** in `main.py` — needed for absolute `from backend...` imports when run as `uvicorn backend.main:app`. Do NOT remove.
- **run.sh** CDs into `backend/`, activates `.venv`, then `cd ..` so `backend.main` resolves as a package. `.venv` is inside `backend/`.
- **JWT auth:** Token-based (HS256), auto-generated secret persisted to **`backend/.jwt_secret`** (not the repo root, despite older notes). Token expires after 24h (configurable via `JWT_EXPIRE_MINUTES`). Frontend stores token in `localStorage`. The secret is **gitignored** — it was committed until this change, which let anyone with repo access forge a token for any account. Never re-commit it.
- **Passwords:** Accounts use **bcrypt directly** (`password_service.py`) — deliberately not `passlib`, which is unmaintained and breaks against bcrypt 4.x+. Anything over **72 bytes** is rejected rather than truncated, because bcrypt silently ignores the excess and two different long passwords would otherwise authenticate the same account. `display_id` is display/attribution only and is **no longer a credential**.
- **No password reset exists.** Nothing is emailed. A forgotten password means permanent loss of the account and its private YouTube history — the signup and login pages state this. Adding one needs an email provider, which this app does not have.
- **`is_subscription_active` timezone handling:** SQLite stores naive datetimes. The comparison strips tzinfo from `datetime.now(timezone.utc)` via `.replace(tzinfo=None)` to match the naive stored value.
- **YouTube access:** `require_youtube_access` returns HTTP 401 with no token, and HTTP 402 (`subscription_required`) for an account with no trial at all. It admits a subscriber **or any trial account, including one with 0 uses left** — the quota is enforced at consume time instead, because only the consume can tell a genuinely new job from a duplicate the user already paid for. Rejecting at 0 in the dependency would lock a user out of their own results. The 402 `trial_exhausted` in the API comes from the handler when the atomic consume fails. `require_subscriber` is still defined but no longer used by any route.
- **Trial quota mechanics:** The authoritative gate is a single conditional UPDATE (`WHERE trial_uses_remaining > 0`) issued **in the same transaction as the job INSERT**, so two tabs both seeing "1 left" cannot both succeed. Failures refund; duplicate hits are free. `refund_trial_use` claims the job's `trial_use_consumed` flag before crediting, so the pipeline handler and the boot sweeper cannot both refund.
- **Refunds have two handlers:** `asyncio.CancelledError` inherits from `BaseException`, so it skips `except Exception` and needs its own clause. A hard kill bypasses both, which is why `main.py`'s boot sweeper refunds the jobs it marks failed at startup.
- **Subscription model:** Mock PayPal activates 30-day subscription. No auto-renewal. No real payment processing. Subscribing deliberately does **not** consume or reset the trial counter.
- **History isolation:** Rumble rows have `user_id IS NULL` and are shared with everyone. YouTube rows carry an owner and are visible only to that user — including a **404, never 403**, for someone else's job id (a 403 would confirm a guessed id exists). `list_jobs` with no `source` filter returns `or_(source != 'youtube', user_id == uid)`; a logged-out caller gets Rumble only, and `?source=youtube` logged out returns `[]` rather than everyone's history. Unscoped, `find_existing_job_id` would hand user B user A's job id — which B's own ownership check would then 404, so B would never receive the analysis the isolation rule promises.
- **`_next_display_id` safety:** Falls back to 1 if the users table query fails (handles race condition at first registration).
- **UTC time serialization:** Pydantic `field_serializer` appends `+00:00` to naive datetimes from SQLite. Frontend defensively appends `Z`.
- **Channel cache datetime bug (fixed):** Naive vs aware datetime comparison in cache age check (Python 3.12+). Fixed by stripping tzinfo before comparison.
- **Stuck-job bug (fixed):** `update_job_status("running")` was outside the try block in orchestrators — silent death left status at `pending`. Now inside try block.
- **Rumble metadata:** Uses oEmbed API (`rumble.com/api/Media/oembed.json`) as primary source (bypasses Cloudflare), falls back to cloudscraper page scrape for additional fields (view count, upload date).
- **Rumble transcription:** Downloads raw audio from embed JSON (`"ua"` / `"u"` blocks), selects best format (prefers aac/mp3/m4a over mp4/webm, uses bitrate as tiebreaker). Falls back to ffmpeg for HLS (m3u8) streams. Rejects `.tar` format.
- **OpenRouter API key:** Read from `~/.config/fabric/.env` at runtime (not from environment variables). Both `openrouter_service.py` and `cost_service.py` read it independently.
- **No cancellation mechanism:** Running background tasks cannot be cancelled. The `_jobs` dict tracks task lifecycle but provides no cancel interface.
- **The trial is abusable, and login is brute-forceable.** Signup grants 33 real OpenRouter calls with no email verification and the app has no rate limiting, so a disposable-email script can spend the owner's OpenRouter balance without bound. Accepted for a local/self-hosted app; both need addressing before it faces the internet.
- **A systematically failing URL re-charges on each retry** — failed rows are excluded from dedup. Net-neutral (each failure refunds), but the counter visibly dips and recovers.
- **`backend/.venv` vs the IDE interpreter:** the repo root also has a stale `.venv`. `run.sh` uses `backend/.venv`, which is the one that has `bcrypt`. IDE "module not found" warnings for `bcrypt` come from the wrong interpreter.
- **`OPENROUTER_API_KEY` can be shadowed by the host environment.** Fabric gives real env vars priority over `~/.config/fabric/.env`, so a placeholder exported into the systemd user environment makes every analysis fail with `401 Missing Authentication header`. `systemctl --user unset-environment OPENROUTER_API_KEY` fixes it; until re-login, start the backend with `env -u OPENROUTER_API_KEY`.

### Frontend
- **Dev server port is set in `frontend/vite.config.js`, NOT in this doc** — editing AGENTS.md does not change the port. Current setting: `server: { port: 5174, strictPort: true }`. If you ever change the port again, you must **also** update `allow_origins` in `backend/main.py` (currently `http://localhost:5174` + `http://127.0.0.1:5174`), or the browser will block every API call with a CORS error. Docs to keep in sync: AGENTS.md, SETUP.md, README.md.
- **`strictPort: true`** means `npm run dev` fails loudly if 5174 is occupied instead of silently bumping to 5175 — deliberate, because CORS only allowlists 5174.
- **`index.html` title** still shows "OSINT-1" — not rebranded to "Marina's Wisdom"
- **MetadataDisplay.jsx** referenced in earlier docs does not exist in current code — metadata display is inlined in AnalysisRunner.jsx and HistoryPage.jsx
- **Duplicated `request()` helper** in each API module (youtube.js, rumble.js, history.js) — identical code repeated 3 times. The shared one in `client.js` parses structured errors into `err.status` / `err.code` / `err.data` while keeping `err.message` a human string, so a 402 no longer renders as raw JSON on the page. A 401 from `/auth/login`, `/auth/register` or `/auth/me` is **not** treated as a session expiry — otherwise a wrong password would clear the token and the mount-time `/me` probe would bounce a visitor off the free Rumble page.
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
- **Passwordless auth** (first name + display ID) — removed; replaced by email + password (`bcrypt` directly, **not** `passlib`). `display_id` survives as display/attribution only
- **Globally shared YouTube history** — removed; YouTube rows are per-user, shared Rumble rows are not. Fully user-isolated history is *not* what this is: Rumble stays one public list

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
cd frontend && npm run dev            # Dev server with HMR on localhost:5174
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