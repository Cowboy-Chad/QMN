# Marina's Wisdom

OSINT analysis app leveraging [Fabric](https://github.com/danielmiessler/fabric) AI patterns for automated analysis of multimedia content.

## Architecture

```
React (Vite)  ←→  FastAPI (Python)  ←→  fabric CLI  ←→  OpenRouter API
                                    ↕
                            PostgreSQL (asyncpg, Alembic)
```

Deployed as a Render backend (Docker) plus a Netlify frontend — see [DEPLOY.md](DEPLOY.md).

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 22.12+
- [Fabric CLI](https://github.com/danielmiessler/fabric) installed and configured
- OpenRouter API key (environment variable, or `~/.config/fabric/.env`)
- Docker (or podman) for the local Postgres

### Database

```bash
docker compose up -d db          # Postgres 17; the default DATABASE_URL points here
source backend/.venv/bin/activate
alembic upgrade head             # Alembic owns the schema — the app never creates tables
```

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
./run.sh
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5174 in your browser.

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/auth/register` | Public | Create an account — `{full_name, email, password}` |
| POST | `/api/auth/login` | Public | `{email, password}` → token |
| GET | `/api/auth/me` | Optional | Current account |
| POST | `/api/payments/mock-subscribe` | Required | Mock PayPal — 30-day subscription |
| POST | `/api/youtube/analyze` | Trial or subscriber | Start a YouTube analysis |
| GET | `/api/youtube/jobs/{id}` | Trial or subscriber | Poll your own YouTube job |
| POST | `/api/rumble/analyze` | Public | Start a Rumble analysis |
| GET | `/api/channel/videos` | Public | Cached Rumble channel video list |
| GET | `/api/jobs/{id}` | Optional | Poll a job (your own YouTube, or any Rumble job) |
| GET | `/api/history` | Optional | Shared Rumble results + your own YouTube results |
| GET | `/api/patterns` | Public | List Fabric patterns |
| GET | `/api/health` | Public | Health check |

`/api/analyze` and `/api/analyze/file` no longer exist — see "Removed" below.

## Features

- **Rumble**: Download audio → transcribe via OpenRouter → analyze. **Free, no account.** One shared history for everyone.
- **YouTube**: Fetch transcript → analyze with Fabric pattern. Requires an account and either a **33-use free trial** or a **$7/month subscription**. History is **private per account**.
- **History**: Browse past results, copy results and transcripts, open the original video.

### Accounts

Signup is a full name, an email and a password. There is **no email verification and no password
reset** — nothing is emailed, so a forgotten password means losing the account and its private
YouTube history for good. The signup form says this plainly.

### Removed

Web scraping (`/api/analyze?source=web`), file upload (`/api/analyze/file`), the in-app model
selector, and passwordless login (first name + display ID).