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
    source: str, url: str | None, pattern: str, model: str | None,
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
            .where(AnalysisJob.status.in_(["pending", "running", "completed"]))
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
    analyst_name: str = "Anonymous",
    analyst_display_id: int | None = None,
) -> str:
    async with async_session() as session:
        job = AnalysisJob(
            source=source,
            video_url=url,
            file_path=file_path,
            video_id=video_id,
            pattern=pattern,
            status="pending",
            analyst_name=analyst_name,
            analyst_display_id=analyst_display_id,
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
    """Upsert a cache row.

    A single INSERT ... ON CONFLICT DO UPDATE, not read-then-insert. Two writers
    can race here — the background refresh task and the synchronous first-request
    path in channel_service.list_channel_videos — and on Postgres the loser of a
    read-then-insert race raises IntegrityError out of a request handler.

    Deliberately not `try/except IntegrityError`: on Postgres a failed statement
    poisons the surrounding transaction and would need a SAVEPOINT to recover,
    which is exactly the trap the old database._migrate() fell into.
    """
    from datetime import datetime, timezone
    from sqlalchemy.dialects.postgresql import insert

    now = datetime.now(timezone.utc)
    stmt = (
        insert(CacheEntry)
        .values(key=key, value=value, updated_at=now)
        .on_conflict_do_update(
            index_elements=[CacheEntry.key],
            set_={"value": value, "updated_at": now},
        )
    )
    async with async_session() as session:
        await session.execute(stmt)
        await session.commit()