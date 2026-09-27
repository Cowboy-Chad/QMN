import asyncio
import os
import re
import time

from backend.rumble.db_helpers import (
    create_job, update_job_status, find_existing_job_id, find_existing_transcript,
)
from backend.rumble.service import download_and_transcribe
from backend.services.metadata_service import fetch_video_metadata
from backend.services.fabric_service import run_fabric, DEFAULT_MODEL
from backend.services.cost_service import estimate_cost

RUMBLE_CHANNEL = os.environ.get("RUMBLE_CHANNEL", "MarinaJacobi")
RUMBLE_CHANNEL_LOWER = RUMBLE_CHANNEL.lower()

_jobs: dict[str, asyncio.Task] = {}


async def run_rumble_analysis(
    url: str, pattern: str, model: str | None = None,
    analyst_name: str = "Anonymous",
    analyst_display_id: int | None = None,
) -> str:
    existing_id = await find_existing_job_id("rumble", url, pattern, model)
    if existing_id:
        return existing_id

    m = re.search(r'rumble\.com/(v[a-z0-9]+)', url)
    video_id = m.group(1) if m else None
    job_id = await create_job(
        source="rumble", url=url, pattern=pattern, video_id=video_id,
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

        if not re.search(r'rumble\.com', url):
            raise ValueError(f"URL does not appear to be a Rumble URL: {url}")

        try:
            meta = await asyncio.wait_for(fetch_video_metadata(url), timeout=10)
        except (asyncio.TimeoutError, Exception):
            meta = {}

        channel_id = meta.get("channel") or None
        channel_title = meta.get("channel") or None
        video_title = meta.get("title") or None

        channel = (channel_id or "").lower()
        if not channel:
            m = re.search(r'/c/([^/?#]+)', url)
            if m:
                channel = m.group(1).lower()
        if channel and channel != RUMBLE_CHANNEL_LOWER:
            raise ValueError(
                f"This app only supports videos from channel '{RUMBLE_CHANNEL}'. "
                f"The detected channel is '{channel or 'unknown'}'."
            )

        transcript = await find_existing_transcript("rumble", url)

        if transcript is None:
            transcript, transcript_cost = await download_and_transcribe(url)
            meta["original_transcript_cost"] = round(transcript_cost, 6)

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