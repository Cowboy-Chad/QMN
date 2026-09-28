import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from backend.database import init_db
from backend.youtube.router import router as youtube_router
from backend.rumble.router import router as rumble_router
from backend.rumble.channel_router import router as channel_router
from backend.history.router import router as history_router
from backend.auth.router import router as auth_router
from backend.payments.router import router as payments_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    # Clean up any jobs left in pending/running from a previous server instance
    from backend.database import async_session
    from backend.models import AnalysisJob
    from backend.services.trial_service import refund_trial_use
    from sqlalchemy import select, update
    async with async_session() as session:
        # Capture the ids first: this set is exactly the jobs whose pipeline never
        # reached an ending, so the trial uses they consumed were never refunded by
        # the in-process handler.
        stuck = await session.execute(
            select(AnalysisJob.id).where(AnalysisJob.status.in_(["pending", "running"]))
        )
        stuck_ids = [row[0] for row in stuck.all()]
        if stuck_ids:
            await session.execute(
                update(AnalysisJob)
                .where(AnalysisJob.id.in_(stuck_ids))
                .values(status="failed", error="Server restarted")
            )
            await session.commit()

    # Give back the trial uses those jobs spent. refund_trial_use claims each job's
    # flag before crediting, so a job that already failed normally (and refunded in
    # the pipeline) cannot be refunded twice here.
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


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174", "http://127.0.0.1:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(youtube_router)
app.include_router(rumble_router)
app.include_router(channel_router)
app.include_router(history_router)
app.include_router(auth_router)
app.include_router(payments_router)