from typing import Optional

from backend.models import AnalysisJob
from backend.database import async_session
from backend.youtube.schemas import JobStatusResponse
from backend.services.fabric_service import DEFAULT_MODEL


async def get_job(job_id: str, user_id: str | None = None) -> Optional[JobStatusResponse]:
    """Fetch a job, optionally requiring it to belong to `user_id`.

    Pass `user_id` for YouTube: history is private per user. Rumble leaves it None
    and keeps its shared history.

    The ownership test is folded into the lookup rather than exposing the owner in
    the response, and returns None (not a 403) so a guessed job id is indistinguishable
    from a nonexistent one.
    """
    async with async_session() as session:
        job = await session.get(AnalysisJob, job_id)
        if job is None:
            return None
        if user_id is not None and job.user_id != user_id:
            # A NULL owner compares unequal to a real id, so unowned rows (Rumble)
            # are correctly invisible here too.
            return None
        return JobStatusResponse(
            id=job.id,
            source=job.source,
            video_url=job.video_url,
            video_id=job.video_id,
            channel_id=job.channel_id,
            channel_title=job.channel_title,
            video_title=job.video_title,
            analyst_name=job.analyst_name,
            analyst_display_id=job.analyst_display_id,
            pattern=job.pattern,
            status=job.status,
            transcript=job.transcript,
            result=job.result,
            error=job.error,
            metadata_json=job.metadata_json,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )


async def _job_to_response(job: AnalysisJob) -> JobStatusResponse:
    return JobStatusResponse(
        id=job.id,
        source=job.source,
        video_url=job.video_url,
        video_id=job.video_id,
        channel_id=job.channel_id,
        channel_title=job.channel_title,
        video_title=job.video_title,
        analyst_name=job.analyst_name,
        analyst_display_id=job.analyst_display_id,
        pattern=job.pattern,
        status=job.status,
        transcript=job.transcript,
        result=job.result,
        error=job.error,
        metadata_json=job.metadata_json,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


async def find_existing_result(
    source: str, url: str | None, pattern: str, model: str | None,
    owner_id: str | None = None,
) -> JobStatusResponse | None:
    """Find a completed analysis matching this url+pattern (+model).

    `owner_id` scopes the search to one user's jobs. YouTube passes it because
    analyses are private: without it, user B would be shown user A's cached result.
    """
    if not url:
        return None
    from sqlalchemy import select, desc
    requested = model or DEFAULT_MODEL
    async with async_session() as session:
        stmt = (
            select(AnalysisJob)
            .where(AnalysisJob.source == source)
            .where(AnalysisJob.video_url == url)
            .where(AnalysisJob.pattern == pattern)
            .where(AnalysisJob.status == "completed")
            .where(AnalysisJob.result.isnot(None))
            .order_by(desc(AnalysisJob.created_at))
        )
        if owner_id is not None:
            stmt = stmt.where(AnalysisJob.user_id == owner_id)
        result = await session.execute(stmt)
        jobs = result.scalars().all()
        for job in jobs:
            stored = (job.metadata_json or {}).get("model")
            if stored == requested:
                return await _job_to_response(job)
            if stored is None and requested == DEFAULT_MODEL:
                return await _job_to_response(job)
    return None


async def find_existing_job_id(
    source: str, url: str | None, pattern: str, model: str | None,
    owner_id: str | None = None,
) -> str | None:
    """Find an existing job id for this url+pattern (+model), completed or in flight.

    `owner_id` scoping is required for correctness, not just tidiness: unscoped, this
    would hand user B *user A's* job id, and B's ownership check would then 404 on the
    very job the server just told them to poll.
    """
    if not url:
        return None
    from sqlalchemy import select, desc
    requested = model or DEFAULT_MODEL
    async with async_session() as session:
        stmt = (
            select(AnalysisJob)
            .where(AnalysisJob.source == source)
            .where(AnalysisJob.video_url == url)
            .where(AnalysisJob.pattern == pattern)
            .where(AnalysisJob.status.in_(["pending", "running", "completed"]))
            .order_by(desc(AnalysisJob.created_at))
        )
        if owner_id is not None:
            stmt = stmt.where(AnalysisJob.user_id == owner_id)
        result = await session.execute(stmt)
        jobs = result.scalars().all()
        for job in jobs:
            stored = (job.metadata_json or {}).get("model")
            if stored == requested:
                return job.id
            if stored is None and requested == DEFAULT_MODEL:
                return job.id
    return None


async def find_existing_transcript(
    source: str, url: str, owner_id: str | None = None,
) -> str | None:
    """Reuse a previously fetched transcript for the same video.

    `owner_id` is passed only by the YouTube pipeline, because YouTube analyses are
    per-user — reusing another user's transcript would mean serving a result derived
    from their cached run. Rumble passes nothing and keeps its shared cache (subtitles
    are free to fetch, so the only cost here is one extra lookup).
    """
    if not url:
        return None
    from sqlalchemy import select
    async with async_session() as session:
        stmt = (
            select(AnalysisJob)
            .where(AnalysisJob.source == source)
            .where(AnalysisJob.video_url == url)
            .where(AnalysisJob.transcript.isnot(None))
            .where(AnalysisJob.status.in_(["completed"]))
            .order_by(AnalysisJob.created_at.desc())
            .limit(1)
        )
        if owner_id is not None:
            stmt = stmt.where(AnalysisJob.user_id == owner_id)
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing and existing.transcript:
            return existing.transcript
    return None


async def create_job(
    source: str, url: str | None, pattern: str, file_path: str | None = None,
    video_id: str | None = None,
    analyst_name: str = "Anonymous",
    analyst_display_id: int | None = None,
    user_id: str | None = None,
    trial_user_id: str | None = None,
) -> tuple[str, int | None]:
    """Create a job row. Returns (job_id, trial_uses_remaining).

    `trial_uses_remaining` is None when no trial use was charged (Rumble, or a
    subscriber), otherwise the count left *after* this job's use was consumed.

    When `trial_user_id` is given, the consume and the INSERT deliberately share one
    session and one commit: the conditional UPDATE in decrement_trial_use is the real
    quota gate, and pairing it with the INSERT means a failed insert costs nothing and
    a successful one is always paid for. That is what stops two tabs both seeing
    "1 left" from both proceeding.
    """
    from backend.services.trial_service import decrement_trial_use

    async with async_session() as session:
        remaining = None
        if trial_user_id:
            remaining = await decrement_trial_use(session, trial_user_id)
        job = AnalysisJob(
            source=source,
            video_url=url,
            file_path=file_path,
            video_id=video_id,
            pattern=pattern,
            status="pending",
            analyst_name=analyst_name,
            analyst_display_id=analyst_display_id,
            user_id=user_id,
            # Doubles as the claim flag that makes refund_trial_use idempotent.
            trial_use_consumed=trial_user_id is not None,
        )
        session.add(job)
        await session.commit()
        return job.id, remaining


async def update_job_status(job_id: str, status: str, **extra_fields):
    async with async_session() as session:
        job = await session.get(AnalysisJob, job_id)
        if job:
            job.status = status
            for k, v in extra_fields.items():
                setattr(job, k, v)
            await session.commit()