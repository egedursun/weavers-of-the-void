from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.write_guard import unheld
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.environment import TemperatureBand
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.demography.biology import profiles_of
from aerona.engine.demography.care import tend_conditions
from aerona.engine.demography.cohorts import rebalance_classes, reconcile, seed
from aerona.engine.demography.labour import allocate
from aerona.engine.demography.martial import BattleTally, backfill_records, earliest_tally, record_battles
from aerona.engine.demography.mobility import class_mobility, desertion, ennoble_heroes, ruin_merchants, shift_classes
from aerona.engine.demography.peoples import (
    biology_for,
    culture_for,
    drift_union,
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
from aerona.engine.phase import Phase
from aerona.engine.primitives.capacity import LAND_COMMUNITY_TYPES
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.queries import active_bonds, canon
from aerona.engine.primitives.stats import stat
from aerona.engine.recording.record import record as record_incident

COLD = frozenset({TemperatureBand.FROZEN, TemperatureBand.COLD})


async def region_of(ctx: TickContext, atlas: RegionAtlas, community: EntityRow) -> RegionEnvironmentRow | None:
    region = atlas.top_region(community.id)
    return await ctx.session.get(RegionEnvironmentRow, region) if region is not None else None


@reads(
    "mortal.age",
    "mortal.agility",
    "mortal.beauty",
    "mortal.charisma",
    "mortal.creativity",
    "mortal.endurance",
    "mortal.hp",
    "mortal.intellect",
    "mortal.lifespan",
    "mortal.perception",
    "mortal.strength",
    "mortal.willpower",
    "mortal.wisdom",
    "people.population",
    "settlement.population",
    "table.allele_pools",
    "table.assistive_aids",
    "table.augment_effects",
    "table.augments",
    "table.bodies",
    "table.body_customs",
    "table.bonds",
    "table.community_cohorts",
    "table.community_societies",
    "table.conditions",
    "table.cult_tenets",
    "table.culture_values",
    "table.deep_passages",
    "table.disease_profiles",
    "table.entities",
    "table.entity_flags",
    "table.genomes",
    "table.holder_levels",
    "table.incident_participants",
    "table.incidents",
    "table.incubating_ideas",
    "table.injuries",
    "table.item_profiles",
    "table.language_profiles",
    "table.lexemes",
    "table.maimed_cohorts",
    "table.memories",
    "table.mind_attributes",
    "table.mind_facets",
    "table.mind_profiles",
    "table.minds",
    "table.mortal_equipment",
    "table.mortal_profiles",
    "table.name_registry",
    "table.node_births",
    "table.nodes",
    "table.outbreaks",
    "table.people_biology",
    "table.people_culture",
    "table.people_reproduction",
    "table.prostheses",
    "table.region_environment",
    "table.role_norms",
    "table.sense_profiles",
    "table.species_profiles",
    "table.state_changes",
    "table.thoughts",
    "table.tradition_profiles",
    "table.traits",
    "table.union_customs",
    "table.world_maps",
)
@writes(
    "mortal.agility",
    "mortal.charisma",
    "mortal.hp",
    "mortal.intellect",
    "mortal.lifespan",
    "mortal.strength",
    "table.bodies",
    "table.body_customs",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_cohorts",
    "table.conditions",
    "table.entities",
    "table.entity_flags",
    "table.genomes",
    "table.incident_facts",
    "table.incident_participants",
    "table.incident_steps",
    "table.incidents",
    "table.injuries",
    "table.memories",
    "table.mortal_profiles",
    "table.name_registry",
    "table.node_births",
    "table.people_biology",
    "table.people_culture",
    "table.settlement_profiles",
    "table.thoughts",
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
        await tend_conditions(ctx, community, rows)
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
    "table.entities",
    "table.faction_profiles",
    "table.holder_levels",
    "table.labour_disputes",
    "table.labour_reasons",
    "table.law_jurisdictions",
    "table.law_profiles",
    "table.market_prices",
    "table.nodes",
    "table.outbreaks",
    "table.people_biology",
    "table.people_culture",
    "table.people_reproduction",
    "table.polity_members",
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
    "table.deep_passages",
    "table.entities",
    "table.house_members",
    "table.house_profiles",
    "table.loans",
    "table.memories",
    "table.name_registry",
    "table.node_births",
    "table.nodes",
    "table.offices",
    "table.outlaws",
    "table.people_culture",
    "table.polity_members",
    "table.polity_profiles",
    "table.polity_territories",
    "table.state_changes",
    "table.vassalages",
    "table.war_sides",
    "table.wars",
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
    "table.house_members",
    "table.house_profiles",
    "table.incident_facts",
    "table.incident_participants",
    "table.incident_terms",
    "table.incidents",
    "table.memories",
    "table.mobility_events",
    "table.name_registry",
    "table.node_births",
    "table.nodes",
    "table.people_culture",
)
async def society_mobility(ctx: TickContext) -> None:
    ctx.count("deserted", await desertion(ctx))
    ctx.count("ennobled", await ennoble_heroes(ctx))
    ctx.count("ruined", await ruin_merchants(ctx))
    ctx.count("classes_shifted", await shift_classes(ctx))
    for community in await canon(ctx.session, LAND_COMMUNITY_TYPES):
        for key, value in (await class_mobility(ctx, community)).items():
            ctx.count(key, value)
    await ctx.session.flush()


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
    await drift_union(ctx.session, people)
    if culture.martial_style is not style:
        await record_incident(
            ctx,
            "peoples.martial_style",
            roles={IncidentRole.SUBJECT: people.id},
            facts={"before": style, "after": culture.martial_style, "learned": int(culture.martial_style is victor)},
        )
    tradition = await rite_tradition(ctx.session, ctx.rules, people, culture, ctx.epoch)
    if tradition is not None:
        ctx.count("funeral_rites")
        await record_incident(
            ctx, "peoples.funeral_rite", roles={IncidentRole.SUBJECT: people.id, IncidentRole.PRODUCT: tradition.id}, facts={"rite": culture.funeral_rite}
        )


@reads(
    "people.population",
    "settlement.population",
    "table.applied_fixups",
    "table.battles",
    "table.bodies",
    "table.bonds",
    "table.community_cohorts",
    "table.community_societies",
    "table.creator",
    "table.cult_doctrines",
    "table.culture_values",
    "table.deep_passages",
    "table.dimensions",
    "table.endemic_diseases",
    "table.entities",
    "table.entity_traits",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.holder_levels",
    "table.holder_techniques",
    "table.incident_participants",
    "table.incidents",
    "table.language_profiles",
    "table.language_standing",
    "table.name_registry",
    "table.node_births",
    "table.nodes",
    "table.people_biology",
    "table.people_culture",
    "table.region_environment",
    "table.sons",
    "table.speaker_cohorts",
    "table.species_profiles",
    "table.stars",
    "table.state_changes",
    "table.world_biochemistries",
    "table.world_maps",
    "table.world_physics",
    "table.worlds",
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
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.name_registry",
    "table.node_births",
    "table.people_biology",
    "table.people_culture",
    "table.tradition_profiles",
    "table.union_customs",
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
