"""Alembic environment (async). Targets the app's SQLAlchemy metadata and DB URL.

GeoAlchemy2's alembic_helpers make the PostGIS geometry column + spatial index autogenerate
and render correctly (and avoid duplicate spatial-index DDL).
"""
import asyncio
from logging.config import fileConfig

from alembic import context
from geoalchemy2 import alembic_helpers
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import get_settings

# Importing app.db registers every model on Base.metadata.
import app.db  # noqa: F401
from app.models.base import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _include_object(obj, name, type_, reflected, compare_to):
    """Only manage objects on our own tables. The postgis/postgis image ships PostGIS
    tiger/topology system tables; without this filter autogenerate would try to drop them.
    Geometry-specific handling is delegated to GeoAlchemy2."""
    table_name = name if type_ == "table" else getattr(getattr(obj, "table", None), "name", None)
    if table_name is not None and table_name not in target_metadata.tables:
        return False
    return alembic_helpers.include_object(obj, name, type_, reflected, compare_to)


def _url() -> str:
    return get_settings().database_url


def run_migrations_offline() -> None:
    context.configure(
        url=_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_item=alembic_helpers.render_item,
        include_object=_include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def _do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        process_revision_directives=alembic_helpers.writer,
        render_item=alembic_helpers.render_item,
        include_object=_include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine = create_async_engine(_url(), pool_pre_ping=True)
    async with engine.connect() as connection:
        await connection.run_sync(_do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
