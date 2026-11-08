from collections import Counter

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.settlement import DistrictRow, SettlementInfrastructureRow
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.environment import RiverClass
from aerona.domain.enums.settlement import DistrictKind
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.structure import StructureKind
from aerona.engine.context import TickContext
from aerona.engine.environment.book import EnvironmentBook
from aerona.engine.environment.profile import Works
from aerona.engine.lore.research import has_technique
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.queries import canon
from aerona.engine.primitives.words import names_word
from aerona.engine.structures.readers import Working, working
from aerona.rules.registry import Rules

WORKS_FIXUP = "environment.typed_works"
WORK_MAX = 5
BRIDGE_WORDS = ("bridge",)
HARBOUR_WORDS = ("harbour", "harbor", "port", "quay", "dock")


STRUCTURE_WORKS: dict[StructureKind, tuple[str, ...]] = {
    StructureKind.ROAD: ("roads",),
    StructureKind.BRIDGE: ("bridges",),
    StructureKind.HARBOUR: ("harbours",),
    StructureKind.CANAL: ("harbours", "irrigation"),
    StructureKind.IRRIGATION: ("irrigation",),
    StructureKind.DAM: ("irrigation",),
    StructureKind.CARAVANSERAI: (),
    StructureKind.MARKET: (),
}


def waystation_capacity(rules: Rules, item: Working) -> int:
    if item.profile.kind is StructureKind.CARAVANSERAI:
        return round_half_up(rules.structure_functions.caravanserai_capacity * item.profile.level * item.strength)
    if item.profile.kind is StructureKind.MARKET:
        return round_half_up(rules.trade_routes.capacity_per_market * item.strength)
    return 0


async def structure_works(session: AsyncSession, atlas: RegionAtlas, rules: Rules, tallies: dict[int, Counter[str]]) -> None:
    for item in await working(session, list(STRUCTURE_WORKS)):
        region_id = atlas.top_region(item.structure.id)
        if region_id is None:
            continue
        tally = tallies.setdefault(region_id, Counter())
        for key in STRUCTURE_WORKS[item.profile.kind]:
            tally[key] += max(1, round_half_up(item.profile.level * item.strength))
        tally["waystations"] += waystation_capacity(rules, item)


async def region_works(session: AsyncSession, atlas: RegionAtlas, rules: Rules) -> dict[int, Works]:
    knowledge = await KnowledgeMap.load(session)
    infrastructure = {row.settlement_entity_id: row for row in await session.scalars(select(SettlementInfrastructureRow))}
    harboured = set(await session.scalars(select(DistrictRow.settlement_entity_id).where(DistrictRow.kind == DistrictKind.HARBOUR)))
    tallies: dict[int, Counter[str]] = {}
    for entity in await canon(session, [EntityType.SETTLEMENT]):
        region_id = atlas.top_region(entity.id)
        if region_id is None:
            continue
        tally = tallies.setdefault(region_id, Counter())
        works = infrastructure.get(entity.id)
        tally["roads"] += knowledge.knows(entity.id, KnowledgeBranch.ARCHITECTURE)
        harbours = works.harbour_capacity // rules.districts.harbour_works_capacity if works is not None else 0
        tally["harbours"] += max(int(entity.id in harboured or (works is not None and works.harbour_capacity > 0)), harbours)
        if works is not None:
            tally["bridges"] += works.bridges
            tally["irrigation"] += works.irrigation
    await structure_works(session, atlas, rules, tallies)
    return {
        region_id: Works(
            roads=tally["roads"], bridges=tally["bridges"], harbours=tally["harbours"], irrigation=tally["irrigation"], waystations=tally["waystations"]
        )
        for region_id, tally in tallies.items()
    }


async def works_by_region(ctx: TickContext, book: EnvironmentBook) -> dict[int, Works]:
    return await region_works(ctx.session, book.atlas, ctx.rules)


def _named(entity: EntityRow, words: tuple[str, ...]) -> bool:
    text = f"{entity.subtype or ''} {entity.name}".lower()
    return names_word(text, words)


async def _settlement_in(ctx: TickContext, atlas: RegionAtlas, region_id: int) -> EntityRow | None:
    for settlement in await canon(ctx.session, [EntityType.SETTLEMENT]):
        if atlas.top_region(settlement.id) == region_id:
            return settlement
    return None


async def _infrastructure(ctx: TickContext, settlement_id: int) -> SettlementInfrastructureRow:
    row = await ctx.session.get(SettlementInfrastructureRow, settlement_id)
    if row is None:
        row = SettlementInfrastructureRow(settlement_entity_id=settlement_id, locked=[])
        ctx.session.add(row)
        await ctx.session.flush()
    return row


async def backfill_typed_works(ctx: TickContext) -> int:
    if await ctx.session.get(AppliedFixupRow, WORKS_FIXUP) is not None:
        return 0
    atlas = await RegionAtlas.load(ctx.session)
    structures = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.STRUCTURE, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    bridges = harbours = 0
    for structure in list(structures):
        bridge, harbour = _named(structure, BRIDGE_WORDS), _named(structure, HARBOUR_WORDS)
        region_id = atlas.top_region(structure.id) if bridge or harbour else None
        settlement = await _settlement_in(ctx, atlas, region_id) if region_id is not None else None
        if settlement is None:
            continue
        if bridge:
            works = await _infrastructure(ctx, settlement.id)
            works.bridges = min(WORK_MAX, (works.bridges or 0) + 1)
            bridges += 1
        if harbour:
            found = await ctx.session.scalar(
                select(DistrictRow).where(DistrictRow.settlement_entity_id == settlement.id, DistrictRow.kind == DistrictKind.HARBOUR)
            )
            if found is None:
                ctx.session.add(DistrictRow(settlement_entity_id=settlement.id, kind=DistrictKind.HARBOUR, level=1, built_epoch=structure.birth_epoch))
            harbours += 1
    irrigated = await backfill_irrigation(ctx, atlas)
    ctx.session.add(AppliedFixupRow(key=WORKS_FIXUP, result={"bridges": bridges, "harbours": harbours, "irrigation": irrigated}))
    await ctx.session.flush()
    return bridges + harbours + irrigated


async def backfill_irrigation(ctx: TickContext, atlas: RegionAtlas) -> int:
    knowledge = await KnowledgeMap.load(ctx.session)
    grounds = {row.entity_id: row for row in await ctx.session.scalars(select(RegionEnvironmentRow))}
    irrigated = 0
    for settlement in await canon(ctx.session, [EntityType.SETTLEMENT]):
        region_id = atlas.top_region(settlement.id)
        ground = grounds.get(region_id) if region_id is not None else None
        if ground is None or ground.river_class is RiverClass.NONE:
            continue
        skilled = knowledge.level(settlement.id, KnowledgeBranch.AGRICULTURE) >= ctx.rules.environment.irrigation_agriculture_level
        if not skilled and not await has_technique(ctx.session, settlement.id, Technique.IRRIGATION):
            continue
        works = await _infrastructure(ctx, settlement.id)
        if works.irrigation <= 0:
            works.irrigation = 1
            irrigated += 1
    return irrigated
