from fastapi import APIRouter, HTTPException

from backend.rumble.schemas import RumbleRequest, JobStatusResponse
from backend.rumble.db_helpers import get_job, find_existing_result
from backend.rumble.orchestrator import run_rumble_analysis

router = APIRouter(prefix="/api/rumble")


@router.post("/analyze")
async def analyze_rumble(body: RumbleRequest):
    job_id = await run_rumble_analysis(url=body.video_url, pattern=body.pattern)
    return {"job_id": job_id, "status": "pending"}


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_rumble_job(job_id: str):
    job = await get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/check-result")
async def check_rumble_result(video_url: str, pattern: str):
    job = await find_existing_result("rumble", video_url, pattern, None)
    if job is None:
        return {"found": False}
    return {"found": True, "job": job}