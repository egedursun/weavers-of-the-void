from collections import Counter

from sqlalchemy import select

from aerona.catalog.couplings import CARRION_RESTS, KEEPING_RESTS, WORLD_RESTS
from aerona.catalog.terrain import TERRAIN
from aerona.constants.units import PER_MILLE, PERCENT
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.couplings import CarrionPulseRow
from aerona.db.tables.ecology import SpeciesProfileRow, SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.evolution import EcosystemServiceRow
from aerona.db.tables.fossils import FossilBedRow
from aerona.db.write_guard import held
from aerona.domain.enums.couplings import CarrionRest
from aerona.domain.enums.ecology import Diet
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.environment import ScarKind, TerrainTrait
from aerona.domain.enums.evolution import KeystoneRole
from aerona.domain.enums.fossil import FossilSource
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.models.entity_stats import SpiritStats
from aerona.engine.context import TickContext
from aerona.engine.environment.book import add_scar
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.interconnect.flows import FlowCategory
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int, clamp_percent, round_half_up
from aerona.engine.primitives.queries import canon, top_region
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.stats import set_stats, stat_or
from aerona.engine.recording.record import record

MASS_DEATHS = frozenset(
    category.value for category in (FlowCategory.DEATH, FlowCategory.CASUALTY, FlowCategory.FAMINE, FlowCategory.PLAGUE, FlowCategory.DISASTER)
)


async def dead_by_region(ctx: TickContext) -> Counter[int]:
    dead: Counter[int] = Counter()
    for (_phase, key, node, category), delta in ctx.environment.stats.flows.items():
        if key == "population" and category in MASS_DEATHS and delta < 0:
            dead[node] -= delta
    regions: Counter[int] = Counter()
    for node, count in sorted(dead.items()):
        entity = await ctx.session.get(EntityRow, node)
        region = await top_region(ctx.session, entity) if entity is not None else None
        if region is not None:
            regions[region.id] += count
    return regions


async def living_by_region(ctx: TickContext) -> Counter[int]:
    atlas = await RegionAtlas.load(ctx.session)
    living: Counter[int] = Counter()
    for community in await canon(ctx.session, [EntityType.SETTLEMENT, EntityType.PEOPLE]):
        region_id = atlas.top_region(community.id)
        if region_id is not None:
            living[region_id] += stat_or(community, "population", 0)
    return living


def per_living(per_mille: int, living: int) -> int:
    return max(1, per_mille * living // PER_MILLE)


async def scavenger_ranges(ctx: TickContext, region_id: int) -> list[SpeciesRangeRow]:
    eaters = select(SpeciesProfileRow.species_entity_id).where(SpeciesProfileRow.diet == Diet.SCAVENGER)
    statement = select(SpeciesRangeRow).where(SpeciesRangeRow.region_entity_id == region_id, SpeciesRangeRow.species_entity_id.in_(eaters))
    return list(await ctx.session.scalars(statement.order_by(SpeciesRangeRow.species_entity_id)))


async def feed_scavengers(
    ctx: TickContext, row: CarrionPulseRow, ranges: list[SpeciesRangeRow], ground: RegionEnvironmentRow | None, region: EntityRow
) -> None:
    table = ctx.rules.carrion
    eaten = min(row.carrion, max(1, row.carrion * table.scavenge_pct // PERCENT))
    row.carrion -= eaten
    row.scavenged += eaten
    if "preserved" not in row.locked:
        row.preserved = False
    await settle_rest(ctx, row, region, ground)
    draw = CARRION_RESTS[row.rest].scavenger(ctx.rules)
    for found in ranges:
        if "abundance" not in found.locked and not held(found.species_entity_id):
            found.abundance = clamp_percent(found.abundance + table.scavenger_boom * draw // PERCENT)
    if ground is not None and "disease_load" not in ground.locked:
        ground.disease_load = clamp_percent(ground.disease_load + table.vermin_disease)
    set_stats(region, danger=clamp_percent(stat_or(region, "danger", 0) + table.predators_drawn))


async def settle_rest(ctx: TickContext, row: CarrionPulseRow, region: EntityRow, ground: RegionEnvironmentRow | None, rest: CarrionRest | None = None) -> None:
    if "rest" in row.locked:
        return
    was = row.rest
    row.rest = rest or await rest_of(ctx, region, ground)
    if row.rest is not was and row.carrion > 0:
        await record(ctx, "carrion.laid", roles={IncidentRole.PLACE: region.id}, facts={"rest": row.rest, "dead": row.carrion}, place=region.id)


async def scavenged_by(ctx: TickContext, region_id: int) -> bool:
    statement = select(EcosystemServiceRow.strength).where(
        EcosystemServiceRow.region_entity_id == region_id, EcosystemServiceRow.role == KeystoneRole.SCAVENGER, EcosystemServiceRow.strength > 0
    )
    return await ctx.session.scalar(statement.limit(1)) is not None


async def taken_rest(ctx: TickContext, region: EntityRow, ground: RegionEnvironmentRow | None) -> CarrionRest | None:
    if ground is None:
        return None
    if ground.burned_epoch is not None and ground.burned_epoch >= ctx.epoch:
        return CarrionRest.BURNED
    if TerrainTrait.WATERY in TERRAIN[ground.dominant_terrain].traits:
        return CarrionRest.SUNK
    if await scavenged_by(ctx, region.id) and "disease_load" not in ground.locked:
        ground.disease_load = clamp_int(round_half_up(ground.disease_load * (PERCENT - ctx.rules.carrion.scavenged_disease_cut_pct) / PERCENT), 0, PERCENT)
        return CarrionRest.SCAVENGED
    return None


async def rest_of(ctx: TickContext, region: EntityRow, ground: RegionEnvironmentRow | None) -> CarrionRest:
    table = ctx.rules.carrion
    world = await ctx.session.get(WorldRow, region.world_id) if region.world_id is not None else None
    if world is not None and world.world_type in WORLD_RESTS:
        return WORLD_RESTS[world.world_type]
    taken = await taken_rest(ctx, region, ground)
    if taken is not None:
        return taken
    if ground is not None and abs(ground.latitude) >= table.frozen_latitude:
        return CarrionRest.FROZEN
    if ground is not None and ground.moisture <= table.dry_moisture:
        return CarrionRest.MUMMIFIED
    return CarrionRest.ROTTING


async def lie_unscavenged(ctx: TickContext, row: CarrionPulseRow, ground: RegionEnvironmentRow | None, region: EntityRow) -> None:
    table = ctx.rules.carrion
    await settle_rest(ctx, row, region, ground)
    if "preserved" not in row.locked:
        row.preserved = row.rest in KEEPING_RESTS
    spec = CARRION_RESTS[row.rest]
    if ground is not None and "disease_load" not in ground.locked:
        ground.disease_load = clamp_percent(ground.disease_load + spec.disease(ctx.rules))
    if ground is not None and spec.soil and "soil_fertility" not in ground.locked:
        ground.soil_fertility = clamp_percent(ground.soil_fertility + spec.soil)
    await lay_remains(ctx, row, region)
    if CARRION_RESTS[row.rest].gone:
        row.carrion = 0
    elif row.rest is CarrionRest.FLOATING:
        set_stats(region, danger=clamp_percent(stat_or(region, "danger", 0) + table.floating_hazard))
        if ground is not None:
            add_scar(ground, ScarKind.HAUNTED, table.haunting)


async def lay_remains(ctx: TickContext, row: CarrionPulseRow, region: EntityRow) -> None:
    chance = CARRION_RESTS[row.rest].fossil(ctx.rules)
    if chance <= 0 or not ctx.rng(f"carrion.fossil.{region.id}.{ctx.epoch}").chance(chance):
        return
    laid = await ctx.session.scalar(
        select(FossilBedRow.id).where(FossilBedRow.region_entity_id == region.id, FossilBedRow.source == FossilSource.BURIED_DEAD).limit(1)
    )
    if laid is not None:
        return
    ctx.session.add(
        FossilBedRow(
            region_entity_id=region.id,
            world_id=region.world_id,
            source=FossilSource.BURIED_DEAD,
            richness=ctx.rules.fossils.richness,
            frozen=row.rest is CarrionRest.FROZEN,
            laid_epoch=ctx.epoch,
            locked=[],
        )
    )


UNBURIED = "unburied dead"


async def unburied_of(ctx: TickContext, region_id: int) -> list[EntityRow]:
    query = select(EntityRow).where(
        EntityRow.entity_type == EntityType.SPIRIT,
        EntityRow.status == EntityStatus.CANON,
        EntityRow.location_id == region_id,
        EntityRow.subtype == UNBURIED,
    )
    return list(await ctx.session.scalars(query.order_by(EntityRow.id)))


async def restless(ctx: TickContext, row: CarrionPulseRow, ground: RegionEnvironmentRow | None, region: EntityRow, living: int) -> None:
    table = ctx.rules.carrion
    if ground is not None:
        add_scar(ground, ScarKind.HAUNTED, table.haunting)
    mass = per_living(table.restless_dead, living)
    chance = table.restless_chance * CARRION_RESTS[row.rest].restless(ctx.rules) // PERCENT
    if row.carrion < mass or not ctx.rng(f"carrion.restless.{region.id}.{ctx.epoch}").chance(chance):
        return
    strength = clamp_percent(row.carrion // mass * 10)
    unrest = clamp_percent(table.unburied_unrest_base + row.carrion // mass * table.unburied_unrest_per)
    walking = [spirit for spirit in await unburied_of(ctx, region.id) if not held(spirit.id)]
    if walking:
        spirit = walking[0]
        set_stats(spirit, strength=max(strength, stat_or(spirit, "strength", 0)), unrest=unrest)
        return
    spirit = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.SPIRIT,
            name=f"The Unburied of {region.name}",
            body=f"The restless dead of {region.name}, left where they fell.",
            stats=SpiritStats(strength=strength, unrest=unrest),
            power=2,
            world_id=region.world_id,
            location_id=region.id,
            subtype=UNBURIED,
        ),
    )
    await record(
        ctx, "carrion.restless", roles={IncidentRole.PLACE: region.id, IncidentRole.SUBJECT: spirit.id}, facts={"spirit": str(spirit.name)}, place=region.id
    )


async def settle_unburied(ctx: TickContext, unburied_regions: set[int]) -> int:
    calmer = ctx.rules.carrion.unburied_calm
    settled = 0
    unnamed = select(EntityRow).where(EntityRow.entity_type == EntityType.SPIRIT, EntityRow.subtype.is_(None), EntityRow.description.like("The Unburied of %"))
    for spirit in list(await ctx.session.scalars(unnamed)):
        if not held(spirit.id):
            spirit.subtype = UNBURIED
    query = select(EntityRow).where(EntityRow.entity_type == EntityType.SPIRIT, EntityRow.status == EntityStatus.CANON, EntityRow.subtype == UNBURIED)
    for spirit in list(await ctx.session.scalars(query.order_by(EntityRow.id))):
        if held(spirit.id) or spirit.location_id in unburied_regions:
            continue
        set_stats(spirit, unrest=clamp_percent(stat_or(spirit, "unrest", 0) - calmer))
        settled += 1
    return settled


async def mourn_cost(ctx: TickContext, region_id: int) -> None:
    towns = select(EntityRow).where(EntityRow.location_id == region_id, EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON)
    for town in await ctx.session.scalars(towns.order_by(EntityRow.id)):
        if not held(town.id):
            set_stats(town, prosperity=clamp_percent(stat_or(town, "prosperity", 0) - ctx.rules.carrion.burial_cost))


@reads(
    "people.population",
    "settlement.population",
    "settlement.prosperity",
    "spirit.unrest",
    "table.bonds",
    "table.carrion_pulses",
    "table.creator",
    "table.dimensions",
    "table.ecosystem_services",
    "table.entities",
    "table.foreign_gods",
    "table.fossil_beds",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.incident_participants",
    "table.incidents",
    "table.name_registry",
    "table.node_births",
    "table.nodes",
    "table.region_environment",
    "table.sons",
    "table.species_profiles",
    "table.species_ranges",
    "table.stars",
    "table.state_changes",
    "table.worlds",
)
@writes(
    "settlement.prosperity",
    "spirit.unrest",
    "table.bonds",
    "table.carrion_pulses",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.fossil_beds",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.name_registry",
    "table.node_births",
    "table.region_environment",
    "table.species_ranges",
)
async def carrion(ctx: TickContext) -> None:
    table = ctx.rules.carrion
    rows = {row.region_entity_id: row for row in await ctx.session.scalars(select(CarrionPulseRow))}
    living = await living_by_region(ctx)
    for region_id, dead in sorted((await dead_by_region(ctx)).items()):
        if dead < per_living(table.mass_dead, living[region_id]) or held(region_id):
            continue
        row = rows.get(region_id)
        if row is None:
            row = CarrionPulseRow(
                region_entity_id=region_id, carrion=0, scavenged=0, preserved=False, rest=CarrionRest.ROTTING, kept=False, epoch=ctx.epoch, locked=[]
            )
            ctx.session.add(row)
            rows[region_id] = row
        if "carrion" not in row.locked:
            row.carrion += dead
        row.epoch = ctx.epoch
        ctx.count("carrion_pulses")
    for region_id, row in sorted(rows.items()):
        region = await ctx.session.get(EntityRow, region_id)
        if region is None or region.status is not EntityStatus.CANON or held(region_id) or "carrion" in row.locked:
            continue
        ground = await ctx.session.get(RegionEnvironmentRow, region_id)
        ranges = await scavenger_ranges(ctx, region_id)
        if ranges and row.carrion:
            await feed_scavengers(ctx, row, ranges, ground, region)
        elif row.carrion:
            await lie_unscavenged(ctx, row, ground, region)
        if row.carrion and not row.kept:
            buried = min(row.carrion, table.burial * living[region_id] // PER_MILLE)
            row.carrion -= buried
            await mourn_cost(ctx, region_id)
            if buried > row.carrion:
                await settle_rest(ctx, row, region, ground, CarrionRest.BURIED)
                await lay_remains(ctx, row, region)
        if row.carrion:
            await restless(ctx, row, ground, region, living[region_id])
        if not row.carrion and not row.kept:
            await ctx.session.delete(row)
    still = {region_id for region_id, row in rows.items() if row.carrion >= per_living(table.restless_dead, living[region_id])}
    ctx.count("unburied_settling", await settle_unburied(ctx, still))
    await ctx.session.flush()
