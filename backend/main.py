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
    from sqlalchemy import update
    async with async_session() as session:
        await session.execute(
            update(AnalysisJob)
            .where(AnalysisJob.status.in_(["pending", "running"]))
            .values(status="failed", error="Server restarted")
        )
        await session.commit()
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