from pydantic import BaseModel, Field
from typing import Optional

from backend.schemas import JobStatusResponse


class HistoryFilter(BaseModel):
    source: Optional[str] = None
    pattern: Optional[str] = None
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)