from fastapi import APIRouter, Depends, HTTPException

from backend.youtube.schemas import YouTubeRequest, JobStatusResponse
from backend.youtube.db_helpers import get_job, find_existing_result
from backend.youtube.orchestrator import run_youtube_analysis
from backend.auth.dependencies import require_subscriber
from backend.models import User

router = APIRouter(prefix="/api/youtube")


@router.post("/analyze")
async def analyze_youtube(body: YouTubeRequest, current_user: User = Depends(require_subscriber)):
    job_id = await run_youtube_analysis(
        url=body.video_url, pattern=body.pattern,
        analyst_name=current_user.first_name,
        analyst_display_id=current_user.display_id,
    )
    return {"job_id": job_id, "status": "pending"}


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_youtube_job(job_id: str, current_user: User = Depends(require_subscriber)):
    job = await get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/check-result")
async def check_youtube_result(video_url: str, pattern: str, current_user: User = Depends(require_subscriber)):
    job = await find_existing_result("youtube", video_url, pattern, None)
    if job is None:
        return {"found": False}
    return {"found": True, "job": job}