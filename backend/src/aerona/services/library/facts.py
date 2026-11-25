import asyncio
import logging
import sqlite3
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.session import Database
from aerona.db.tables.cosmos import CosmosRow
from aerona.engine.primitives.capacity import LAND_COMMUNITY_TYPES
from aerona.engine.primitives.queries import canon, living_sons
from aerona.engine.primitives.stats import stat
from aerona.paths import UniversePaths
from aerona.services.library.catalogue import UniverseFacts

logger = logging.getLogger(__name__)

REVISION_QUERY = text("SELECT version_num FROM alembic_version LIMIT 1")
SEED_SUMMARY_LENGTH = 400


def folder_size(root: Path) -> int:
    if not root.is_dir():
        return 0
    total = 0
    for path in root.rglob("*"):
        try:
            if path.is_file() and not path.is_symlink():
                total += path.stat().st_size
        except OSError:
            continue
    return total


def read_revision(database: Path) -> str:
    if not database.is_file():
        return ""
    connection = sqlite3.connect(database)
    try:
        found = connection.execute(str(REVISION_QUERY)).fetchone()
    except sqlite3.Error:
        return ""
    finally:
        connection.close()
    return str(found[0]) if found else ""


async def schema_revision_at(paths: UniversePaths) -> str:
    return await asyncio.to_thread(read_revision, paths.database)


async def schema_revision(session: AsyncSession) -> str:
    try:
        found = await session.scalar(REVISION_QUERY)
    except Exception:
        return ""
    return str(found or "")


async def facts_in(session: AsyncSession, size_bytes: int) -> UniverseFacts:
    cosmos: CosmosRow | None = await CosmosRepository(session).get()
    revision = await schema_revision(session)
    if cosmos is None:
        return UniverseFacts(epoch=0, year=0, population=0, sons=0, size_bytes=size_bytes, schema_revision=revision, seed="")
    population = sum(stat(community, "population") or 0 for community in await canon(session, LAND_COMMUNITY_TYPES))
    sons = len(await living_sons(session))
    return UniverseFacts(
        epoch=cosmos.epoch,
        year=cosmos.epoch_start_year,
        population=population,
        sons=sons,
        size_bytes=size_bytes,
        schema_revision=revision,
        seed=" ".join(cosmos.seed_idea.split())[:SEED_SUMMARY_LENGTH],
    )


async def facts_of(database: Database, paths: UniversePaths) -> UniverseFacts:
    size = await asyncio.to_thread(folder_size, paths.root)
    async with database.read() as session:
        return await facts_in(session, size)


async def facts_at(paths: UniversePaths) -> UniverseFacts | None:
    if not paths.database.is_file():
        return None
    database = Database(f"sqlite+aiosqlite:///{paths.database}")
    try:
        return await facts_of(database, paths)
    except Exception:
        logger.warning("the facts of the universe at %s could not be read", paths.root.name, exc_info=True)
        return None
    finally:
        await database.dispose()
