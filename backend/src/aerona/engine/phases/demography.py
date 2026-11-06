from enum import StrEnum

from aerona.catalog.peoples import FUNERAL_DEEDS
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.write_guard import unheld
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.environment import TemperatureBand
from aerona.engine.context import TickContext
from aerona.engine.demography.biology import profiles_of
from aerona.engine.demography.cohorts import rebalance_classes, reconcile, seed
from aerona.engine.demography.labour import allocate
from aerona.engine.demography.martial import BattleTally, backfill_records, earliest_tally, record_battles
from aerona.engine.demography.mobility import class_mobility, desertion, ennoble_heroes, ruin_merchants
from aerona.engine.demography.peoples import (
    biology_for,
    culture_for,
    ensure_profiles,
    homeland_diseases,
    kin_of,
    member_lifespan,
    refresh_biology,
    refresh_culture,
)
from aerona.engine.demography.promotion import doze, promote, sync_maimed, sync_veterans
from aerona.engine.demography.rites import rite_tradition
from aerona.engine.demography.urban import urban_drift
from aerona.engine.disease.emergence import WET
from aerona.engine.disease.harm import community_targets
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.primitives.capacity import LAND_COMMUNITY_TYPES
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.queries import active_bonds, canon
from aerona.engine.primitives.stats import stat

COLD = frozenset({TemperatureBand.FROZEN, TemperatureBand.COLD})


async def region_of(ctx: TickContext, atlas: RegionAtlas, community: EntityRow) -> RegionEnvironmentRow | None:
    region = atlas.top_region(community.id)
    return await ctx.session.get(RegionEnvironmentRow, region) if region is not None else None


@reads(
    "people.population",
    "settlement.population",
    "table.bodies",
    "table.community_cohorts",
    "table.community_societies",
    "table.conditions",
    "table.culture_values",
    "table.disease_profiles",
    "table.entity_flags",
    "table.incident_participants",
    "table.incidents",
    "table.injuries",
    "table.maimed_cohorts",
    "table.memories",
    "table.outbreaks",
    "table.people_biology",
    "table.people_culture",
    "table.region_environment",
    "table.world_maps",
)
@writes(
    "table.bodies",
    "table.community_cohorts",
    "table.conditions",
    "table.entities",
    "table.entity_flags",
    "table.injuries",
    "table.memories",
    "table.people_biology",
    "table.people_culture",
)
async def cohort_upkeep(ctx: TickContext) -> None:
    atlas = await RegionAtlas.load(ctx.session)
    seeded = 0
    for community in unheld(await canon(ctx.session, LAND_COMMUNITY_TYPES)):
        if (stat(community, "population") or 0) <= 0:
            continue
        if community.entity_type is EntityType.PEOPLE:
            await ensure_profiles(ctx.session, ctx.rules, community, await region_of(ctx, atlas, community))
        rows = await seed(ctx.session, ctx.rules, community, ctx.epoch)
        seeded += 1
        await rebalance_classes(ctx.session, ctx.rules, community, rows, ctx.epoch)
        await sync_veterans(ctx, community)
        await sync_maimed(ctx, community)
        await reconcile(ctx.session, ctx.rules, community, rows, ctx.epoch)
    ctx.count("cohorts_kept", seeded)
    ctx.count("promoted", await promote(ctx))
    slept, woke = await doze(ctx)
    ctx.count("dormant", slept)
    ctx.count("woken", woke)
    await ctx.session.flush()


@reads(
    "people.population",
    "settlement.population",
    "table.bonds",
    "table.community_cohorts",
    "table.community_labour",
    "table.community_societies",
    "table.community_stocks",
    "table.corvee_levies",
    "table.disease_profiles",
    "table.labour_reasons",
    "table.market_prices",
    "table.outbreaks",
    "table.people_biology",
    "table.people_culture",
    "table.region_environment",
    "table.resource_profiles",
    "table.resource_workers",
    "table.settlement_profiles",
    "table.workshops",
    "table.world_maps",
)
@writes("table.community_cohorts", "table.community_labour", "table.labour_reasons", "table.settlement_profiles")
async def labour_allocation(ctx: TickContext) -> None:
    atlas = await RegionAtlas.load(ctx.session)
    kept = 0
    for community in unheld(await canon(ctx.session, LAND_COMMUNITY_TYPES)):
        if (stat(community, "population") or 0) <= 0:
            continue
        ground = await region_of(ctx, atlas, community)
        wet_cold = ground is not None and (ground.temperature_band in COLD or ground.wetland >= WET)
        await allocate(ctx, community, ground, wet_cold=wet_cold, targets=await community_targets(ctx.session, community.id, atlas))
        kept += 1
    ctx.count("labour_kept", kept)
    await ctx.session.flush()


@reads(
    "army.experience",
    "army.morale",
    "army.size",
    "people.population",
    "settlement.population",
    "table.armies",
    "table.army_units",
    "table.battles",
    "table.bonds",
    "table.captive_cohorts",
    "table.captives",
    "table.community_cohorts",
    "table.community_societies",
    "table.cult_tenets",
    "table.entities",
    "table.epoch_year_cursors",
    "table.house_members",
    "table.house_profiles",
    "table.loans",
    "table.memories",
    "table.people_culture",
    "table.polity_members",
)
@writes(
    "army.size",
    "people.population",
    "settlement.population",
    "table.army_units",
    "table.bonds",
    "table.captives",
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_cohorts",
    "table.community_societies",
    "table.entities",
    "table.epoch_year_cursors",
    "table.house_members",
    "table.house_profiles",
    "table.incident_participants",
    "table.incidents",
    "table.memories",
    "table.mobility_events",
    "table.name_registry",
    "table.nodes",
    "table.people_culture",
)
async def society_mobility(ctx: TickContext) -> None:
    ctx.count("deserted", await desertion(ctx))
    ctx.count("ennobled", await ennoble_heroes(ctx))
    ctx.count("ruined", await ruin_merchants(ctx))
    for community in await canon(ctx.session, LAND_COMMUNITY_TYPES):
        for key, value in (await class_mobility(ctx, community)).items():
            ctx.count(key, value)
    await ctx.session.flush()


def words(value: StrEnum) -> str:
    return value.value.replace("_", " ")


async def homeland_regions(ctx: TickContext, atlas: RegionAtlas, people: EntityRow) -> list[int]:
    homes = [bond.target_node_id for bond in await active_bonds(ctx.session, [BondKind.LIVES_IN], sources=[people.id])]
    found = {atlas.top_region(people.id), *(atlas.top_region(home) for home in homes)}
    return sorted(region for region in found if region is not None)


async def refresh_people(ctx: TickContext, atlas: RegionAtlas, tally: BattleTally, people: EntityRow) -> None:
    ground = await region_of(ctx, atlas, people)
    biology, culture = await ensure_profiles(ctx.session, ctx.rules, people, ground)
    diseases = await homeland_diseases(ctx.session, await homeland_regions(ctx, atlas, people))
    fresh = biology_for(ctx.rules, people, await member_lifespan(ctx.session, people), ground, kin=await kin_of(ctx.session, people), immunities=diseases)
    refresh_biology(ctx.rules, biology, fresh, ground)
    victor = await record_battles(ctx.session, tally, culture, ctx.epoch)
    style = culture.martial_style
    refresh_culture(ctx.rules, culture, await culture_for(ctx.session, ctx.rules, people, ground), victor)
    if culture.martial_style is not style:
        learned = ", learned from those who beat them" if culture.martial_style is victor else ""
        text = f"The {people.name} gave up fighting as {words(style)} and took up the way of {words(culture.martial_style)}{learned}."
        await note(ctx, text, key="peoples.martial_style", ids=[people.id], kind=ChronicleKind.WAR)
    tradition = await rite_tradition(ctx.session, ctx.rules, people, culture, ctx.epoch)
    if tradition is not None:
        ctx.count("funeral_rites")
        text = f"The {people.name} now {FUNERAL_DEEDS[culture.funeral_rite]}; {tradition.name} began."
        await note(ctx, text, key="peoples.funeral_rite", ids=[people.id, tradition.id], kind=ChronicleKind.LINEAGE)


@reads(
    "people.population",
    "settlement.population",
    "table.applied_fixups",
    "table.battles",
    "table.bodies",
    "table.bonds",
    "table.community_cohorts",
    "table.community_societies",
    "table.cult_doctrines",
    "table.culture_values",
    "table.endemic_diseases",
    "table.entity_traits",
    "table.epoch_year_cursors",
    "table.holder_levels",
    "table.holder_techniques",
    "table.incidents",
    "table.language_profiles",
    "table.language_standing",
    "table.name_registry",
    "table.nodes",
    "table.people_biology",
    "table.people_culture",
    "table.region_environment",
    "table.speaker_cohorts",
    "table.species_profiles",
    "table.world_maps",
)
@writes(
    "people.population",
    "table.applied_fixups",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_cohorts",
    "table.community_societies",
    "table.entities",
    "table.epoch_year_cursors",
    "table.incident_participants",
    "table.incidents",
    "table.name_registry",
    "table.people_biology",
    "table.people_culture",
    "table.tradition_profiles",
)
async def people_cycles(ctx: TickContext) -> None:
    atlas = await RegionAtlas.load(ctx.session)
    ctx.count("profiles_backfilled", await backfill_records(ctx.session))
    tally = await BattleTally.load(ctx.session, await earliest_tally(ctx.session), ctx.epoch)
    for people in unheld(await canon(ctx.session, [EntityType.PEOPLE])):
        await refresh_people(ctx, atlas, tally, people)
    await ctx.session.flush()
    moved = 0
    for community in await canon(ctx.session, LAND_COMMUNITY_TYPES):
        if (stat(community, "population") or 0) <= 0:
            continue
        _, culture = await profiles_of(ctx.session, community)
        moved += abs(await urban_drift(ctx, community, culture))
    ctx.count("urban_drift", moved)
    await ctx.session.flush()


PHASES = (
    Phase("cohort_upkeep", cohort_upkeep),
    Phase("labour_allocation", labour_allocation),
    Phase("society_mobility", society_mobility),
    Phase("people_cycles", people_cycles),
)
