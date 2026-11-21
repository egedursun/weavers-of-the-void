from dataclasses import dataclass

from sqlalchemy import select

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.military import OccupationRow
from aerona.db.tables.occupation_regimes import OccupationRegimeRow
from aerona.db.tables.polity import PolityMemberRow
from aerona.domain.enums.entity import EntityType
from aerona.engine.context import TickContext
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.queries import living_entity


@dataclass
class RegimeTally:
    founded: int = 0
    rules_set: int = 0
    collaborators: int = 0
    killed: int = 0
    measures: int = 0
    deported: int = 0
    annexed: int = 0
    liberated: int = 0
    settlers: int = 0


async def locals_of(ctx: TickContext, regime: OccupationRegimeRow) -> list[EntityRow]:
    atlas = await RegionAtlas.load(ctx.session)
    found: list[EntityRow] = []
    for community in atlas.communities_in(regime.region_entity_id):
        entity = await living_entity(ctx.session, community)
        if entity is not None and entity.id != regime.occupier_entity_id:
            found.append(entity)
    return found


async def towns_of(ctx: TickContext, regime: OccupationRegimeRow) -> list[EntityRow]:
    return [entity for entity in await locals_of(ctx, regime) if entity.entity_type is EntityType.SETTLEMENT]


async def owner_of(ctx: TickContext, region_id: int, occupier_id: int) -> int | None:
    atlas = await RegionAtlas.load(ctx.session)
    communities = [node for node in atlas.communities_in(region_id) if node != occupier_id]
    if not communities:
        return None
    query = select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id.in_(communities), PolityMemberRow.polity_entity_id != occupier_id)
    return await ctx.session.scalar(query.order_by(PolityMemberRow.polity_entity_id).limit(1))


async def occupation_of(ctx: TickContext, regime: OccupationRegimeRow) -> OccupationRow | None:
    row = await ctx.session.get(OccupationRow, regime.region_entity_id)
    return row if row is not None and row.occupier_entity_id == regime.occupier_entity_id else None
