import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, JSON, Integer
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    source = Column(String, nullable=False)  # youtube | rumble
    video_url = Column(Text, nullable=True)
    file_path = Column(Text, nullable=True)
    video_id = Column(String, nullable=True)
    channel_id = Column(String, nullable=True)
    channel_title = Column(Text, nullable=True)
    video_title = Column(Text, nullable=True)
    analyst_name = Column(String, default="Anonymous")
    analyst_display_id = Column(Integer, nullable=True)
    pattern = Column(String, nullable=False)
    status = Column(String, default="pending")  # pending | running | completed | failed
    transcript = Column(Text, nullable=True)
    result = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class CacheEntry(Base):
    __tablename__ = "cache_store"

    key = Column(String, primary_key=True)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    display_id = Column(Integer, unique=True, nullable=True)
    first_name = Column(String, nullable=False)
    subscription_status = Column(String, default="free")  # free | active | expired
    subscription_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )