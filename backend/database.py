import os

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Local development default. Matches docker-compose.yml exactly, so `docker compose
# up -d db` plus `./run.sh` works with no .env file at all.
DEFAULT_DATABASE_URL = "postgresql+asyncpg://marina:marina@localhost:5432/marina"

# libpq-only query parameters. Render's connection string carries some of these and
# asyncpg rejects them as unexpected keyword arguments, so they are stripped.
_LIBPQ_ONLY_PARAMS = ("sslmode", "channel_binding", "options", "target_session_attrs")


def get_database_url() -> str:
    """Normalize DATABASE_URL into a form asyncpg can actually connect with.

    Exposed (rather than inlined) so alembic/env.py uses the identical logic —
    one normalizer, so the app and migrations can never disagree about which
    database they mean.
    """
    raw = os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)

    # Render's `connectionString` property emits the bare libpq form
    # (postgres:// or postgresql://). SQLAlchemy needs the driver spelled out.
    for prefix in ("postgres://", "postgresql://"):
        if raw.startswith(prefix):
            raw = "postgresql+asyncpg://" + raw[len(prefix):]
            break

    url = make_url(raw)

    query = {k: v for k, v in url.query.items() if k not in _LIBPQ_ONLY_PARAMS}
    if query != url.query:
        url = url.set(query=query)

    return url.render_as_string(hide_password=False)


def get_connect_args() -> dict:
    """TLS settings for asyncpg.

    Render's *internal* connection string (same private network) needs no TLS.
    The *external* one does. `DATABASE_SSL` forces the decision:
    auto (default) | require | disable.
    """
    mode = os.environ.get("DATABASE_SSL", "auto").strip().lower()

    if mode == "require":
        return {"ssl": "require"}
    if mode == "disable":
        return {}

    # auto: external Render hosts look like dpg-xxxxx-a.oregon-postgres.render.com,
    # internal ones are short names with no domain.
    host = make_url(get_database_url()).host or ""
    if "render.com" in host:
        return {"ssl": "require"}
    return {}


DATABASE_URL = get_database_url()

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    # Render's connection proxy silently drops idle TCP connections, which surfaces
    # as a stale-connection error on the first query after an idle period.
    pool_pre_ping=True,
    pool_recycle=1800,
    pool_size=5,
    max_overflow=5,
    pool_timeout=30,
    connect_args=get_connect_args(),
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Schema is owned by Alembic (`alembic upgrade head`), never by the app — see
# alembic/versions/. The previous init_db()/create_all()/_migrate() pair was
# removed so a failed migration fails the deploy instead of being papered over.
