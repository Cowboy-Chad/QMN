import asyncio
import json
import re
import subprocess


def _build_metadata(data: dict) -> dict:
    metadata = {
        "title": data.get("title"),
        "channel": data.get("channel") or data.get("uploader"),
        "channel_url": data.get("channel_url") or data.get("uploader_url"),
        "channel_subscribers": data.get("channel_follower_count"),
        "view_count": data.get("view_count"),
        "upload_date": data.get("upload_date"),
        "duration_seconds": data.get("duration"),
        "webpage_url": data.get("webpage_url"),
        "timestamp": data.get("timestamp"),
    }

    duration = data.get("duration")
    if duration:
        h, r = divmod(duration, 3600)
        m, s = divmod(r, 60)
        if h:
            metadata["duration_display"] = f"{h}:{m:02d}:{s:02d}"
        else:
            metadata["duration_display"] = f"{m}:{s:02d}"

    upload_date = data.get("upload_date")
    timestamp = data.get("timestamp")
    if upload_date and len(upload_date) == 8:
        import datetime
        dt = datetime.datetime.strptime(upload_date, "%Y%m%d")
        metadata["upload_date_display"] = dt.strftime("%Y-%m-%d")
        if timestamp:
            metadata["upload_date_relative"] = _relative_time(datetime.datetime.fromtimestamp(timestamp))
        else:
            metadata["upload_date_relative"] = _relative_time(dt)

    return metadata


async def _fetch_rumble_metadata(url: str) -> dict:
    meta = {}

    # Primary: oEmbed API — fast, reliable, no Cloudflare issues
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://rumble.com/api/Media/oembed.json",
                params={"url": url},
            )
            if resp.status_code == 200:
                data = resp.json()
                meta["title"] = data.get("title")
                meta["webpage_url"] = url
                dur = data.get("duration")
                if dur:
                    meta["duration_seconds"] = dur
                    h, r = divmod(dur, 3600)
                    m, s = divmod(r, 60)
                    meta["duration_display"] = (
                        f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
                    )
                author_url = data.get("author_url", "")
                if author_url:
                    m_ch = re.search(r'/c/([^/?#]+)', author_url)
                    if m_ch:
                        meta["channel"] = m_ch.group(1)
    except Exception:
        pass

    # Secondary: scrape page for metadata not available in oEmbed
    try:
        import cloudscraper
        scraper = cloudscraper.create_scraper()
        resp = await asyncio.to_thread(scraper.get, url, timeout=30)
        resp.raise_for_status()
        html = resp.text

        # JSON-LD for upload date, view count, etc.
        ld_match = re.search(
            r'<script[^>]*type=["\']?application/ld\+json["\']?[^>]*>(.*?)</script>',
            html, re.DOTALL,
        )
        if ld_match:
            try:
                ld_list = json.loads(ld_match.group(1))
                if isinstance(ld_list, list):
                    for item in ld_list:
                        if isinstance(item, dict) and item.get("@type") == "VideoObject":
                            ld = item
                            break
                    else:
                        ld = None
                else:
                    ld = ld_list if isinstance(ld_list, dict) else None

                if isinstance(ld, dict):
                    if not meta.get("upload_date_display"):
                        upload_date = ld.get("uploadDate")
                        if upload_date:
                            meta["upload_date_display"] = upload_date
                            meta["upload_date_relative"] = _relative_time_str(upload_date)
                    if not meta.get("view_count"):
                        stat = ld.get("interactionStatistic")
                        if isinstance(stat, dict):
                            meta["view_count"] = stat.get("userInteractionCount")
                        elif isinstance(stat, list):
                            for s_item in stat:
                                if isinstance(s_item, dict) and s_item.get("interactionType", "").endswith("WatchAction"):
                                    meta["view_count"] = s_item.get("userInteractionCount")
                                    break
            except (json.JSONDecodeError, Exception):
                pass

        # View count from page text (fallback if JSON-LD didn't have it)
        if not meta.get("view_count"):
            m = re.search(r'(\d[\d,]*)\s*views', html)
            if m:
                meta["view_count"] = int(m.group(1).replace(",", ""))

        # Upload date from page text (fallback)
        if not meta.get("upload_date_display"):
            m = re.search(r'(\d{1,2}\s+\w+\s+\d{4})', html)
            if m:
                meta["upload_date_display"] = m.group(1)
                meta["upload_date_relative"] = _relative_time_str(m.group(1))

    except Exception:
        pass

    return meta


def _relative_time_str(date_str: str) -> str:
    import datetime
    for fmt in ("%Y-%m-%d", "%d %B %Y", "%d %b %Y", "%d %B %Y"):
        try:
            dt = datetime.datetime.strptime(date_str, fmt)
            now = datetime.datetime.now()
            diff = now - dt
            if diff.days >= 365:
                years = diff.days // 365
                return f"{years} year{'s' if years > 1 else ''} ago"
            if diff.days >= 30:
                months = diff.days // 30
                return f"{months} month{'s' if months > 1 else ''} ago"
            if diff.days > 0:
                return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
            if diff.seconds >= 3600:
                hours = diff.seconds // 3600
                return f"{hours} hour{'s' if hours > 1 else ''} ago"
            return "today"
        except ValueError:
            continue
    return date_str


async def fetch_video_metadata(url: str) -> dict:
    try:
        proc = await asyncio.create_subprocess_exec(
            "yt-dlp",
            "--impersonate", "Chrome-133",
            "--dump-json",
            url,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=15)
        if proc.returncode != 0:
            raise RuntimeError(f"yt-dlp exited with code {proc.returncode}")
        data = json.loads(stdout.decode().strip())
        return _build_metadata(data)
    except (asyncio.TimeoutError, Exception):
        if re.search(r'rumble\.com', url):
            return await _fetch_rumble_metadata(url)
        return {}


def _relative_time(dt):
    import datetime
    now = datetime.datetime.now(dt.tzinfo) if dt.tzinfo else datetime.datetime.now()
    diff = now - dt
    if diff.days >= 365:
        years = diff.days // 365
        return f"{years} year{'s' if years > 1 else ''} ago"
    if diff.days >= 30:
        months = diff.days // 30
        return f"{months} month{'s' if months > 1 else ''} ago"
    if diff.days > 0:
        return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
    if diff.seconds >= 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    return "today"