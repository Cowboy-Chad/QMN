import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "marina_jacobi.db")
DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    from backend.models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Migration: add/rename columns in existing tables (safe to run multiple times)
    async with engine.begin() as conn:
        def _migrate(connection):
            import sqlalchemy as sa
            inspector = sa.inspect(connection)
            cols = {c["name"] for c in inspector.get_columns("analysis_jobs")}

            # Rename url → video_url
            if "url" in cols and "video_url" not in cols:
                connection.execute(sa.text("ALTER TABLE analysis_jobs RENAME COLUMN url TO video_url"))

            # Refresh column list after rename
            cols = {c["name"] for c in inspector.get_columns("analysis_jobs")}
            for col in ("video_id", "channel_id", "channel_title", "video_title"):
                if col not in cols:
                    connection.execute(sa.text(f"ALTER TABLE analysis_jobs ADD COLUMN {col} VARCHAR"))
        await conn.run_sync(_migrate)


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session