from fastapi import APIRouter, Depends

from backend.history.schemas import JobStatusResponse
from backend.history.db_helpers import list_jobs, get_job
from backend.auth.dependencies import get_current_user
from backend.models import User
from backend.services.fabric_service import list_patterns, DEFAULT_MODEL as FABRIC_DEFAULT_MODEL

router = APIRouter(prefix="/api")


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str, current_user: User | None = Depends(get_current_user)):
    """Rumble jobs are public. YouTube jobs are visible only to their owner, and
    not at all to a logged-out caller."""
    job = await get_job(job_id, user_id=current_user.id if current_user else None)
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
    current_user: User | None = Depends(get_current_user),
):
    """Shared Rumble history plus, when signed in, the caller's own YouTube history."""
    limit = max(1, min(100000, limit))
    offset = max(0, offset)
    return await list_jobs(
        source=source, pattern=pattern, limit=limit, offset=offset,
        user_id=current_user.id if current_user else None,
    )


@router.get("/patterns")
async def get_patterns():
    return await list_patterns()


@router.get("/models")
async def get_models():
    return {"models": [], "default": FABRIC_DEFAULT_MODEL}