from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.session import Database
from aerona.media.file_store import FileMediaStore
from aerona.rules.registry import Rules
from aerona.services.divine_will.index import LoreIndex

FOLDER = "will-media"


def media_beside(database_file: str | None) -> FileMediaStore:
    return FileMediaStore(Path(str(database_file)).parent / FOLDER)


def harness_media(database: Database) -> FileMediaStore:
    return media_beside(database.engine.url.database)


def session_media(session: AsyncSession) -> FileMediaStore:
    bind = session.bind
    assert bind is not None
    return media_beside(bind.engine.url.database)


def harness_index(database: Database) -> LoreIndex:
    return LoreIndex(database, Rules, media=harness_media(database))
