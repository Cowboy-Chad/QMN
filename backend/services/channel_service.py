import asyncio
import json
import os
import subprocess

CHANNEL_URL = os.environ.get("RUMBLE_CHANNEL_URL", "https://rumble.com/c/MarinaJacobi")
MAX_RESULTS = int(os.environ.get("CHANNEL_MAX_RESULTS", "100"))


async def list_channel_videos(max_results: int = MAX_RESULTS) -> list[dict]:
    args = [
        "yt-dlp",
        "--flat-playlist",
        "--dump-json",
        "--impersonate", "Chrome-133",
        "--playlist-end", str(max_results),
        CHANNEL_URL,
    ]
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
    except asyncio.TimeoutError:
        proc.kill()
        raise RuntimeError("yt-dlp channel listing timed out after 60s")

    if proc.returncode != 0:
        stderr_str = stderr.decode().strip()[:300]
        raise RuntimeError(f"yt-dlp exited code {proc.returncode}: {stderr_str}")

    videos = []
    for line in stdout.decode().strip().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue

        raw_url = data.get("url") or data.get("webpage_url", "")
        full_url = raw_url if raw_url.startswith("http") else f"https://rumble.com{raw_url}"

        videos.append({
            "title": data.get("title"),
            "url": full_url,
            "duration": data.get("duration"),
            "view_count": data.get("view_count"),
            "upload_date": data.get("upload_date"),
        })

    return videos