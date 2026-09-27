# Last Session Summary — Freemium Auth Model

**Date:** 2026-09-26 (session start)
**Branch:** `main` (commit `4642c39`)

---

## What Was Done

### Core Change: Freemium Authentication Model

The app was converted from "everything requires JWT auth" to a **freemium two-tier system**:

| Feature | Auth Required | Cost |
|---------|--------------|------|
| Rumble analysis | **None** — fully public | Free |
| YouTube analysis | JWT + active subscription | $7/month |
| History | **None** — fully public | Free |
| Register/Login | Public | Free |

### Backend Changes

**New files:**
- `backend/auth/__init__.py`, `backend/auth/router.py` — `/api/auth/register` (first_name only), `/api/auth/login` (display_id + first_name), `GET /api/auth/me`
- `backend/auth/dependencies.py` — `get_current_user` (optional → User|None) + `require_subscriber` (raises 401/402)
- `backend/payments/__init__.py`, `backend/payments/router.py` — `POST /api/payments/mock-subscribe` (mock PayPal, activates 30-day subscription)
- `backend/services/auth_service.py` — JWT (HS256), user CRUD, `_next_display_id` auto-increment, subscription management
- `backend/schemas.py` — `RegisterRequest`, `LoginRequest`, `TokenResponse`, `UserResponse`

**Modified files (key changes):**
- `backend/models.py` — User model: removed `username`, `email`, `password_hash`. Added `display_id` (Integer, unique), `first_name` (String), `subscription_status` (free/active/expired), `subscription_expires_at` (DateTime). AnalysisJob: removed `user_id`, added `analyst_name` + `analyst_display_id`
- `backend/database.py` — Users table migration + analyst columns migration
- `backend/youtube/router.py` — All endpoints use `require_subscriber` (auth + active subscription needed)
- `backend/rumble/router.py` — All endpoints are **public** (no auth deps)
- `backend/rumble/channel_router.py` — Public (no auth dep)
- `backend/history/router.py` — All endpoints public (no auth deps)
- `backend/youtube/db_helpers.py`, `backend/rumble/db_helpers.py` — Removed `user_id` params, added `analyst_name`/`analyst_display_id` support
- `backend/youtube/orchestrator.py`, `backend/rumble/orchestrator.py` — Accept `analyst_name` + `analyst_display_id` params (defaults "Anonymous"/None)
- `backend/requirements.txt` — Removed `passlib[bcrypt]` and `bcrypt`. Kept `python-jose[cryptography]`
- `backend/main.py` — Added payments router import

**Bugs fixed:**
1. `_next_display_id()` — catches table-not-found exception on first registration, returns 1
2. `is_subscription_active()` — strips tzinfo from `datetime.now(timezone.utc)` via `.replace(tzinfo=None)` before comparing with naive SQLite datetime

### Frontend Changes

**New files:**
- `frontend/src/context/AuthContext.jsx` — AuthProvider: login (displayId + firstName), register (firstName), mockSubscribe, logout. Tracks `isAuthenticated` + `isSubscribed`
- `frontend/src/auth/LoginPage.jsx` — Login form: User ID number + First Name
- `frontend/src/auth/RegisterPage.jsx` — 3-step flow: name → mock PayPal payment → success + auto-redirect
- `frontend/src/auth/ProtectedRoute.jsx` — Auth gate, redirects to `/login`
- `frontend/src/auth/SubscriptionGuard.jsx` — YouTube gate, shows SubscriptionModal if not subscribed
- `frontend/src/components/SubscriptionModal.jsx` — Modal: subscribe ($7/month) or login, inline mock PayPal for logged-in users

**Modified files:**
- `frontend/src/App.jsx` — Default route: `/` → `/analysis/rumble`. YouTube: wrapped in SubscriptionGuard + ProtectedRoute
- `frontend/src/components/Layout.jsx` — Logo links to `/rumble`. Shows `first_name (#display_id)` when authenticated, "Subscribe" link when not
- `frontend/src/history/HistoryPage.jsx` — Shows `Analyst: name (#id)` in collapsed and expanded views, analyst_name added to search haystack
- `frontend/src/api/client.js` — Updated request() helper

### Docs Updated
- `AGENTS.md` — Full rewrite for freemium model (auth sections, routing table, flow details)
- `SETUP.md` — Full rewrite (freemium setup steps, verification commands, env vars)
- `last-session-summary.md` — This file

---

## Current Status

### ✅ Working (Verified by Tests)

| Test | Result |
|------|--------|
| Backend starts via `run.sh` | ✅ Clean startup (port 8000) |
| Health check | ✅ 200 OK |
| Register (first_name only) | ✅ Returns JWT + UserResponse with display_id #1 |
| Login (display_id + first_name) | ✅ Returns JWT |
| Auth/me | ✅ Returns user info |
| Mock subscribe | ✅ Status changes to "active", 30-day expiry |
| Auth/me without token | ✅ 401 |
| YouTube without auth | ✅ 401 |
| YouTube with auth + subscription | ✅ 200 (proxies to orchestrator) |
| Rumble without auth | ✅ Public (404 for nonexistent job) |
| History without auth | ✅ Public (200, empty array) |
| Patterns without auth | ✅ Public (200, 71 patterns) |
| Second user display_id | ✅ Auto-increments to #2 |
| Frontend build | ✅ Clean, no errors (2235 modules) |

### Known Issues

- **No user isolation** — all history is shared. This is by design (requested feature)
- **Mock PayPal** — no real payment processing. Subscription activation is instant via API
- **No subscription renewal** — 30-day expiry with no auto-renewal
- **TestClient needed for API tests** — raw `AsyncClient + ASGITransport` doesn't trigger the FastAPI lifespan; use `starlette.testclient.TestClient` instead
- **OpenRouter API key** loaded from `~/.config/fabric/.env` at runtime

### Git State
- **Last commit:** `4642c39` — "Implement freemium auth model: free Rumble access, $7/month YouTube subscription"
- **Working tree:** clean (all files committed)
- **48 files changed,** 1,798 insertions, 350 deletions

---

## Quick Start for Next Session

```bash
# Terminal 1 — Backend
cd /home/cowboy/000/cve-marina-1/backend
source .venv/bin/activate && ./run.sh

# Terminal 2 — Frontend
cd /home/cowboy/000/cve-marina-1/frontend && npm run dev
```

Open http://localhost:5173 → lands on free Rumble analysis. Click YouTube → subscription modal → register (first name only) → mock PayPal → YouTube access.

**Key files to review:**
- [AGENTS.md](AGENTS.md) — Full project reference (updated for freemium)
- [SETUP.md](SETUP.md) — Quick start and verification
- `backend/services/auth_service.py` — Auth logic
- `backend/auth/dependencies.py` — get_current_user + require_subscriber
- `frontend/src/context/AuthContext.jsx` — Frontend auth state
- `frontend/src/auth/RegisterPage.jsx` — 3-step registration flow
- `frontend/src/components/SubscriptionModal.jsx` — YouTube gate modal

**Endpoints to verify quickly:**
```bash
curl http://localhost:8000/health                          # health
curl -X POST http://localhost:8000/api/auth/register -H 'Content-Type: application/json' -d '{"first_name":"Test"}'  # register
curl -X POST http://localhost:8000/api/payments/mock-subscribe -H "Authorization: Bearer $TOKEN"  # subscribe
curl http://localhost:8000/api/history                       # public history
curl http://localhost:8000/api/patterns                      # public patterns
curl -X POST http://localhost:8000/api/rumble/analyze -H 'Content-Type: application/json' -d '{"video_url":"test","pattern":"summarize"}'  # public rumble
```