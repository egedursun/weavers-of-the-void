from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.facets import CAPACITY_FIELDS, FACETS, STAT_CHANNELS, TOWN_FIELDS, FacetEffect, FacetSpec
from aerona.constants.units import PERCENT
from aerona.db.base import Base
from aerona.db.tables.culture import HolderLevelRow, HolderTechniqueRow
from aerona.db.tables.disease import OutbreakRow
from aerona.db.tables.economy import CommunityStockRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.facets import FacetPracticeRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.disease import OutbreakStatus
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.facets import FacetChannel, FacetKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.structure import StructureKind
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import set_stats, stat_or
from aerona.engine.recording.record import record
from aerona.engine.recording.terms import explaining_alone, term

COMMUNITIES = (EntityType.PEOPLE, EntityType.SETTLEMENT)


@dataclass
class FacetTally:
    rooted: int = 0
    faded: int = 0
    shifted: int = 0
    effects: int = 0


@dataclass(frozen=True)
class Sources:
    techniques: Mapping[int, frozenset[Technique]]
    goods: Mapping[int, frozenset[CommodityKind]]
    structures: Mapping[int, frozenset[StructureKind]]
    rows: Mapping[tuple[str, str, str | None, tuple[str, ...]], frozenset[int]]


async def gather_sources(session: AsyncSession) -> Sources:
    techniques: dict[int, set[Technique]] = defaultdict(set)
    for holder, technique in await session.execute(select(HolderTechniqueRow.holder_entity_id, HolderTechniqueRow.technique)):
        techniques[holder].add(technique)
    goods: dict[int, set[CommodityKind]] = defaultdict(set)
    for holder, commodity in await session.execute(
        select(CommunityStockRow.community_entity_id, CommunityStockRow.commodity).where(CommunityStockRow.quantity > 0)
    ):
        goods[holder].add(commodity)
    structures: dict[int, set[StructureKind]] = defaultdict(set)
    placed = select(StructureProfileRow.host_entity_id, StructureProfileRow.kind).where(StructureProfileRow.host_entity_id.is_not(None))
    for host, kind in await session.execute(placed):
        if host is not None:
            structures[host].add(kind)
    rows: dict[tuple[str, str, str | None, tuple[str, ...]], frozenset[int]] = {}
    for spec in FACETS.values():
        for source in spec.rows:
            key = (source.table, source.column, source.field, source.values)
            if key in rows:
                continue
            table = Base.metadata.tables[source.table]
            statement = select(table.c[source.column]).distinct()
            if source.field is not None:
                statement = statement.where(table.c[source.field].in_(list(source.values)))
            rows[key] = frozenset(value for value in await session.scalars(statement) if value is not None)
    return Sources(
        {key: frozenset(value) for key, value in techniques.items()},
        {key: frozenset(value) for key, value in goods.items()},
        {key: frozenset(value) for key, value in structures.items()},
        rows,
    )


def met(spec: FacetSpec, sources: Sources, owners: tuple[int, ...]) -> int:
    known = frozenset().union(*(sources.techniques.get(owner, frozenset()) for owner in owners))
    held_goods = frozenset().union(*(sources.goods.get(owner, frozenset()) for owner in owners))
    built = frozenset().union(*(sources.structures.get(owner, frozenset()) for owner in owners))
    found = 0
    found += 1 if spec.techniques and known.intersection(spec.techniques) else 0
    found += 1 if spec.goods and held_goods.intersection(spec.goods) else 0
    found += 1 if spec.structures and built.intersection(spec.structures) else 0
    rows_met = any(set(owners) & sources.rows.get((source.table, source.column, source.field, source.values), frozenset()) for source in spec.rows)
    found += 1 if spec.rows and rows_met else 0
    return found


def target_of(spec: FacetSpec, sources: Sources, owners: tuple[int, ...]) -> int:
    groups = spec.groups
    return round_half_up(PERCENT * met(spec, sources, owners) / groups) if groups else 0


async def owners_of(session: AsyncSession, community: EntityRow) -> tuple[int, ...]:
    if community.entity_type is EntityType.PEOPLE:
        return (community.id,)
    folk = await people_of(session, community)
    return (community.id, folk.id) if folk is not None else (community.id,)


async def tell(ctx: TickContext, key: str, row: FacetPracticeRow) -> None:
    await record(ctx, key, roles={IncidentRole.SUBJECT: row.community_entity_id}, facts={"facet": row.facet, "level": row.level})


async def shift(ctx: TickContext, row: FacetPracticeRow, target: int, tally: FacetTally) -> None:
    table = ctx.rules.facets
    before = row.level
    step = max(1, round_half_up(abs(target - before) * table.drift_pct / PERCENT)) if target != before else 0
    after = before + step if target > before else before - step
    after = clamp_int(min(after, target) if target > before else max(after, target), 0, PERCENT)
    if after == before:
        return
    with explaining_alone():
        term(f"facets.{row.facet.value}", after - before, source_node_id=row.community_entity_id)
        row.level, row.updated_epoch = after, ctx.epoch
    tally.shifted += 1
    if before < table.rooted_level <= after:
        tally.rooted += 1
        await tell(ctx, "facets.took_root", row)
    elif after <= table.faded_level < before:
        tally.faded += 1
        await tell(ctx, "facets.faded", row)


def amount_of(ctx: TickContext, effect: FacetEffect, level: int) -> int:
    return round_half_up(effect.amount * level * ctx.rules.facets.effect_pct / (PERCENT * PERCENT))


async def touch_town(ctx: TickContext, community: EntityRow, field: str, amount: int) -> bool:
    town = await ctx.session.get(SettlementProfileRow, community.id)
    if town is None or field in (town.locked or []):
        return False
    value = getattr(town, field) + amount
    setattr(town, field, max(0, value) if field in CAPACITY_FIELDS else clamp_int(value, 0, PERCENT))
    return True


def touch_stat(community: EntityRow, key: str, amount: int) -> bool:
    if key not in type(community.stats).model_fields:
        return False
    set_stats(community, **{key: clamp_int(stat_or(community, key, 0) + amount, 0, PERCENT)})
    return True


async def touch_research(ctx: TickContext, community: EntityRow, effect: FacetEffect, amount: int) -> bool:
    level = await ctx.session.get(HolderLevelRow, (community.id, effect.branch)) if effect.branch is not None else None
    if level is None or "progress" in (level.locked or []):
        return False
    level.progress = max(0, level.progress + amount)
    return True


async def touch_disease(ctx: TickContext, community: EntityRow, amount: int, atlas: RegionAtlas) -> bool:
    region = atlas.top_region(community.id)
    if region is None or held(region):
        return False
    touched = False
    active = select(OutbreakRow).where(OutbreakRow.region_entity_id == region, OutbreakRow.status == OutbreakStatus.ACTIVE)
    for outbreak in await ctx.session.scalars(active.order_by(OutbreakRow.id)):
        if "severity" not in (outbreak.locked or []):
            outbreak.severity = clamp_int(outbreak.severity + amount, 0, PERCENT)
            touched = True
    return touched


async def apply_effect(ctx: TickContext, community: EntityRow, effect: FacetEffect, amount: int, atlas: RegionAtlas) -> bool:
    field = TOWN_FIELDS.get(effect.channel)
    if field is not None:
        return await touch_town(ctx, community, field, amount)
    if effect.channel in STAT_CHANNELS:
        return touch_stat(community, effect.channel.value, amount)
    if effect.channel is FacetChannel.RESEARCH:
        return await touch_research(ctx, community, effect, amount)
    return await touch_disease(ctx, community, amount, atlas)


async def act(ctx: TickContext, community: EntityRow, rows: list[FacetPracticeRow], atlas: RegionAtlas, tally: FacetTally) -> None:
    cap = ctx.rules.facets.channel_cap
    pushes: dict[tuple[FacetChannel, KnowledgeBranch | None], int] = defaultdict(int)
    for row in rows:
        for effect in FACETS[row.facet].effects:
            pushes[(effect.channel, effect.branch)] += amount_of(ctx, effect, row.level)
    for (channel, branch), total in sorted(pushes.items(), key=lambda item: (item[0][0].value, item[0][1].value if item[0][1] else "")):
        amount = max(-cap, min(cap, total))
        if amount == 0:
            continue
        with explaining_alone():
            term(f"facets.{channel.value}", amount, source_node_id=community.id)
            if await apply_effect(ctx, community, FacetEffect(channel, amount, branch), amount, atlas):
                tally.effects += 1


async def keep_facets(ctx: TickContext, tally: FacetTally) -> None:
    sources = await gather_sources(ctx.session)
    atlas = await RegionAtlas.load(ctx.session)
    kept: dict[int, dict[FacetKind, FacetPracticeRow]] = defaultdict(dict)
    for row in await ctx.session.scalars(select(FacetPracticeRow).order_by(FacetPracticeRow.id)):
        kept[row.community_entity_id][row.facet] = row
    communities = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type.in_(COMMUNITIES), EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    for community in list(communities):
        if held(community.id):
            continue
        owners = await owners_of(ctx.session, community)
        mine = kept[community.id]
        for facet, spec in FACETS.items():
            target = target_of(spec, sources, owners)
            found = mine.get(facet)
            if found is None and target <= 0:
                continue
            if found is None:
                found = FacetPracticeRow(community_entity_id=community.id, facet=facet, level=0, since_epoch=ctx.epoch, updated_epoch=ctx.epoch, locked=[])
                ctx.session.add(found)
                mine[facet] = found
            if "level" not in (found.locked or []):
                await shift(ctx, found, target, tally)
        await act(ctx, community, [row for row in mine.values() if row.level > 0], atlas, tally)
    await ctx.session.flush()
