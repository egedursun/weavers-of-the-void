import asyncio
from pathlib import Path

from alembic import command
from alembic.config import Config

SCRIPT_LOCATION = Path(__file__).resolve().parent / "alembic"
ASYNC_DRIVER = "sqlite+aiosqlite"
SYNC_DRIVER = "sqlite"


def build_config(database_url: str) -> Config:
    config = Config()
    config.set_main_option("script_location", str(SCRIPT_LOCATION))
    config.set_main_option("sqlalchemy.url", database_url.replace(ASYNC_DRIVER, SYNC_DRIVER, 1))
    return config


def upgrade_to_head_sync(database_url: str) -> None:
    command.upgrade(build_config(database_url), "head")


async def upgrade_to_head(database_url: str) -> None:
    await asyncio.to_thread(upgrade_to_head_sync, database_url)


def autogenerate(database_url: str, message: str) -> None:
    command.revision(build_config(database_url), message=message, autogenerate=True)
