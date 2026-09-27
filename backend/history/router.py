from fastapi import APIRouter

from backend.history.schemas import JobStatusResponse
from backend.history.db_helpers import list_jobs, get_job
from backend.services.fabric_service import list_patterns, DEFAULT_MODEL as FABRIC_DEFAULT_MODEL

router = APIRouter(prefix="/api")


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    job = await get_job(job_id)
    if job is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/history", response_model=list[JobStatusResponse])
async def get_history(
    source: str | None = None,
    pattern: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    limit = max(1, min(100000, limit))
    offset = max(0, offset)
    return await list_jobs(source=source, pattern=pattern, limit=limit, offset=offset)


@router.get("/patterns")
async def get_patterns():
    return await list_patterns()


@router.get("/models")
async def get_models():
    return {"models": [], "default": FABRIC_DEFAULT_MODEL}