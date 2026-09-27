from pydantic import BaseModel
from typing import Optional

from backend.schemas import JobStatusResponse


class YouTubeRequest(BaseModel):
    video_url: str = ""
    pattern: str