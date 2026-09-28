# Full Startup Guide — Marina's Wisdom

**Freemium Model:** Rumble (Marina Jacobi) analysis is **free** — no signup required, and its history is shared with everyone. YouTube analysis requires an account (full name + email + password) and either a **33-use free trial** or a **$7/month subscription** via mock PayPal. YouTube history is private to each account.

> **There is no password reset.** Nothing is emailed — a forgotten password permanently costs the account and its private YouTube history. The signup and login pages say so.

---

## Prerequisites (one-time setup outside the repo)

```bash
# Python 3.12+
python3 --version

# Node.js 20+
node --version

# Fabric CLI on PATH
fabric --version

# OpenRouter API key in fabric config
echo "OPENROUTER_API_KEY=sk-or-v1-..." > ~/.config/fabric/.env

# ffmpeg + ffprobe (required for Rumble audio transcription)
ffmpeg -version

# yt-dlp (required for YouTube metadata)
yt-dlp --version
```

---

## 1. Backend Setup & Start

```bash
# Navigate to repo root
cd /home/cowboy/000/cve-marina-1

# Create virtual environment (one-time)
cd backend
python3 -m venv .venv

# Activate it
source .venv/bin/activate

# Install Python dependencies (one-time)
pip install -r requirements.txt

# Start the backend server (with --reload for auto-restart on changes)
./run.sh
```

**The backend starts on `http://0.0.0.0:8000`.**

- First run auto-creates `marina_jacobi.db` (SQLite database) at the repo root.
- Auto-generates **`backend/.jwt_secret`** (JWT signing key) the first time a token is signed — not at startup, and not at the repo root. It is **gitignored**; never commit it.

---

## 2. Frontend Setup & Start (separate terminal)

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

## 3. User Flow

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
# Terminal 1 — Backend
cd /home/cowboy/000/cve-marina-1/backend
source .venv/bin/activate && ./run.sh

# Terminal 2 — Frontend
cd /home/cowboy/000/cve-marina-1/frontend && npm run dev
```

---

## Environment Variables Reference

| Variable | Default | Description |
|---|---|---|
| `VITE_API_BASE` | `http://localhost:8000/api` | Frontend API proxy target |
| `FABRIC_MODEL` | `deepseek/deepseek-v4-flash` | LLM model for Fabric analysis |
| `FABRIC_VENDOR` | `OpenRouter` | Vendor flag passed to Fabric |
| `FABRIC_TIMEOUT` | `600` | Per-attempt timeout (seconds) |
| `TRANSCRIPTION_MODEL` | `openai/gpt-audio-mini` | Model for audio transcription |
| `TRANSCRIPTION_CHUNK_SECONDS` | `600` | Audio chunk duration (10 min) |
| `RUMBLE_CHANNEL` | `MarinaJacobi` | Only allow Rumble videos from this channel |
| `JWT_SECRET` | Auto-generated (`backend/.jwt_secret`) | HMAC key for JWT token signing |
| `JWT_EXPIRE_MINUTES` | `1440` (24 hours) | JWT token lifetime |

---

## Verifying Everything Works

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