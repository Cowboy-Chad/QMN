import asyncio
import json
import os
import re
import time
from datetime import datetime, timezone

import cloudscraper

from backend.services.database_helpers import get_cache, set_cache

CHANNEL_URL = os.environ.get("RUMBLE_CHANNEL_URL", "https://rumble.com/c/MarinaJacobi")
MAX_RESULTS = int(os.environ.get("CHANNEL_MAX_RESULTS", "500"))
BATCH_SIZE = int(os.environ.get("CHANNEL_BATCH_SIZE", "3"))
REFRESH_INTERVAL = int(os.environ.get("CHANNEL_REFRESH_INTERVAL", "3600"))  # 1 hour
CACHE_KEY = "channel_videos"

_SCRAPER = None
_background_task: asyncio.Task | None = None


def _get_scraper():
    global _SCRAPER
    if _SCRAPER is None:
        _SCRAPER = cloudscraper.create_scraper()
    return _SCRAPER


def _parse_season_episode(title: str | None) -> tuple[int, int]:
    """Extract (season, episode) from a video title. Returns (999, 999) for unknown.
    Finds the best match — prefers a match with both season AND episode over
    a match with season alone."""
    if not title:
        return (999, 999)
    # Patterns: "S5 E3", "Season 5 Episode 3", "S12E5", "S5 E20"
    pattern = re.compile(
        r'(?:^|\b)S(?:eason)?[.\s]*(\d+)(?:[.\s]*E(?:p(?:isode)?)?[.\s]*(\d+))?',
        re.IGNORECASE,
    )
    best = None
    for m in pattern.finditer(title):
        season = int(m.group(1))
        episode = int(m.group(2)) if m.group(2) else 0
        # Prefer matches that have both season AND episode
        if episode > 0:
            return (season, episode)  # found a complete match, use it
        if best is None:
            best = (season, episode)
    return best if best else (999, 999)


def _parse_video_json(html: str) -> list[dict]:
    videos = []
    pattern = re.compile(
        r'<rum-videos-grid[^>]*>\s*<script[^>]*type=["\']application/json["\'][^>]*>(.*?)</script>\s*</rum-videos-grid>',
        re.DOTALL,
    )
    for match in pattern.finditer(html):
        try:
            data = json.loads(match.group(1))
            for item in data.get("items", []):
                if item.get("object_type") != "video":
                    continue
                raw_url = item.get("relative_url", "")
                full_url = (
                    raw_url
                    if raw_url.startswith("http")
                    else f"https://rumble.com{raw_url}"
                )
                title = item.get("title")
                if title and isinstance(title, str):
                    title = title.rstrip(".… ")
                season_ep = _parse_season_episode(title)
                videos.append({
                    "title": title,
                    "url": full_url,
                    "duration": item.get("duration"),
                    "view_count": item.get("view_count"),
                    "upload_date": item.get("upload_date"),
                    "season": season_ep[0],
                    "episode": season_ep[1],
                })
        except (json.JSONDecodeError, Exception):
            continue
    return videos


def _has_next_page(html: str) -> str | None:
    m = re.search(r'<link\s+rel=next\s+href=["\']?([^"\' >]+)["\'>]', html)
    if m:
        return m.group(1)
    return None


def _fetch_page(url: str) -> tuple[str, str | None]:
    scraper = _get_scraper()
    resp = scraper.get(url, timeout=30)
    resp.raise_for_status()
    html = resp.text
    next_url = _has_next_page(html)
    if next_url and not next_url.startswith("http"):
        next_url = "https://rumble.com" + next_url
    return html, next_url


async def _fetch_all_videos(max_results: int) -> list[dict]:
    """Fetch all channel pages from Rumble and return video list."""
    all_videos = []
    discovered_urls: set[str] = set()
    pending = [CHANNEL_URL]

    while pending and len(all_videos) < max_results:
        batch = pending[:BATCH_SIZE]
        pending = pending[BATCH_SIZE:]

        results = await asyncio.gather(
            *[asyncio.to_thread(_fetch_page, url) for url in batch],
            return_exceptions=True,
        )

        for url, result in zip(batch, results):
            if isinstance(result, Exception):
                continue  # skip failed pages, return what we have
            html, next_url = result
            page_videos = _parse_video_json(html)
            all_videos.extend(page_videos)
            if next_url and next_url not in discovered_urls:
                discovered_urls.add(next_url)
                pending.append(next_url)

        if not pending:
            break

    all_videos.sort(key=lambda v: (v.get("season", 999), v.get("episode", 0)))
    return all_videos[:max_results]


async def _refresh_cache():
    """Background task: fetch videos from Rumble and store to DB."""
    global _background_task
    try:
        videos = await _fetch_all_videos(MAX_RESULTS)
        await set_cache(CACHE_KEY, json.dumps(videos))
    except Exception:
        pass  # background failure is non-fatal; stale cache is served
    finally:
        _background_task = None


async def list_channel_videos(max_results: int = MAX_RESULTS) -> list[dict]:
    global _background_task

    # 1. Try DB cache
    cached_json, updated_at = await get_cache(CACHE_KEY)

    if cached_json:
        videos = json.loads(cached_json)

        # 2. If cache is stale, trigger a background refresh (non-blocking)
        if updated_at:
            # DB stores naive UTC datetimes; make comparison safe
            now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
            cache_stored = updated_at.replace(tzinfo=None) if updated_at.tzinfo else updated_at
            age = (now_naive - cache_stored).total_seconds()
            if age > REFRESH_INTERVAL and _background_task is None:
                _background_task = asyncio.create_task(_refresh_cache())

        return videos[:max_results]

    # 3. No cache at all (first-ever request) — fetch synchronously, store, return
    videos = await _fetch_all_videos(MAX_RESULTS)
    await set_cache(CACHE_KEY, json.dumps(videos))
    return videos[:max_results]