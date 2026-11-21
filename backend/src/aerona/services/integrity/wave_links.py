from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.sea_waves import SeaWaveCoastRow, SeaWaveRow
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.sea_waves.sea import coasts_of, sea_of


async def stray_coasts(session: AsyncSession) -> list[int]:
    rows = list(await session.scalars(select(SeaWaveCoastRow).order_by(SeaWaveCoastRow.id)))
    if not rows:
        return []
    atlas = await RegionAtlas.load(session)
    shores: dict[int, set[int]] = {}
    found: list[int] = []
    for row in rows:
        wave = await session.get(SeaWaveRow, row.wave_id)
        sea = wave.sea_region_id if wave is not None else None
        if sea is None:
            found.append(row.id)
            continue
        if sea not in shores:
            shores[sea] = set(coasts_of(atlas, sea_of(atlas, sea)))
        if row.region_entity_id not in shores[sea]:
            found.append(row.id)
    return found


async def strike_stray_coast(session: AsyncSession, key: int) -> None:
    row = await session.get(SeaWaveCoastRow, key)
    if row is not None:
        await session.delete(row)
