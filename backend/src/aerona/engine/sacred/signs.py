from sqlalchemy import select

from aerona.db.tables.celestial import SkyEventRow
from aerona.db.tables.dominion import DominionRow, MiracleRecordRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.warfare import BattleRow
from aerona.domain.enums.entity import EntityType
from aerona.engine.context import TickContext
from aerona.engine.phases.native_faith import struck_places
from aerona.engine.sacred.places import region_of


async def struck_regions(ctx: TickContext) -> set[int]:
    regions: set[int] = set()
    for place_id in await struck_places(ctx.session, ctx.epoch):
        place = await ctx.session.get(EntityRow, place_id)
        region = await region_of(ctx.session, place) if place is not None else None
        if region is not None:
            regions.add(region.id)
    return regions


async def defeated_realms(ctx: TickContext) -> set[int]:
    losers = {item for item in await ctx.session.scalars(select(BattleRow.loser_entity_id).where(BattleRow.epoch == ctx.epoch)) if item is not None}
    realms: set[int] = set()
    for loser in losers:
        entity = await ctx.session.get(EntityRow, loser)
        if entity is None:
            continue
        if entity.entity_type is EntityType.POLITY:
            realms.add(entity.id)
        elif entity.affiliated_entity_id is not None:
            realms.add(entity.affiliated_entity_id)
    return realms


async def omen_worlds(ctx: TickContext) -> set[int]:
    return {item for item in await ctx.session.scalars(select(SkyEventRow.world_id).where(SkyEventRow.epoch == ctx.epoch)) if item is not None}


async def miracles_by_region(ctx: TickContext, since: int) -> dict[int, set[int]]:
    found: dict[int, set[int]] = {}
    rows = await ctx.session.execute(select(MiracleRecordRow.region_entity_id, MiracleRecordRow.god_node_id).where(MiracleRecordRow.epoch >= since))
    for region, god in rows:
        if region is not None:
            found.setdefault(region, set()).add(god)
    return found


async def dominion_over(ctx: TickContext, region_id: int) -> int:
    found = await ctx.session.scalars(select(DominionRow.strength).where(DominionRow.region_entity_id == region_id))
    return max(list(found), default=0)
