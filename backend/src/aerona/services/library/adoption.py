import asyncio
import json
import logging
import os
import re
import sqlite3
from pathlib import Path

from aerona.constants.app import APP_VERSION
from aerona.constants.library import ADOPTED_UNIVERSE_NAME, UNIVERSE_ID_PATTERN
from aerona.domain.enums.library import LibraryEventKind, UniverseOrigin
from aerona.paths import ProcessPaths, UniversePaths
from aerona.services.library.catalogue import Catalogue, NewUniverse, UniverseRecord, new_universe_id
from aerona.services.library.facts import facts_at, schema_revision_at
from aerona.services.library.manifest import read_manifest

logger = logging.getLogger(__name__)

MARKER_KEY = "universe_id"
COSMOS_NAME_QUERY = "SELECT name FROM cosmos LIMIT 1"
ADOPTED_NOTE = "Moved from the single-universe layout of an earlier edition."
RECOVERED_NOTE = "Found on the shelf without a catalogue entry."
UNIVERSE_ID = re.compile(UNIVERSE_ID_PATTERN)


def pending_adoption(process: ProcessPaths) -> str | None:
    marker = process.adoption_marker
    if not marker.is_file():
        return None
    try:
        found = json.loads(marker.read_text(encoding="utf-8")).get(MARKER_KEY)
    except (OSError, ValueError, AttributeError):
        return None
    return found if isinstance(found, str) and UNIVERSE_ID.match(found) else None


def mark_adoption(process: ProcessPaths, universe_id: str) -> None:
    partial = process.adoption_marker.with_suffix(".partial")
    partial.write_text(json.dumps({MARKER_KEY: universe_id}), encoding="utf-8")
    os.replace(partial, process.adoption_marker)


def move_owned(legacy: UniversePaths, target: UniversePaths) -> list[str]:
    target.root.mkdir(parents=True, exist_ok=True)
    moved: list[str] = []
    for source in legacy.owned():
        if not source.exists():
            continue
        destination = target.root / source.name
        if destination.exists():
            logger.warning("adoption left %s in place because the universe folder already holds one", source.name)
            continue
        os.replace(source, destination)
        moved.append(source.name)
    return moved


def cosmos_name(database: Path) -> str:
    if not database.is_file():
        return ""
    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    try:
        found = connection.execute(COSMOS_NAME_QUERY).fetchone()
    except sqlite3.Error:
        return ""
    finally:
        connection.close()
    return str(found[0]).strip() if found and found[0] else ""


async def enter_catalogue(catalogue: Catalogue, universe_id: str, origin_note: str) -> UniverseRecord:
    paths = catalogue.paths.universe(universe_id)
    name = await asyncio.to_thread(cosmos_name, paths.database) or ADOPTED_UNIVERSE_NAME
    record = await catalogue.add(
        universe_id,
        NewUniverse(
            name=await catalogue.free_name(name),
            origin=UniverseOrigin.ADOPTED,
            media_prefix="",
            app_version=APP_VERSION,
            schema_revision=await schema_revision_at(paths),
            origin_note=origin_note,
        ),
    )
    await catalogue.log(LibraryEventKind.ADOPTED, universe_id, record.name, origin_note)
    facts = await facts_at(paths)
    if facts is not None:
        return await catalogue.store_facts(universe_id, facts) or record
    return record


async def adopt_old_layout(catalogue: Catalogue) -> str | None:
    process = catalogue.paths
    legacy = process.legacy
    universe_id = pending_adoption(process)
    if universe_id is None:
        if process.library_database.is_file() or not legacy.database.is_file():
            await catalogue.open()
            return None
        universe_id = new_universe_id()
        await asyncio.to_thread(mark_adoption, process, universe_id)
    await catalogue.open()
    moved = await asyncio.to_thread(move_owned, legacy, process.universe(universe_id))
    if await catalogue.get(universe_id) is None:
        await enter_catalogue(catalogue, universe_id, ADOPTED_NOTE)
    process.adoption_marker.unlink(missing_ok=True)
    logger.info("the single universe of %s was adopted into the library as %s (%s)", process.root.name, universe_id, ", ".join(moved) or "nothing left to move")
    return universe_id


async def shelve_strays(catalogue: Catalogue) -> list[str]:
    folders = catalogue.paths.universes
    if not folders.is_dir():
        return []
    known = {record.id for record in await catalogue.every()}
    shelved: list[str] = []
    for folder in sorted(folders.iterdir()):
        if not folder.is_dir() or folder.name in known or not UNIVERSE_ID.match(folder.name):
            continue
        paths = UniversePaths(folder)
        if not paths.database.is_file():
            continue
        manifest = read_manifest(paths.manifest)
        if manifest is not None and manifest.id == folder.name:
            record = await catalogue.restore_row(manifest)
            await catalogue.log(LibraryEventKind.ADOPTED, record.id, record.name, RECOVERED_NOTE)
        else:
            await enter_catalogue(catalogue, folder.name, RECOVERED_NOTE)
        shelved.append(folder.name)
    return shelved


async def prepare_library(catalogue: Catalogue) -> str | None:
    adopted = await adopt_old_layout(catalogue)
    await shelve_strays(catalogue)
    return adopted
