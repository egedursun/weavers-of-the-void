import json
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.cartography.model import RegionRecord
from aerona.constants.cartography import MAP_REGIONS_PATH
from aerona.db.tables.celestial import WorldMapRow

DECODED: dict[str, list[RegionRecord]] = {}
DECODED_CAP = 64


def _decode(values: Any) -> list[RegionRecord]:
    if not isinstance(values, list):
        return []
    return [RegionRecord.model_validate(item) for item in values]


def decode_regions(raw: Any) -> list[RegionRecord]:
    if not isinstance(raw, str):
        return _decode(raw)
    found = DECODED.get(raw)
    if found is None:
        if len(DECODED) >= DECODED_CAP:
            DECODED.clear()
        found = DECODED[raw] = _decode(json.loads(raw))
    return list(found)


def _regions_column() -> Any:
    return func.json_extract(WorldMapRow.geometry, MAP_REGIONS_PATH)


STORED: dict[tuple[str, int], tuple[tuple[Any, ...], list[RegionRecord]]] = {}
VERSION_COLUMNS = (WorldMapRow.signature, WorldMapRow.epoch, WorldMapRow.generator_version, WorldMapRow.updated_at)


async def stored_regions(session: AsyncSession) -> dict[int, list[RegionRecord]]:
    database = str(session.sync_session.get_bind().engine.url)
    versions = {row[0]: tuple(row[1:]) for row in await session.execute(select(WorldMapRow.world_id, *VERSION_COLUMNS).order_by(WorldMapRow.world_id))}
    stale = [world_id for world_id, version in versions.items() if STORED.get((database, world_id), ((), []))[0] != version]
    if stale:
        rows = await session.execute(select(WorldMapRow.world_id, *VERSION_COLUMNS, _regions_column()).where(WorldMapRow.world_id.in_(stale)))
        for row in rows:
            STORED[(database, row[0])] = (tuple(row[1:-1]), decode_regions(row[-1]))
    return {world_id: list(STORED[(database, world_id)][1]) for world_id in versions}


async def stored_world_regions(session: AsyncSession, world_id: int) -> list[RegionRecord] | None:
    rows = list(await session.execute(select(_regions_column()).where(WorldMapRow.world_id == world_id)))
    if not rows:
        return None
    return decode_regions(rows[0][0])
