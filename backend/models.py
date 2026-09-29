import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, JSON, Integer, Boolean
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
    # Owner of the job. NULL for Rumble (free/shared history); set for YouTube so
    # history and duplicate detection can be scoped per user.
    user_id = Column(String, nullable=True, index=True)
    # True when this job consumed one free-trial use. Doubles as the claim flag that
    # makes refund_trial_use idempotent (cleared on refund).
    trial_use_consumed = Column(Boolean, default=False)
    pattern = Column(String, nullable=False)
    status = Column(String, default="pending")  # pending | running | completed | failed
    transcript = Column(Text, nullable=True)
    result = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    # timezone=True -> Postgres timestamptz. Required, not cosmetic: every default
    # below writes an aware datetime, and asyncpg rejects an aware value bound to a
    # naive `timestamp without time zone` column. SQLite used to discard the offset
    # silently, which hid the mismatch.
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class CacheEntry(Base):
    __tablename__ = "cache_store"

    key = Column(String, primary_key=True)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    display_id = Column(Integer, unique=True, nullable=True)  # display/attribution only, not a credential
    first_name = Column(String, nullable=False)  # derived from full_name's first token, for the nav bar
    full_name = Column(String, nullable=True)  # as typed at signup
    email = Column(String, nullable=False, unique=True, index=True)  # login identity (stored lowercased)
    password_hash = Column(String, nullable=False)  # bcrypt
    # NULL = no free trial on this account. 0 = trial exhausted. Both states render
    # differently, so NULL and 0 must stay distinguishable.
    trial_uses_remaining = Column(Integer, nullable=True)
    subscription_status = Column(String, default="free")  # free | active | expired
    subscription_expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )