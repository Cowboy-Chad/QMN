import asyncio
import os
import sys
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Make `backend.*` importable when alembic runs from the repo root (it does — see
# run.sh, which serves uvicorn from the root for the same reason). `prepend_sys_path = .`
# in alembic.ini covers the normal case; this is belt-and-braces for `alembic -c`
# invocations from elsewhere.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import get_connect_args, get_database_url  # noqa: E402
from backend.models import Base  # noqa: E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# The models are the single source of truth for schema; this is what lets
# `alembic revision --autogenerate` and `alembic check` compare against them.
target_metadata = Base.metadata


def _config_section() -> dict:
    """The ini section with the URL injected.

    Set here rather than via `config.set_main_option` because ConfigParser applies
    %-interpolation to values, and a generated database password is free to contain
    a percent sign. Injecting into the dict skips that entirely.
    """
    section = config.get_section(config.config_ini_section, {})
    section["sqlalchemy.url"] = get_database_url()
    return section


def run_migrations_offline() -> None:
    """Emit SQL to stdout without connecting — `alembic upgrade head --sql`."""
    context.configure(
        url=get_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        _config_section(),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args=get_connect_args(),
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
