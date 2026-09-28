# Last Session Summary — Password Accounts + Free Trial + Per-User History

**Date:** 2026-09-27 → 2026-09-28
**Branch:** `trial-accounts-and-private-history` — one commit, the tip of this branch
(branched from `main` at `2e4a4ce`; run `git log --oneline -1` for its hash)

> **This work is deliberately on a branch, not on `main`.** Asked about merging, the user said no
> — leave it here and do **not** merge or move it unprompted. If they later want it on `main`:
> `git checkout main && git merge --ff-only trial-accounts-and-private-history` (fast-forwards
> cleanly; `main` has not moved).

---

## TL;DR for the next session

The whole feature is **implemented, verified, and committed** as the single commit on
`trial-accounts-and-private-history`. The working tree is clean, and `main` is untouched by design
(see the note above).

Any servers that were running will be gone after a full shutdown. Start both, with the env caveat
below.

```bash
# Terminal 1 — backend
cd /home/cowboy/000/cve-marina-1/backend
source .venv/bin/activate
env -u OPENROUTER_API_KEY ./run.sh     # <-- the env -u matters, see "Traps"

# Terminal 2 — frontend
cd /home/cowboy/000/cve-marina-1/frontend && npm run dev
```

Open http://localhost:5174.

---

## What changed

The app went from *passwordless freemium* to *real accounts with a usage-metered free trial*.

| | Before | After |
|---|---|---|
| YouTube signup | first name only | **full name + email + password** |
| YouTube access | $7/month subscription only | **33-use free trial** *or* $7/month |
| YouTube history | shared with everyone | **private per account** |
| Rumble | free, public, shared history | **unchanged** |
| Login | display ID + first name | **email + password** |

Both tiers share **one** signup. The account is created first; the user then chooses "start the
free trial" or "subscribe $7/month". Trial vs paid is a *state of the account*, not a separate
signup path.

### Locked decisions (agreed with the user)

| Decision | Choice |
|---|---|
| What burns a trial use | Only a genuinely new job. Duplicate hits are free. Failures refund. |
| Cross-user dedup | **Fully isolated** — no reuse between users, even for the same video+pattern |
| Legacy accounts | **Database was reset.** No migration, no backfill, no dual login |
| Full name | New `full_name` column; `first_name` derived from its first token |
| Forgotten password | **Accepted lockout**, documented in the UI. There is no email sending |
| Adjacent bugs | The four found during exploration were fixed in this change |

### The four adjacent bugs fixed

1. **`_migrate()` was dead code** — `backend/database.py` defined it but commit `4642c39` had
   deleted the `await conn.run_sync(_migrate)` call, so it never ran. Restored.
2. **`/register` early-exit bounced the wrong users** — it only redirected *subscribed* users, so a
   logged-in free user could create a duplicate account. Now any authenticated user is redirected.
3. **Raw JSON errors on the page** — `subscription_required` 402s rendered as
   `{"detail":{...}}` verbatim. `client.js` now parses structured errors.
4. **`SubscriptionGuard` returned `null`** — dismissing the modal left a blank page with no nav.
   It now renders a locked panel *behind* the modal.

### Files

**New (added in this change):**
- `backend/services/password_service.py` — bcrypt hash/verify, 72-byte guard
- `backend/services/trial_service.py` — atomic `decrement_trial_use`, idempotent `refund_trial_use`

**Deleted:** `backend/.jwt_secret` — untracked and gitignored now (it had been committed; see Traps)

**Heavily modified:** `backend/{models,schemas,database,main}.py`,
`backend/auth/{router,dependencies}.py`, `backend/services/auth_service.py`,
`backend/youtube/{router,orchestrator,db_helpers}.py`, `backend/history/{router,db_helpers}.py`,
`frontend/src/api/client.js`, `frontend/src/context/AuthContext.jsx`,
`frontend/src/auth/{LoginPage,RegisterPage,SubscriptionGuard}.jsx`,
`frontend/src/components/{Layout,SubscriptionModal}.jsx`,
`frontend/src/youtube/YouTubeAnalysisPage.jsx`, `frontend/src/history/HistoryPage.jsx`,
`frontend/src/App.jsx`, `.gitignore`

**Docs updated:** `AGENTS.md`, `SETUP.md`, and `README.md`. README was **beyond the approved
plan's scope** — it was stale from before the *previous* freemium rewrite (still documented
`/api/analyze?source=web` and `/api/analyze/file` as live endpoints), so it was corrected too.

**`backend/rumble/*` received zero edits** — deliberate. Rumble rows have `user_id IS NULL`,
match `source != 'youtube'`, and short-circuit before every ownership test.

**The approved plan is at** `/home/cowboy/.claude/plans/federated-cooking-moth.md` (24 KB, has the
full rationale for every decision below).

---

## How the important mechanisms work

Understanding these four things is most of the onboarding.

### 1. The trial quota is enforced by one atomic UPDATE

`create_job` in `backend/youtube/db_helpers.py` opens **one** session, and inside it:
`UPDATE users SET trial_uses_remaining = trial_uses_remaining - 1 WHERE id=? AND trial_uses_remaining > 0`,
then inserts the job row, then commits **once**. That single transaction is the serialization
point — two tabs both seeing "1 left" cannot both succeed. `rowcount == 0` means exhausted.

`refund_trial_use` is idempotent by **claiming the job's `trial_use_consumed` flag** before
crediting, so the pipeline's failure handler and the boot sweeper in `main.py` cannot both refund.

**The counter stores *remaining*, not *consumed*.** `NULL` means "no trial ever granted"; `0` means
"used up". That distinction is load-bearing — it is what lets the UI tell an *exhausted*
trial user ("subscribe to keep going") from an account that never had a trial
("subscription required").

### 2. Order is dedup first, then quota

A duplicate hit is free and works even at 0 uses left, so a user who has spent their trial can
still re-open a result they already paid for.

This is why **`require_youtube_access` deliberately admits a 0-use account.** It decides *who gets
in*, not *whether they can spend*. An early version rejected at 0 in the dependency and was a real
bug: it locked users out of their own results. The 402 `trial_exhausted` comes from the handler
when the atomic consume fails.

### 3. Refunds need two handlers

`asyncio.CancelledError` inherits from `BaseException`, so it **skips `except Exception`** and needs
its own clause. In the `except Exception` path the refund happens **before** the status write, so a
failing `update_job_status` cannot lose the credit. A hard kill bypasses both — which is why
`main.py`'s boot sweeper refunds the jobs it marks failed at startup.

### 4. Isolation is a 404, never a 403

A 403 would confirm that a guessed job id exists. Ownership is **folded into the query** rather
than checked after the fetch. `user_id == uid` is never true for a NULL row, so unowned (Rumble)
rows stay invisible in YouTube-scoped queries.

Scoping the *dedup lookups* was required for correctness, not just cost: unscoped,
`find_existing_job_id` would hand user B **user A's** job id, and B's own ownership check would then
404 on the very job the server just told them to poll — so B would never get the analysis the
isolation decision promises.

---

## Verification (all passed)

Run against the live servers, behaviorally — not by reading code.

| Suite | Result |
|---|---|
| Trial quota + isolation | **41/41** |
| Subscriber path (unlimited, trial untouched) | **6/6** |
| Boot-sweeper refund on restart | **4/4** |
| Refund idempotency (2nd refund returns `False`, counter unchanged) | **1/1** |
| Auth contract re-check at end of session | **4/4** |

Specifically confirmed: signup returns `trial_uses_remaining: 33` with the email lowercased, the
full name stored, and **no `password_hash` in any response**; duplicate email in different case →
409; 7-char password → 400; >72-byte password → 400; wrong password and unknown email return the
**same** 401 message; analyze 33 → 32; a failed analysis refunds 32 → **33**; a second account gets
a **different** job id for the same video and a 404 on the first account's job; logged-out
`?source=youtube` returns `[]`; a subscriber forced to 0 trial uses still analyzes and is not
charged. JWT rotation genuinely invalidates previously-issued tokens.

`npm run lint` → warnings only, all of classes already present in `JobContext`/`PatternSelector`/
`AnalysisRunner`/`VideoPicker`. `npm run build` → succeeds, 2235 modules.

> Two "failures" in the final re-check were **bugs in my test script, not the app**: a login
> assertion read a stale variable left over from the preceding wrong-password call, and I asserted
> a refund lands on 32 when a single failed job from 33 must restore 33. Both re-verified clean.

---

## Traps that will bite you

**1. `OPENROUTER_API_KEY` shadowing — the one that already broke a real run.**
Fabric gives real environment variables priority over `~/.config/fabric/.env`. A placeholder
exported into the systemd user environment makes *every* analysis fail with
`401 Unauthorized {"message":"Missing Authentication header"}`. Fix:
`systemctl --user unset-environment OPENROUTER_API_KEY` (permanent), or start the backend with
`env -u OPENROUTER_API_KEY` (per-session). **Until that env var is cleared, always start with
`env -u`.**

**2. `pkill -f "backend.main:app"` kills your own shell.** The pattern matches the invoking shell's
command line, so you get exit code 144. The uvicorn process does die — the shell dies with it.

**3. `.jwt_secret` does not regenerate after deletion while the server is running.** `_JWT_SECRET`
is a module-level global cached on first read, so the live process keeps using the old secret and
never rewrites the file. **Restart the backend** to force regeneration.

**4. Backend has no `--reload`.** It was started without it, so backend edits need a manual
restart. The frontend does have HMR.

**5. Two `db_helpers.py` files that used to be identical no longer are.** YouTube's `create_job` now
takes extra params and returns a tuple. Rumble's copy is frozen — do not "resync" them.

**6. `backend/.venv` is the real venv.** The repo root also has a stale `.venv`. `run.sh` uses
`backend/.venv`, which is the one with `bcrypt` installed. IDE "module not found" warnings for
`bcrypt` come from the wrong interpreter.

---

## Accepted risks (the user was told and approved)

- **No password reset.** Nothing is emailed; a forgotten password permanently loses the account
  *and* its private history. Stated plainly on both the signup and login pages.
- **The trial is abusable.** Signup grants 33 real OpenRouter calls with no email verification and
  no rate limiting, so a disposable-email script can spend the owner's OpenRouter balance without
  bound. Same missing limiter leaves password login open to online brute force. Both need
  addressing before this faces the internet.
- **Signup does not prove email ownership.** A user can squat someone else's address (they cannot
  take over an *existing* account — the unique index blocks that — but they can hold the address).
- **A systematically failing URL re-charges on each retry**, because failed rows are excluded from
  dedup. Net-neutral (each failure refunds), but the counter visibly dips and recovers.
- **Mid-job token expiry shows "Job not found"** in AnalysisRunner. No redirect loop, since 404
  avoids the 401 branch in `client.js`. Optional follow-up: render "session expired" for a 404 that
  arrives while a token is present.
- **`bcrypt` is used directly, not `passlib`** — passlib is unmaintained and breaks against
  bcrypt 4.x+. Anything over 72 bytes is **rejected, not truncated**, because bcrypt silently
  ignores the excess and two different long passwords would otherwise authenticate the same
  account.

---

## Loose ends

1. **The work is on a branch, not `main`, and that is the user's choice** — see the note at the
   top. Do not merge it unprompted.
2. **`require_subscriber` in `backend/auth/dependencies.py` is now dead code** — no route uses it.
   Kept deliberately as a documented sibling of `require_youtube_access`. Tell the user it can go.
3. **`marina_jacobi.db.bak-2026-09-27`** — the pre-reset database, moved aside rather than deleted
   so the old data stayed recoverable. Verified contents: **2 accounts, 3 Rumble jobs, 3 YouTube
   jobs.** The user was told they can ask for a hard delete. It is now `gitignore`d via
   `*.db.bak*` so it cannot reach history.
4. **The live database contains throwaway test accounts.** As of session end: **13 users**, 15
   YouTube jobs (almost all smoke tests that failed on purpose), 2 Rumble jobs. Worth offering to
   clean up before the user does real work. Note the reset also cleared the Rumble `channel_videos`
   cache, so the **first channel fetch is synchronous again (~20s)** before the hourly refresh
   repopulates it.
5. **`frontend/index.html` title still says "OSINT-1"** — never rebranded. Pre-existing.
6. **No test framework exists.** Every verification this session was ad-hoc curl/Python against a
   running server. If tests are ever wanted, `starlette.testclient.TestClient` is required (raw
   `AsyncClient + ASGITransport` does not trigger the FastAPI lifespan).

---

## Where to look first

- `/home/cowboy/.claude/plans/federated-cooking-moth.md` — the approved plan and full rationale
- [AGENTS.md](AGENTS.md) — fully updated: freemium model, API table, DB schema, Known Quirks
- `backend/services/trial_service.py` — the quota gate (~60 lines, read this first)
- `backend/youtube/db_helpers.py` — `create_job`, where the atomic consume lives
- `backend/auth/dependencies.py` — `require_youtube_access` and why it admits 0-use accounts
- `frontend/src/context/AuthContext.jsx` — `isTrial` / `hasYouTubeAccess` / `applyTrialRemaining`

## Quick smoke test after restart

```bash
curl http://localhost:8000/health

# register → expect trial_uses_remaining: 33, lowercased email, NO password_hash
curl -X POST http://localhost:8000/api/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"full_name":"Test User","email":"Test@Example.com","password":"hunter2hunter2"}'

# login → expect 200; wrong password → 401 with the SAME message as an unknown email
curl -X POST http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"test@example.com","password":"hunter2hunter2"}'

# public Rumble history must never contain a youtube row, logged out or not
curl 'http://localhost:8000/api/history'
# logged out, this must return []
curl 'http://localhost:8000/api/history?source=youtube'
```

Then in the browser: signup → "Start your free trial" → counter reads 33 → run one analysis →
32. Log out, log back in with email + password → still 32 (server-side, not localStorage).
