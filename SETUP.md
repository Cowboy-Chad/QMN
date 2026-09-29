# Full Startup Guide — Marina's Wisdom

**Freemium Model:** Rumble (Marina Jacobi) analysis is **free** — no signup required, and its history is shared with everyone. YouTube analysis requires an account (full name + email + password) and either a **33-use free trial** or a **$7/month subscription** via mock PayPal. YouTube history is private to each account.

> **There is no password reset.** Nothing is emailed — a forgotten password permanently costs the account and its private YouTube history. The signup and login pages say so.

---

## Prerequisites (one-time setup outside the repo)

```bash
# Python 3.12+
python3 --version

# Node.js 22.12+ (Vite 8 requires ^20.19 || >=22.12)
node --version

# Docker or podman — supplies the local Postgres
docker --version

# Fabric CLI on PATH
fabric --version

# OpenRouter API key: as an environment variable, or in fabric's config.
# The app checks the environment first and falls back to this file.
echo "OPENROUTER_API_KEY=sk-or-v1-..." > ~/.config/fabric/.env

# ffmpeg + ffprobe (required for Rumble audio transcription)
ffmpeg -version

# yt-dlp (required for YouTube metadata)
yt-dlp --version
```

---

## 1. Database (one-time, then just needs to be running)

```bash
# Navigate to repo root
cd /home/cowboy/000/cve-marina-1

# Start Postgres 17 in a container. The default DATABASE_URL in backend/database.py
# points here, so no .env is needed for local development.
docker compose up -d db

# Apply migrations. Alembic owns the schema — the app never creates tables.
source backend/.venv/bin/activate
alembic upgrade head

# After any change to backend/models.py:
alembic revision --autogenerate -m "describe the change"   # then READ the generated file
alembic check          # "No new upgrade operations detected" == models and migration agree
```

`docker compose down` stops it; the data survives in a named volume. `docker compose down -v`
wipes it.

---

## 2. Backend Setup & Start

```bash
# Navigate to repo root, then into backend/
cd /home/cowboy/000/cve-marina-1/backend

# Create virtual environment (one-time)
python3 -m venv .venv

# Activate it
source .venv/bin/activate

# Install Python dependencies (one-time)
pip install -r requirements.txt

# Start the backend server (with --reload for auto-restart on changes)
./run.sh
```

**The backend starts on `http://0.0.0.0:8000`.**

- The schema comes from `alembic upgrade head` above. If the backend reports a missing column, the
  migration has not been applied — it does not create tables itself.
- Auto-generates **`backend/.jwt_secret`** (JWT signing key) the first time a token is signed — not
  at startup, and not at the repo root. It is **gitignored**; never commit it. If `JWT_SECRET` is
  set in the environment, that value wins and no file is written.
- `.env` is entirely optional locally — see [`.env.example`](.env.example) for every variable.

---

## 3. Frontend Setup & Start (separate terminal)

```bash
# Navigate to frontend directory
cd /home/cowboy/000/cve-marina-1/frontend

# Install npm dependencies (one-time)
npm install

# Start the Vite dev server (with HMR)
npm run dev
```

**The frontend starts on `http://localhost:5174`** (set in `frontend/vite.config.js`).

---

## 4. User Flow

| Step | Action | Result |
|------|--------|--------|
| 1 | Open `http://localhost:5174` | Redirected to **Rumble Analysis** page (`/analysis/rumble`) — **free, no login needed** |
| 2 | Pick a Rumble video and pattern, click "Analyze" | Analysis runs immediately — no auth required |
| 3 | Click **YouTube** in the nav bar | **Subscription modal** appears |
| 4 | Click "Subscribe $7/month" | Redirected to `/register` |
| 5 | Enter your **First Name** only | Account created with `subscription_status: free` |
| 6 | Click "Confirm $7/month" (mock PayPal) | Subscription activated (30 days), redirected to YouTube analysis |
| 7 | Paste a YouTube URL, pick a pattern, press Enter | Analysis runs, result appears in the AnalysisRunner |

> On subsequent visits, log in via **User ID number** + **First Name** to access YouTube.

---

## Quick Reference (after everything is set up)

```bash
# Terminal 1 — Backend (Postgres must already be up: docker compose up -d db)
cd /home/cowboy/000/cve-marina-1/backend
source .venv/bin/activate && ./run.sh

# Terminal 2 — Frontend
cd /home/cowboy/000/cve-marina-1/frontend && npm run dev
```

Deploying instead of running locally? See [DEPLOY.md](DEPLOY.md).

---

## Environment Variables Reference

Every variable is documented with a commented example in [`.env.example`](.env.example); nothing
needs a `.env` for local development.

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://marina:marina@localhost:5432/marina` | Postgres connection string; scheme and libpq-only params are normalized on read |
| `DATABASE_SSL` | `auto` | `auto` \| `require` \| `disable` |
| `CORS_ORIGINS` | the two localhost:5174 origins | Comma-separated frontend origins. Set to the Netlify URL in production |
| `VITE_API_BASE` | `http://localhost:8000/api` | Frontend API base — inlined at build time, so a change needs a rebuild |
| `FABRIC_MODEL` | `deepseek/deepseek-v4-flash` | LLM model for Fabric analysis |
| `FABRIC_VENDOR` | `OpenRouter` | Vendor flag passed to Fabric |
| `FABRIC_TIMEOUT` | `600` | Per-attempt timeout (seconds) |
| `TRANSCRIPTION_MODEL` | `openai/gpt-audio-mini` | Model for audio transcription |
| `TRANSCRIPTION_CHUNK_SECONDS` | `600` | Audio chunk duration (10 min) |
| `RUMBLE_CHANNEL` | `MarinaJacobi` | Only allow Rumble videos from this channel |
| `JWT_SECRET` | Auto-generated (`backend/.jwt_secret`) | HMAC key for JWT token signing. **The environment wins over the file.** Required in production |
| `JWT_EXPIRE_MINUTES` | `1440` (24 hours) | JWT token lifetime |
| `OPENROUTER_API_KEY` | from `~/.config/fabric/.env` | Checked in the environment first, then that file |
| `MARINA_TMP_DIR` | `/tmp/marina` | Audio scratch space, wiped at boot |
| `RUMBLE_MAX_DOWNLOAD_MB` | `1500` | Ceiling on the one Rumble path that still writes media to disk |

---

## Verifying Everything Works

### Database and schema
```bash
docker compose ps                      # db is "healthy"
alembic current                        # shows the applied revision
alembic check                          # "No new upgrade operations detected" — models match the migration
```

### Backend health check
```bash
curl http://localhost:8000/health
# → {"status":"ok"}
```

### Register a test user (full name + email + password)
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"full_name":"Test User","email":"Test@Example.com","password":"hunter2hunter2"}'
# → {"access_token":"...","token_type":"bearer","user":{"display_id":1,"first_name":"Test","full_name":"Test User","email":"test@example.com","subscription_status":"free","trial_uses_remaining":33,...}}
# Email is normalized to lowercase. password_hash is never returned. Password rules: 8+ chars, 72 bytes max.
```

### Activation (mock PayPal payment)
```bash
TOKEN="<access_token from above>"
curl -X POST http://localhost:8000/api/payments/mock-subscribe \
  -H "Authorization: Bearer $TOKEN"
# → {"success":true,"subscription_status":"active",...}
```

### Login (email + password)
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"hunter2hunter2"}'
# → {"access_token":"...","token_type":"bearer","user":{...}}
# A wrong password and a nonexistent email return the SAME 401 message — the endpoint
# must not be usable to discover which emails have accounts.
```

### YouTube analysis (requires auth + a live trial or subscription)
```bash
curl -X POST http://localhost:8000/api/youtube/analyze \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"video_url":"https://www.youtube.com/watch?v=dQw4w9WgXcQ","pattern":"summarize"}'
# → {"job_id":"...","status":"pending","trial_uses_remaining":32}
# A duplicate (same URL + pattern) returns the existing job_id and does NOT decrement.
# A failed analysis refunds the use. At 0 remaining → 402 {"detail":{"code":"trial_exhausted"}}.
```

### Rumble analysis (public — no token needed!)
```bash
curl -X POST http://localhost:8000/api/rumble/analyze \
  -H "Content-Type: application/json" \
  -d '{"video_url":"https://rumble.com/v12345-example","pattern":"summarize"}'
# → {"job_id":"...","status":"pending"}
```

### History (public — no token needed)
```bash
curl http://localhost:8000/api/history
# → {"jobs":[...],"total":...}
```

### Frontend
Open `http://localhost:5174` — you land on the free Rumble analysis page. The YouTube tab shows a subscription modal prompting registration/payment.