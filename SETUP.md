# Full Startup Guide — Marina's Wisdom

**Freemium Model:** Rumble (Marina Jacobi) analysis is **free** — no signup required. YouTube analysis requires a **$7/month subscription** via mock PayPal payment system.

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
- First run auto-generates `.jwt_secret` (JWT signing key) at the repo root.

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

**The frontend starts on `http://localhost:5173`.**

---

## 3. User Flow

| Step | Action | Result |
|------|--------|--------|
| 1 | Open `http://localhost:5173` | Redirected to **Rumble Analysis** page (`/analysis/rumble`) — **free, no login needed** |
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
| `JWT_SECRET` | Auto-generated (`.jwt_secret`) | HMAC key for JWT token signing |
| `JWT_EXPIRE_MINUTES` | `1440` (24 hours) | JWT token lifetime |

---

## Verifying Everything Works

### Backend health check
```bash
curl http://localhost:8000/health
# → {"status":"ok"}
```

### Register a test user (first name only — no email, no password!)
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"first_name":"Test"}'
# → {"access_token":"...","token_type":"bearer","user":{"display_id":1,"first_name":"Test","subscription_status":"free",...}}
```

### Activation (mock PayPal payment)
```bash
TOKEN="<access_token from above>"
curl -X POST http://localhost:8000/api/payments/mock-subscribe \
  -H "Authorization: Bearer $TOKEN"
# → {"success":true,"subscription_status":"active",...}
```

### Login (by display ID + first name)
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"display_id":1,"first_name":"Test"}'
# → {"access_token":"...","token_type":"bearer","user":{...}}
```

### YouTube analysis (requires auth + subscription)
```bash
curl -X POST http://localhost:8000/api/youtube/analyze \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"video_url":"https://www.youtube.com/watch?v=dQw4w9WgXcQ","pattern":"summarize"}'
# → {"job_id":"...","status":"pending"}
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
Open `http://localhost:5173` — you land on the free Rumble analysis page. The YouTube tab shows a subscription modal prompting registration/payment.