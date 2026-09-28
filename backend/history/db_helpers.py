from typing import Optional

from backend.models import AnalysisJob
from backend.database import async_session
from backend.history.schemas import JobStatusResponse


async def list_jobs(
    source: Optional[str] = None,
    pattern: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    user_id: Optional[str] = None,
) -> list[JobStatusResponse]:
    """List history, applying per-user visibility.

    Rumble history is shared with everyone (its rows have no owner). YouTube history
    is private: it is only ever returned to the user who owns it, and never to a
    logged-out caller. `user_id == uid` is never true for a row whose owner is NULL,
    so unowned rows stay out of a YouTube-scoped query by construction.
    """
    from sqlalchemy import select, desc, or_

    # No anonymous YouTube history at all: a logged-out caller asking for it gets
    # nothing rather than everyone's.
    if source == "youtube" and user_id is None:
        return []

    async with async_session() as session:
        stmt = select(AnalysisJob)
        if source:
            stmt = stmt.where(AnalysisJob.source == source)
            if source == "youtube":
                stmt = stmt.where(AnalysisJob.user_id == user_id)
        else:
            # "All": every Rumble job, plus only this user's YouTube jobs.
            stmt = stmt.where(
                or_(AnalysisJob.source != "youtube", AnalysisJob.user_id == user_id)
            )
        if pattern:
            stmt = stmt.where(AnalysisJob.pattern == pattern)
        stmt = stmt.order_by(desc(AnalysisJob.created_at)).offset(offset).limit(limit)
        result = await session.execute(stmt)
        jobs = result.scalars().all()
        return [
            JobStatusResponse(
                id=j.id,
                source=j.source,
                video_url=j.video_url,
                video_id=j.video_id,
                channel_id=j.channel_id,
                channel_title=j.channel_title,
                video_title=j.video_title,
                analyst_name=j.analyst_name,
                analyst_display_id=j.analyst_display_id,
                pattern=j.pattern,
                status=j.status,
                transcript=j.transcript,
                result=j.result,
                error=j.error,
                metadata_json=j.metadata_json,
                created_at=j.created_at,
                updated_at=j.updated_at,
            )
            for j in jobs
        ]


async def get_job(job_id: str, user_id: Optional[str] = None) -> Optional[JobStatusResponse]:
    """Fetch a single job, applying the same visibility rules as list_jobs.

    The ownership test is folded into the query rather than checked afterwards, and
    a non-visible job returns None (the caller turns that into a 404) — a 403 would
    confirm that a guessed id exists.
    """
    from sqlalchemy import select, or_

    async with async_session() as session:
        stmt = select(AnalysisJob).where(AnalysisJob.id == job_id)
        if user_id is None:
            # Logged out: Rumble only.
            stmt = stmt.where(AnalysisJob.source != "youtube")
        else:
            stmt = stmt.where(
                or_(AnalysisJob.source != "youtube", AnalysisJob.user_id == user_id)
            )
        job = await session.scalar(stmt)
        if job is None:
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