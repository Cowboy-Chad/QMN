from fastapi import APIRouter, HTTPException

from backend.youtube.schemas import YouTubeRequest, JobStatusResponse
from backend.youtube.db_helpers import get_job, find_existing_result
from backend.youtube.orchestrator import run_youtube_analysis

router = APIRouter(prefix="/api/youtube")


@router.post("/analyze")
async def analyze_youtube(body: YouTubeRequest):
    job_id = await run_youtube_analysis(url=body.video_url, pattern=body.pattern)
    return {"job_id": job_id, "status": "pending"}


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_youtube_job(job_id: str):
    job = await get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/check-result")
async def check_youtube_result(video_url: str, pattern: str):
    job = await find_existing_result("youtube", video_url, pattern, None)
    if job is None:
        return {"found": False}
    return {"found": True, "job": job}