import asyncio
import json
import os
import re

import cloudscraper

CHANNEL_URL = os.environ.get("RUMBLE_CHANNEL_URL", "https://rumble.com/c/MarinaJacobi")
MAX_RESULTS = int(os.environ.get("CHANNEL_MAX_RESULTS", "100"))

_SCRAPER = None


def _get_scraper():
    global _SCRAPER
    if _SCRAPER is None:
        _SCRAPER = cloudscraper.create_scraper()
    return _SCRAPER


def _parse_video_json(html: str) -> list[dict]:
    """Extract video items from rum-videos-grid JSON script blocks in the page HTML."""
    videos = []
    # Find all <script type="application/json"> blocks inside <rum-videos-grid>
    pattern = re.compile(
        r'<rum-videos-grid[^>]*>\s*<script[^>]*type=["\']application/json["\'][^>]*>(.*?)</script>\s*</rum-videos-grid>',
        re.DOTALL,
    )
    for match in pattern.finditer(html):
        try:
            data = json.loads(match.group(1))
            items = data.get("items", [])
            for item in items:
                if item.get("object_type") != "video":
                    continue
                raw_url = item.get("relative_url", "")
                full_url = (
                    raw_url
                    if raw_url.startswith("http")
                    else f"https://rumble.com{raw_url}"
                )
                title = item.get("title")
                # Trim trailing garbage and clean up truncated titles
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
    """Check if there's a rel=next link and return its URL."""
    m = re.search(r'<link\s+rel=next\s+href=["\']?([^"\' >]+)["\'>]', html)
    if m:
        return m.group(1)
    return None


def _fetch_page(url: str) -> str:
    """Fetch a page using cloudscraper (bypasses Cloudflare)."""
    scraper = _get_scraper()
    resp = scraper.get(url, timeout=30)
    resp.raise_for_status()
    return resp.text


async def list_channel_videos(max_results: int = MAX_RESULTS) -> list[dict]:
    all_videos = []
    url = CHANNEL_URL

    while url and len(all_videos) < max_results:
        try:
            html = await asyncio.to_thread(_fetch_page, url)
        except Exception as e:
            raise RuntimeError(f"Failed to fetch channel page: {e}")

        page_videos = _parse_video_json(html)
        all_videos.extend(page_videos)

        url = _has_next_page(html)
        if url and not url.startswith("http"):
            url = "https://rumble.com" + url

    return all_videos[:max_results]