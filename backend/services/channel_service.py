import asyncio
import json
import os
import re
import time

import cloudscraper

CHANNEL_URL = os.environ.get("RUMBLE_CHANNEL_URL", "https://rumble.com/c/MarinaJacobi")
MAX_RESULTS = int(os.environ.get("CHANNEL_MAX_RESULTS", "500"))
BATCH_SIZE = int(os.environ.get("CHANNEL_BATCH_SIZE", "3"))
CACHE_TTL = int(os.environ.get("CHANNEL_CACHE_TTL", "300"))  # 5 minutes

_SCRAPER = None
_cache: list[dict] | None = None
_cache_time: float = 0


def _get_scraper():
    global _SCRAPER
    if _SCRAPER is None:
        _SCRAPER = cloudscraper.create_scraper()
    return _SCRAPER


def _parse_video_json(html: str) -> list[dict]:
    """Extract video items from rum-videos-grid JSON script blocks in the page HTML."""
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
                videos.append({
                    "title": title,
                    "url": full_url,
                    "duration": item.get("duration"),
                    "view_count": item.get("view_count"),
                    "upload_date": item.get("upload_date"),
                })
        except (json.JSONDecodeError, Exception):
            continue
    return videos


def _has_next_page(html: str) -> str | None:
    m = re.search(r'<link\s+rel=next\s+href=["\']?([^"\' >]+)["\'>]', html)
    if m:
        return m.group(1)
    return None


def _next_page_url(url: str) -> str | None:
    """Infer the next page URL from the current page number."""
    if "?page=" in url:
        base, page = url.rsplit("?page=", 1)
        try:
            return f"{base}?page={int(page) + 1}"
        except ValueError:
            return None
    return url + "?page=2"


def _page_number(url: str) -> int:
    if "?page=" in url:
        try:
            return int(url.rsplit("?page=", 1)[1])
        except ValueError:
            return 1
    return 1


def _fetch_page(url: str) -> tuple[str, str | None]:
    """Fetch a page, return (html, next_url_or_None)."""
    scraper = _get_scraper()
    resp = scraper.get(url, timeout=30)
    resp.raise_for_status()
    html = resp.text
    next_url = _has_next_page(html)
    if next_url and not next_url.startswith("http"):
        next_url = "https://rumble.com" + next_url
    return html, next_url


async def list_channel_videos(max_results: int = MAX_RESULTS) -> list[dict]:
    global _cache, _cache_time

    # Return cached result if fresh
    now = time.time()
    if _cache is not None and now - _cache_time < CACHE_TTL:
        return _cache[:max_results]

    all_videos = []
    discovered_urls: set[str] = set()
    pending = [CHANNEL_URL]

    while pending and len(all_videos) < max_results:
        # Fetch current batch in parallel (up to BATCH_SIZE at once)
        batch = pending[:BATCH_SIZE]
        pending = pending[BATCH_SIZE:]

        results = await asyncio.gather(
            *[asyncio.to_thread(_fetch_page, url) for url in batch],
            return_exceptions=True,
        )

        for url, result in zip(batch, results):
            if isinstance(result, Exception):
                raise RuntimeError(f"Failed to fetch {url}: {result}")

            html, next_url = result

            page_videos = _parse_video_json(html)
            all_videos.extend(page_videos)

            # Schedule next page if not already discovered
            if next_url and next_url not in discovered_urls:
                discovered_urls.add(next_url)
                pending.append(next_url)

        # If we got all videos and there are no more pages, stop
        if not pending:
            break

    result = all_videos[:max_results]

    # Cache the full result
    _cache = result
    _cache_time = time.time()

    return result