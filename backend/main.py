import os
import shutil
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from backend.youtube.router import router as youtube_router
from backend.rumble.router import router as rumble_router
from backend.rumble.channel_router import router as channel_router
from backend.history.router import router as history_router
from backend.auth.router import router as auth_router
from backend.payments.router import router as payments_router

SWEEP_STUCK_JOBS_ON_BOOT = os.environ.get("SWEEP_STUCK_JOBS_ON_BOOT", "1") == "1"
STUCK_JOB_MAX_AGE_SECONDS = int(os.environ.get("STUCK_JOB_MAX_AGE_SECONDS", "3600"))
MARINA_TMP_DIR = os.environ.get("MARINA_TMP_DIR", "/tmp/marina")


def _assert_single_process() -> None:
    """The job registry and the boot sweeper are per-process state.

    Each orchestrator keeps `_jobs: dict[job_id, asyncio.Task]` in memory, so a job
    started on one worker is invisible to another — a poll landing on the wrong
    worker finds the DB row but never the task. The boot sweeper compounds it: a
    second worker starting up would fail and refund jobs another worker is running.
    Scaling out needs a Postgres-backed queue with claimed_by/heartbeat_at columns,
    not a bigger --workers value.
    """
    workers = os.environ.get("WEB_CONCURRENCY") or os.environ.get("WORKERS") or "1"
    if SWEEP_STUCK_JOBS_ON_BOOT and workers not in ("", "1"):
        raise RuntimeError(
            f"Refusing to start with {workers} workers while SWEEP_STUCK_JOBS_ON_BOOT is on: "
            "the boot sweeper would fail and refund jobs owned by another worker. "
            "Set SWEEP_STUCK_JOBS_ON_BOOT=0 only after moving job state into the database."
        )


def _clear_temp_dir() -> None:
    """Wipe the Rumble scratch directory at boot.

    The per-job `finally` blocks cannot run when a container is SIGKILLed or
    stopped, which is exactly what happens on every Render deploy. Boot is the one
    moment we know for certain no job from this container is still running, so it
    is the only reliable place to reclaim that disk.
    """
    try:
        shutil.rmtree(MARINA_TMP_DIR, ignore_errors=True)
        os.makedirs(MARINA_TMP_DIR, exist_ok=True)
    except OSError:
        pass  # a read-only /tmp is not worth refusing to boot over


@asynccontextmanager
async def lifespan(app: FastAPI):
    from backend.services.auth_service import assert_jwt_secret_configured

    assert_jwt_secret_configured()
    _assert_single_process()
    _clear_temp_dir()

    # Schema is owned by Alembic. The app never creates tables — if
    # `alembic upgrade head` did not run, the deploy should fail loudly rather than
    # silently materialize a schema that drifts from the migrations.

    if SWEEP_STUCK_JOBS_ON_BOOT:
        # Clean up jobs left pending/running by a previous server instance.
        from backend.database import async_session
        from backend.models import AnalysisJob
        from backend.services.trial_service import refund_trial_use
        from sqlalchemy import select, update

        # Only jobs old enough to be certainly dead. Without the age bound, a
        # second process starting while a job is genuinely running would fail that
        # job and hand back a trial use it never spent.
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=STUCK_JOB_MAX_AGE_SECONDS)
        async with async_session() as session:
            # Capture the ids first: this set is exactly the jobs whose pipeline
            # never reached an ending, so the trial uses they consumed were never
            # refunded by the in-process handler.
            stuck = await session.execute(
                select(AnalysisJob.id).where(
                    AnalysisJob.status.in_(["pending", "running"]),
                    AnalysisJob.updated_at < cutoff,
                )
            )
            stuck_ids = [row[0] for row in stuck.all()]
            if stuck_ids:
                await session.execute(
                    update(AnalysisJob)
                    .where(AnalysisJob.id.in_(stuck_ids))
                    .values(status="failed", error="Server restarted")
                )
                await session.commit()

        # Give back the trial uses those jobs spent. refund_trial_use claims each
        # job's flag before crediting, so a job that already failed normally (and
        # refunded in the pipeline) cannot be refunded twice here.
        for job_id in stuck_ids:
            await refund_trial_use(job_id)

    yield


app = FastAPI(title="Marina's Wisdom", lifespan=lifespan)


@app.get("/health")
async def root_health():
    return {"status": "ok"}


@app.get("/v1/models")
async def openai_compat_models():
    return {"object": "list", "data": []}


# allow_credentials is False on purpose: auth is a Bearer header read from
# localStorage, never a cookie, so nothing needs credentialed CORS. Leaving it True
# would also make a wildcard origin illegal per the CORS spec.
_origins = [
    o.strip()
    for o in os.environ.get(
        "CORS_ORIGINS", "http://localhost:5174,http://127.0.0.1:5174"
    ).split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(youtube_router)
app.include_router(rumble_router)
app.include_router(channel_router)
app.include_router(history_router)
app.include_router(auth_router)
app.include_router(payments_router)