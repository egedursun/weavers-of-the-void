import asyncio
from pathlib import Path

from alembic import command
from alembic.config import Config

from aerona.db.migrations import sync_url

SCRIPT_LOCATION = Path(__file__).resolve().parent / "alembic"


def library_config(database_url: str) -> Config:
    config = Config()
    config.set_main_option("script_location", str(SCRIPT_LOCATION))
    config.set_main_option("sqlalchemy.url", sync_url(database_url))
    return config


def upgrade_library_sync(database_url: str) -> None:
    command.upgrade(library_config(database_url), "head")


async def upgrade_library(database_url: str) -> None:
    await asyncio.to_thread(upgrade_library_sync, database_url)
