import asyncio
import re
import time

from backend.youtube.db_helpers import (
    create_job, update_job_status, find_existing_job_id, find_existing_transcript,
)
from backend.youtube.service import fetch_transcript, _extract_video_id
from backend.services.metadata_service import fetch_video_metadata
from backend.services.fabric_service import run_fabric, DEFAULT_MODEL
from backend.services.cost_service import estimate_cost

_jobs: dict[str, asyncio.Task] = {}


async def run_youtube_analysis(
    url: str, pattern: str, model: str | None = None,
    analyst_name: str = "Anonymous",
    analyst_display_id: int | None = None,
) -> str:
    existing_id = await find_existing_job_id("youtube", url, pattern, model)
    if existing_id:
        return existing_id

    video_id = _extract_video_id(url) if url else None
    job_id = await create_job(
        source="youtube", url=url, pattern=pattern, video_id=video_id,
        analyst_name=analyst_name, analyst_display_id=analyst_display_id,
    )
    task = asyncio.create_task(_pipeline(job_id, url, pattern, model))
    _jobs[job_id] = task
    return job_id


async def _pipeline(job_id: str, url: str, pattern: str, model: str | None):
    t0 = time.time()
    meta = {}
    channel_id = None
    channel_title = None
    video_title = None

    try:
        await update_job_status(job_id, "running")

        if not re.search(r'(youtube\.com|youtu\.be)', url):
            raise ValueError(f"URL does not appear to be a YouTube URL: {url}")

        try:
            meta = await asyncio.wait_for(fetch_video_metadata(url), timeout=10)
        except (asyncio.TimeoutError, Exception):
            meta = {}

        channel_id = meta.get("channel") or None
        channel_title = meta.get("channel") or None
        video_title = meta.get("title") or None

        transcript = await find_existing_transcript("youtube", url)

        if transcript is None:
            transcript = await fetch_transcript(url)

        result = await run_fabric(pattern, transcript, model=model)

        processing_time = round(time.time() - t0, 1)
        try:
            cost_info = await estimate_cost(transcript, result, model=model or DEFAULT_MODEL)
        except Exception:
            cost_info = {}
        meta.update({
            "fabric_pattern": pattern,
            "model": model or DEFAULT_MODEL,
            "processing_time_seconds": processing_time,
            **cost_info,
        })

        await update_job_status(job_id, "completed", transcript=transcript, result=result, metadata_json=meta, channel_id=channel_id, channel_title=channel_title, video_title=video_title)

    except Exception as e:
        processing_time = round(time.time() - t0, 1)
        meta.update({"fabric_pattern": pattern, "model": model or DEFAULT_MODEL, "processing_time_seconds": processing_time})
        await update_job_status(job_id, "failed", error=str(e), metadata_json=meta, channel_id=channel_id, channel_title=channel_title, video_title=video_title)
    finally:
        _jobs.pop(job_id, None)