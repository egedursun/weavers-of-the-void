import asyncio
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from aerona.db import tables
from aerona.db.base import Base

SCRIPT_LOCATION = Path(__file__).resolve().parent / "alembic"
ASYNC_DRIVER = "sqlite+aiosqlite"
SYNC_DRIVER = "sqlite"

assert tables


def build_config(database_url: str) -> Config:
    config = Config()
    config.set_main_option("script_location", str(SCRIPT_LOCATION))
    config.set_main_option("sqlalchemy.url", sync_url(database_url))
    return config


def sync_url(database_url: str) -> str:
    return database_url.replace(ASYNC_DRIVER, SYNC_DRIVER, 1)


def replay_migrations_sync(database_url: str) -> None:
    command.upgrade(build_config(database_url), "head")


def created_from_models(database_url: str) -> bool:
    engine = create_engine(sync_url(database_url))
    try:
        with engine.begin() as connection:
            if inspect(connection).get_table_names():
                return False
            Base.metadata.create_all(connection)
            return True
    finally:
        engine.dispose()


def upgrade_to_head_sync(database_url: str) -> None:
    if created_from_models(database_url):
        command.stamp(build_config(database_url), "head")
    else:
        replay_migrations_sync(database_url)


async def upgrade_to_head(database_url: str) -> None:
    await asyncio.to_thread(upgrade_to_head_sync, database_url)


def autogenerate(database_url: str, message: str) -> None:
    command.revision(build_config(database_url), message=message, autogenerate=True)
