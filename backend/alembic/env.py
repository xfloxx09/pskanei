import asyncio
import os

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.config import _as_async_postgres_url
from app.database import Base
from app.models import Story, ScrapeSettings, Provider, PlatformAccount, PublishedClip  # noqa: F401

config = context.config
target_metadata = Base.metadata


def run_migrations_offline():
    raw = config.get_main_option("sqlalchemy.url")
    url = os.getenv("DATABASE_URL", raw)
    url = _as_async_postgres_url(url)
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations():
    section = config.get_section(config.config_ini_section, {})
    raw = section.get("sqlalchemy.url", "")
    if raw:
        section["sqlalchemy.url"] = _as_async_postgres_url(
            os.getenv("DATABASE_URL", raw)
        )
    connectable = async_engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online():
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
