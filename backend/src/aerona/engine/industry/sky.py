from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.industry import RegionPollutionRow
from aerona.db.write_guard import held
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int
from aerona.rules.registry import Rules


async def sky_clear(session: AsyncSession, rules: Rules, community_id: int) -> float:
    region = (await RegionAtlas.load(session)).top_region(community_id)
    row = await session.get(RegionPollutionRow, region) if region is not None else None
    glare = row.light if row is not None else 0
    return 1 - glare * rules.pollution.light_harm / PERCENT / PERCENT


async def irradiate(session: AsyncSession, region_id: int, amount: int, epoch: int) -> int:
    row = await session.get(RegionPollutionRow, region_id)
    if row is None:
        row = RegionPollutionRow(region_node_id=region_id, air=0, water=0, soil=0, polluters={}, epoch=epoch, locked=[])
        session.add(row)
    if "radiation" in row.locked or held(region_id):
        return 0
    before = row.radiation or 0
    row.radiation = clamp_int(before + amount, 0, PERCENT)
    return row.radiation - before
