# Deploying Marina's Wisdom

Backend on **Render** (Docker, always-on, managed Postgres), frontend on **Netlify** (static SPA).

Read this before the first deploy: **the order is circular and needs two backend deploys.** The
frontend needs the backend's URL to build against; the backend needs the frontend's URL for CORS.
So the first backend deploy ships with a placeholder CORS value that gets corrected at the end.

```
 1. Push the repo to GitHub
 2. Render  -> Blueprint -> deploys Postgres + backend (CORS still a placeholder)
 3. Netlify -> deploy the site, VITE_API_BASE = the Render URL
 4. Render  -> copy the Netlify URL into CORS_ORIGINS, redeploy
```

---

## 0. What has to be true before you start

| Thing | Why |
|---|---|
| A GitHub repo containing this code | Render and Netlify both build from git. Manual deploys still pull from a branch. |
| An OpenRouter API key with credit | Every analysis spends real money on it. It is **not** in the repo and must never be. |
| A Render account | The payment method matters — the service is `plan: starter`, i.e. paid and always-on. |
| A Netlify account | Free tier is fine; the frontend is a static bundle. |

**Do not put secrets in the repo.** `.env` and `backend/.jwt_secret` are gitignored, and
`.dockerignore` excludes them from the image as well. If either ever lands in a commit, rotate it —
history is forever.

---

## 1. Push to GitHub

```bash
git remote add origin git@github.com:<you>/<repo>.git   # skip if already set
git push -u origin main
```

Render builds from `main` (`branch: main` in `render.yaml`). Deploying from a feature branch means
editing that field in the dashboard, or merging first.

---

## 2. Backend — Render

**New → Blueprint → point at the repo.** Render reads `render.yaml` and proposes a Postgres
instance plus a web service. Accept it and let it build.

What the blueprint sets, and why:

- **`runtime: docker`** — the pipeline shells out to `fabric`, `ffmpeg` and `yt-dlp`, none of which
  exist on a stock Python runtime. The Dockerfile installs all three.
- **`preDeployCommand: alembic upgrade head`** — runs once in the built image *before* the new
  instance takes traffic, so it cannot race itself across instances the way a boot-time migration
  could. If it fails, the deploy fails. That is intentional: a backend running against an
  unmigrated schema is worse than one that did not start.
- **`plan: starter`** — a free instance spins down after inactivity. Analyses take minutes to hours
  and the job registry lives in process memory, so a spin-down would kill every in-flight job.
- **`autoDeploy: false`** — deploys are manual. See *Deploying again* below.
- **`healthCheckPath: /health`** — Render withholds traffic until this answers.

### Environment variables

| Key | Value | Notes |
|---|---|---|
| `DATABASE_URL` | from `marina-db` | The **internal** connection string: same private network, no TLS. `database.py` normalizes the scheme and strips libpq-only params, so an external URL would also work. |
| `JWT_SECRET` | `generateValue: true` | Render generates and holds it. **Required in production** — the app refuses to boot on Render without it. |
| `OPENROUTER_API_KEY` | `sync: false` | Render prompts for it in the dashboard. Never stored in git. |
| `CORS_ORIGINS` | `https://REPLACE-ME.netlify.app` | Fix this in step 4. |
| `APP_ENV` | `production` | |
| `FABRIC_MODEL` / `FABRIC_VENDOR` | `deepseek/deepseek-v4-flash` / `OpenRouter` | Model is hard-wired; there is no UI selector. |
| `TIKTOKEN_CACHE_DIR` | `/opt/tiktoken` | Baked into the image; repeated so a rebuild is not needed to change it. |
| `MARINA_TMP_DIR` | `/tmp/marina` | Audio scratch space, wiped at boot. |
| `RUMBLE_MAX_DOWNLOAD_MB` | `1500` | Ceiling on the one path that still writes media to disk. |

### The circular part

`CORS_ORIGINS` cannot be correct yet — the Netlify site does not exist. Deploy with the placeholder
and accept that the frontend will not be able to call the API until step 4.

**Do not set `CORS_ORIGINS=*` "temporarily."** It is not needed for this to work, and a wildcard
left in place on a service that spends money per request is how a weekend gets ruined.

### Verify the backend

```bash
curl -s https://<service>.onrender.com/health          # {"status":"ok",...}
curl -s https://<service>.onrender.com/api/patterns | jq '.patterns | length'   # 59
```

**59 is the number to check.** It proves fabric resolved its vendored patterns from `$HOME/.config/fabric`.
If this returns 0, the image's `HOME` is wrong — fabric ignores `XDG_CONFIG_HOME` and hardcodes
`$HOME/.config/fabric`, and when it cannot find the directory it exits 0 with no output rather than
erroring. (The same trap applies to `$HOME/.config/fabric/.env`, which fabric requires to *exist*
even when empty; the Dockerfile creates it.)

Then run one real analysis from the deployed frontend before considering the backend done. A
read-only check cannot catch a missing OpenRouter key or a blocked egress path.

---

## 3. Frontend — Netlify

**Add new site → Import from GitHub → pick the repo.** `netlify.toml` supplies `base = "frontend"`,
`publish = "dist"`, `command = "npm run build"` and `NODE_VERSION = 22.12.0` (Vite 8 requires
`^20.19 || >=22.12`).

Set **one** environment variable, in the Netlify UI (**Site configuration → Environment variables**):

```
VITE_API_BASE = https://<service>.onrender.com/api
```

Note the `/api` suffix, and that this is **not** in `netlify.toml` — Vite inlines it at build time,
so it must exist *before* `npm run build` runs. Changing it later requires a redeploy; a rebuild of
the same commit is enough.

The `[[redirects]]` catch-all (`/*` → `/index.html`, status **200**) is what makes deep links work.
The app uses `BrowserRouter` and `client.js` redirects to `/login` on a 401, so without it a hard
refresh on any route 404s. It is a rewrite, not a redirect — the URL has to stay in the address bar.

---

## 4. Close the loop

1. Copy the Netlify site URL (e.g. `https://marina-wisdom.netlify.app`).
2. Render → `marina-backend` → Environment → set `CORS_ORIGINS` to exactly that origin.
3. **Manual Deploy → Deploy latest commit.**

Scheme, host and port must match the browser's origin character for character; `http` vs `https` and
a trailing slash are both enough to fail. `allow_credentials` is `false` (auth is a `Bearer` header
from `localStorage`, never a cookie), so a wildcard would be technically legal here — it is still
the wrong default for a service with a spend attached.

Then, in the browser: open the deployed site, run one free Rumble analysis, register an account, run
one YouTube analysis, and confirm the trial counter drops from 33 to 32. That exercises CORS, the
database, the quota transaction and both pipelines in one pass.

---

## Deploying again

Because `autoDeploy: false`, pushing to `main` does **not** deploy. That is deliberate: **every
restart SIGKILLs in-flight analyses.** A three-hour Rumble job dies mid-transcription, and while
the boot sweeper refunds the trial use it consumed, the work is gone.

So: push freely, and press **Manual Deploy** when nothing is running.

Migrations ride along automatically — `preDeployCommand` runs `alembic upgrade head` before the new
instance takes traffic. If a migration fails, the old instance keeps serving and the deploy stops.
That is the correct outcome; fix the migration rather than deleting it.

---

## Local development

Same code, same migrations, no cloud:

```bash
docker compose up -d db                  # Postgres 17, matching Render's major version
source backend/.venv/bin/activate
alembic upgrade head                     # Alembic owns the schema; the app never creates tables
cd backend && ./run.sh                   # http://localhost:8000
cd frontend && npm run dev               # http://localhost:5174
```

No `.env` is required — the defaults in the code match `docker-compose.yml`, and `JWT_SECRET` falls
back to a generated `backend/.jwt_secret`. See `.env.example` for every variable.

**Never run `alembic downgrade` against production.** It has no confirmation prompt.

---

## Things that will bite

- **`alembic check` after any `models.py` edit.** Without it a model change ships with no migration
  and the mismatch surfaces only when a query hits a missing column — in production. There is no CI
  running this; it is a manual step, so it is a step that gets forgotten.
- **One worker, one instance.** The job registry is per-process; a job started on one worker is
  invisible to another. `main.py` refuses to boot if `WEB_CONCURRENCY`/`WORKERS` > 1 while the boot
  sweeper is enabled. Do not "fix" a slow deploy by adding workers — scaling out needs a
  Postgres-backed queue, which does not exist yet.
- **Render's filesystem is ephemeral.** Anything written outside Postgres is gone on the next
  deploy, restart or crash. This is why the Rumble pipeline streams video through ffmpeg instead of
  downloading it, and why the scratch directory is wiped at boot.
- **`OPENROUTER_API_KEY` may be shadowed by the host environment locally.** Fabric gives real env
  vars priority over `~/.config/fabric/.env`, so a stale placeholder exported into the systemd user
  environment makes every analysis fail with `401 Missing Authentication header`. Fix with
  `systemctl --user unset-environment OPENROUTER_API_KEY`, or start the backend with
  `env -u OPENROUTER_API_KEY`.
- **The trial is abusable and login is brute-forceable.** Signup grants 33 real OpenRouter calls
  with no email verification and there is no rate limiting anywhere, so a disposable-email script
  can spend the account owner's balance without bound. Acceptable for local/self-hosted; both need
  addressing before this faces the open internet with a funded key.
