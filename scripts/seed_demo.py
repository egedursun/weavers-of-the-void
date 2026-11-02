import asyncio
import sys

from alembic import command

from aerona.db import tables
from aerona.db.base import Base
from aerona.db.migrations import build_config
from aerona.db.session import Database
from aerona.engine.pipeline import simulate
from aerona.settings import get_settings
from tests.engine.integration.factories import seed_rich_cosmos

DEFAULT_EPOCHS = 6

assert tables


async def main(epochs: int) -> None:
    settings = get_settings()
    settings.ensure_directories()
    database = Database(settings.database_url)
    try:
        async with database.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        await asyncio.to_thread(command.stamp, build_config(settings.database_url), "head")
        async with database.write() as session:
            await seed_rich_cosmos(session)
        runs = await simulate(database, epochs)
        print(f"seeded a demo cosmos and simulated {len(runs)} epochs into {settings.database_path}")
    finally:
        await database.dispose()


if __name__ == "__main__":
    asyncio.run(main(int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_EPOCHS))
