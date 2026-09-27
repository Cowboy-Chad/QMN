from typing import Optional

from backend.models import AnalysisJob
from backend.database import async_session
from backend.history.schemas import JobStatusResponse


async def list_jobs(
    source: Optional[str] = None,
    pattern: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[JobStatusResponse]:
    async with async_session() as session:
        from sqlalchemy import select, desc
        stmt = select(AnalysisJob)
        if source:
            stmt = stmt.where(AnalysisJob.source == source)
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


async def get_job(job_id: str) -> Optional[JobStatusResponse]:
    async with async_session() as session:
        job = await session.get(AnalysisJob, job_id)
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