from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.dangers import DANGERS
from aerona.constants.units import PERCENT
from aerona.db.tables.ecology import HerdRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.military import ArmyUnitRow
from aerona.db.tables.region import RegionDangerRow, RegionMemoryRow
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.region import DangerHarm, DangerSource
from aerona.engine.body.cohorts import cohort
from aerona.engine.context import TickContext
from aerona.engine.environment.dangers import harm_weight, weighted
from aerona.engine.environment.knowledge import knowledge_of, polity_of
from aerona.engine.environment.memory import darkness
from aerona.engine.interconnect.flows import FlowCategory, flowing
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.prosperity import add_prosperity
from aerona.engine.primitives.stats import has_stat, set_stats, shift_stat, stat
from aerona.rules.registry import Rules

MAIMING_SOURCES = frozenset({DangerSource.BEASTS, DangerSource.MONSTERS})


@dataclass
class HarmTally:
    dead: int = 0
    maimed: int = 0
    livestock: int = 0
    struck: int = 0


def worst(rules: Rules, rows: list[RegionDangerRow], harm: DangerHarm) -> RegionDangerRow | None:
    scored = [(row.strength * harm_weight(rules, row.source, harm), row.id, row) for row in rows if row.strength > 0]
    return max(scored, key=lambda item: (item[0], -item[1]))[2] if scored else None


def settler_loss(rules: Rules, population: int, harm: int) -> int:
    table = rules.regional_danger
    share = min(harm * table.settlers_loss_pct / PERCENT, table.settlers_loss_cap_pct) / PERCENT
    return min(population, round_half_up(population * share))


async def strike_community(ctx: TickContext, community: EntityRow, region: EntityRow, rows: list[RegionDangerRow], tally: HarmTally) -> None:
    rules = ctx.rules
    table = rules.regional_danger
    population = round(stat(community, "population") or 0)
    lost = settler_loss(rules, population, weighted(rules, rows, DangerHarm.SETTLERS))
    if lost > 0:
        with flowing(FlowCategory.DISASTER):
            set_stats(community, population=max(0, population - lost))
        maiming = sum(row.strength for row in rows if row.source in MAIMING_SOURCES)
        whole = sum(row.strength for row in rows) or 1
        maimed = round_half_up(lost * table.settlers_maimed_pct / PERCENT * maiming / whole)
        source = worst(rules, rows, DangerHarm.SETTLERS)
        spec = DANGERS[source.source] if source is not None else None
        if maimed > 0 and spec is not None and spec.maimed is not None:
            row = await cohort(ctx, community.id, spec.maimed)
            row.count += maimed
            row.updated_epoch = ctx.epoch
            tally.maimed += maimed
        tally.dead += lost
        tally.struck += 1
        if spec is not None and source is not None and lost >= table.settlers_noted_deaths:
            ids = [community.id, region.id, *([source.source_node_id] if source.source_node_id is not None else [])]
            roles = {community.id: IncidentRole.TARGET, **({source.source_node_id: IncidentRole.ACTOR} if source.source_node_id is not None else {})}
            await ctx.chronicle(
                ChronicleKind.WORLD,
                spec.settlers_line.format(count=lost, community=community.name, region=region.name) + ".",
                template_key=f"danger.{source.source.value}",
                entity_ids=ids,
                world_id=community.world_id,
                place_entity_id=region.id,
                magnitude=clamp_int(lost, 0, PERCENT),
                roles=roles,
            )
    livestock = weighted(rules, rows, DangerHarm.LIVESTOCK)
    if livestock <= 0:
        return
    for herd in await ctx.session.scalars(select(HerdRow).where(HerdRow.community_entity_id == community.id).order_by(HerdRow.species_entity_id)):
        if "head" in herd.locked or herd.head <= 0:
            continue
        taken = round_half_up(herd.head * livestock * table.livestock_loss_pct / PERCENT / PERCENT)
        herd.head = max(0, herd.head - taken)
        tally.livestock += taken


async def harm_settlers(ctx: TickContext, atlas: RegionAtlas, dangers: dict[int, list[RegionDangerRow]], regions: dict[int, EntityRow]) -> HarmTally:
    tally = HarmTally()
    communities = await ctx.session.scalars(
        select(EntityRow)
        .where(EntityRow.entity_type.in_([EntityType.SETTLEMENT, EntityType.PEOPLE]), EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    for community in list(communities):
        region_id = atlas.top_region(community.id)
        rows = dangers.get(region_id or 0, [])
        region = regions.get(region_id or 0)
        if not rows or region is None:
            continue
        await strike_community(ctx, community, region, rows, tally)
    return tally


@dataclass(frozen=True)
class Peril:
    dead: int
    ambushed: bool


async def danger_toll(ctx: TickContext, army: EntityRow, rows: list[ArmyUnitRow], region_id: int | None) -> Peril:
    table = ctx.rules.regional_danger
    dangers = list(await ctx.session.scalars(select(RegionDangerRow).where(RegionDangerRow.region_entity_id == region_id))) if region_id is not None else []
    if not dangers:
        return Peril(0, False)
    size = stat(army, "size") or 0
    dead = round_half_up(size * weighted(ctx.rules, dangers, DangerHarm.ARMIES) * table.army_attrition_pct / PERCENT / PERCENT)
    chance = weighted(ctx.rules, dangers, DangerHarm.AMBUSH) * table.ambush_chance_pct / PERCENT
    ambushed = ctx.rng(f"ambush.{army.id}.{region_id}").chance(chance)
    if ambushed:
        dead += round_half_up(size * table.ambush_loss_pct / PERCENT)
        for row in rows:
            row.morale = clamp_int(row.morale - table.ambush_morale, 0, PERCENT)
        ctx.count("danger_ambushes")
    return Peril(dead, ambushed)


@dataclass(frozen=True)
class Wandering:
    lost: bool
    dead: int


async def navigate(ctx: TickContext, army: EntityRow, owner: EntityRow, region_id: int | None, origin: int | None, *, charted: bool) -> Wandering:
    table = ctx.rules.terrain
    if charted or region_id is None or region_id == origin:
        return Wandering(False, 0)
    polity_id = await polity_of(ctx.session, owner.id)
    known = await knowledge_of(ctx.session, polity_id, region_id)
    if known is None or known >= table.unmapped_below:
        return Wandering(False, 0)
    if not ctx.rng(f"lost.{army.id}.{region_id}").chance(table.lost_chance_pct):
        return Wandering(False, 0)
    ctx.count("armies_lost_way")
    return Wandering(True, round_half_up((stat(army, "size") or 0) * table.lost_attrition_pct / PERCENT))


async def haunt_factor(session: AsyncSession, rules: Rules, region_id: int | None) -> float:
    if region_id is None:
        return 1.0
    table = rules.terrain
    memories = list(await session.scalars(select(RegionMemoryRow).where(RegionMemoryRow.region_entity_id == region_id)))
    ground = await session.get(RegionEnvironmentRow, region_id)
    sacred = ground.sacredness if ground is not None else 0
    dark = darkness(rules, memories)
    return (1 + dark * table.haunt_darkness_pct / PERCENT / PERCENT) * max(0.0, 1 - sacred * table.haunt_sacred_pct / PERCENT / PERCENT)


@dataclass
class PilgrimTally:
    settlements: int = 0
    communities: int = 0
    cults: int = 0


async def draw_pilgrims(ctx: TickContext, atlas: RegionAtlas, grounds: dict[int, RegionEnvironmentRow]) -> PilgrimTally:
    table = ctx.rules.terrain
    tally = PilgrimTally()
    holy = {region_id: ground.sacredness for region_id, ground in grounds.items() if ground.sacredness >= table.pilgrim_sacred_min}
    if not holy:
        return tally
    entities = await ctx.session.scalars(
        select(EntityRow)
        .where(EntityRow.entity_type.in_([EntityType.SETTLEMENT, EntityType.PEOPLE, EntityType.CULT]), EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    for entity in list(entities):
        sacred = holy.get(atlas.top_region(entity.id) or 0)
        if sacred is None:
            continue
        share = sacred / PERCENT
        if entity.entity_type is EntityType.CULT:
            if has_stat(entity, "zeal"):
                shift_stat(entity, "zeal", round_half_up(table.pilgrim_zeal * share))
                tally.cults += 1
            continue
        if entity.entity_type is EntityType.SETTLEMENT and add_prosperity(ctx.rules, entity, table.pilgrim_prosperity * share) is not None:
            tally.settlements += 1
        if has_stat(entity, "piety"):
            shift_stat(entity, "piety", round_half_up(table.pilgrim_piety * share))
            tally.communities += 1
    return tally
