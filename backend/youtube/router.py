from fastapi import APIRouter, Depends, HTTPException

from backend.schemas import error_detail
from backend.youtube.schemas import YouTubeRequest, JobStatusResponse
from backend.youtube.db_helpers import get_job, find_existing_result
from backend.youtube.orchestrator import run_youtube_analysis
from backend.auth.dependencies import YouTubeAccess, require_youtube_access
from backend.services.auth_service import get_trial_uses_remaining
from backend.services.trial_service import TrialExhausted

router = APIRouter(prefix="/api/youtube")


@router.post("/analyze")
async def analyze_youtube(body: YouTubeRequest, access: YouTubeAccess = Depends(require_youtube_access)):
    """Queue an analysis. A paid subscriber is unlimited; a trial user is charged
    one use, unless this is a duplicate of a job they already own (dedup precedes
    the quota check, so re-opening your own result is free)."""
    try:
        job_id, remaining = await run_youtube_analysis(
            url=body.video_url, pattern=body.pattern,
            analyst_name=access.user.first_name,
            analyst_display_id=access.user.display_id,
            user_id=access.user.id,
            # Only a trial user is charged. `is_trial` comes from the dependency so
            # the decision is made in one place.
            trial_user_id=access.user.id if access.is_trial else None,
        )
    except TrialExhausted:
        # The atomic consume in create_job found nothing left. No job row was
        # created, so there is nothing to refund.
        raise HTTPException(
            status_code=402,
            detail=error_detail(
                "trial_exhausted",
                "Your free trial is used up. Subscribe to keep analyzing YouTube videos.",
                trial_uses_remaining=0,
            ),
        )

    if remaining is None:
        # Not charged: a duplicate hit, or a subscriber. Report the current count so
        # the UI never ticks down on a free duplicate.
        remaining = await get_trial_uses_remaining(access.user.id)

    return {"job_id": job_id, "status": "pending", "trial_uses_remaining": remaining}


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_youtube_job(job_id: str, access: YouTubeAccess = Depends(require_youtube_access)):
    # Scoped to the caller: YouTube history is private. 404 rather than 403 for
    # someone else's job — a 403 would confirm that a guessed id exists, and the
    # frontend has no use for the distinction.
    job = await get_job(job_id, user_id=access.user.id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/check-result")
async def check_youtube_result(
    video_url: str, pattern: str, access: YouTubeAccess = Depends(require_youtube_access),
):
    """Look for a prior analysis of this video by *this* user.

    Never decrements — it only reports. The count is the advisory one from the
    dependency, which is enough to keep the UI in step without a second /me call.
    """
    job = await find_existing_result("youtube", video_url, pattern, None, owner_id=access.user.id)
    if job is None:
        return {"found": False, "trial_uses_remaining": access.trial_uses_remaining}
    return {"found": True, "job": job, "trial_uses_remaining": access.trial_uses_remaining}
