import json
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.cartography.model import RegionRecord
from aerona.constants.cartography import MAP_REGIONS_PATH
from aerona.db.tables.celestial import WorldMapRow


def decode_regions(raw: Any) -> list[RegionRecord]:
    values = json.loads(raw) if isinstance(raw, str) else raw
    if not isinstance(values, list):
        return []
    return [RegionRecord.model_validate(item) for item in values]


def _regions_column() -> Any:
    return func.json_extract(WorldMapRow.geometry, MAP_REGIONS_PATH)


async def stored_regions(session: AsyncSession) -> dict[int, list[RegionRecord]]:
    rows = await session.execute(select(WorldMapRow.world_id, _regions_column()).order_by(WorldMapRow.world_id))
    return {world_id: decode_regions(raw) for world_id, raw in rows}


async def stored_world_regions(session: AsyncSession, world_id: int) -> list[RegionRecord] | None:
    rows = list(await session.execute(select(_regions_column()).where(WorldMapRow.world_id == world_id)))
    if not rows:
        return None
    return decode_regions(rows[0][0])
