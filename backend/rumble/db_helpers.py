from typing import Optional

from backend.models import AnalysisJob, CacheEntry
from backend.database import async_session
from backend.rumble.schemas import JobStatusResponse
from backend.services.fabric_service import DEFAULT_MODEL


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
    source: str, url: str | None, pattern: str, model: str | None
) -> JobStatusResponse | None:
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
    source: str, url: str | None, pattern: str, model: str | None
) -> str | None:
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
        result = await session.execute(stmt)
        jobs = result.scalars().all()
        for job in jobs:
            stored = (job.metadata_json or {}).get("model")
            if stored == requested:
                return job.id
            if stored is None and requested == DEFAULT_MODEL:
                return job.id
    return None


async def find_existing_transcript(source: str, url: str) -> str | None:
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
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing and existing.transcript:
            return existing.transcript
    return None


async def create_job(
    source: str, url: str | None, pattern: str, file_path: str | None = None,
    video_id: str | None = None,
) -> str:
    async with async_session() as session:
        job = AnalysisJob(
            source=source,
            video_url=url,
            file_path=file_path,
            video_id=video_id,
            pattern=pattern,
            status="pending",
        )
        session.add(job)
        await session.commit()
        return job.id


async def update_job_status(job_id: str, status: str, **extra_fields):
    async with async_session() as session:
        job = await session.get(AnalysisJob, job_id)
        if job:
            job.status = status
            for k, v in extra_fields.items():
                setattr(job, k, v)
            await session.commit()


async def get_cache(key: str) -> tuple[str | None, datetime | None]:
    from datetime import datetime
    async with async_session() as session:
        entry = await session.get(CacheEntry, key)
        if entry:
            return entry.value, entry.updated_at
        return None, None


async def set_cache(key: str, value: str):
    from datetime import datetime, timezone
    async with async_session() as session:
        entry = await session.get(CacheEntry, key)
        if entry:
            entry.value = value
            entry.updated_at = datetime.now(timezone.utc)
        else:
            session.add(CacheEntry(key=key, value=value))
        await session.commit()