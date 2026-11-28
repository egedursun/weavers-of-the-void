from sqlalchemy import select

from aerona.db.fixups import fixup_due
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.environment import dangers, hazards, knowledge, memory, perils
from aerona.engine.environment.geology import lay_columns
from aerona.engine.environment.memory_effects import answer_memories
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.standing import ended_ids
from aerona.engine.recording.record import record

BACKFILL_FIXUP = "region.terrain_backfill"
MEMORY_BACKFILL = "land_memory.w52_backfill"


async def _scene(ctx: TickContext) -> dangers.DangerScene:
    atlas = await RegionAtlas.load(ctx.session)
    grounds = {row.entity_id: row for row in await ctx.session.scalars(select(RegionEnvironmentRow).order_by(RegionEnvironmentRow.entity_id))}
    regions = {
        row.id: row
        for row in await ctx.session.scalars(select(EntityRow).where(EntityRow.entity_type == EntityType.REGION, EntityRow.status == EntityStatus.CANON))
    }
    return dangers.DangerScene(atlas, {key: value for key, value in grounds.items() if key in regions}, regions, await memory.memories_by_region(ctx.session))


async def survey_regions(ctx: TickContext) -> dict[str, int]:
    atlas = await RegionAtlas.load(ctx.session)
    backfilled = await fixup_due(ctx.session, BACKFILL_FIXUP)
    ctx.count("columns_laid", await lay_columns(ctx))
    made = await memory.remember(ctx.session, ctx.rules, atlas, 0 if backfilled else ctx.epoch - 1)
    remembered = len(made)
    await answer_memories(ctx, made)
    if await fixup_due(ctx.session, MEMORY_BACKFILL):
        backfill = await memory.remember(ctx.session, ctx.rules, atlas, 0)
        ctx.session.add(AppliedFixupRow(key=MEMORY_BACKFILL, result={"memories": len(backfill)}))
    gone = await memory.fade_memories(ctx.session, ctx.rules, ctx.epoch)
    for region_id, world_id, kind in gone:
        await record(ctx, "memory.faded", roles={IncidentRole.PLACE: region_id}, facts={"memory": kind}, place=region_id, world_id=world_id)
    faded = len(gone)
    scene = await _scene(ctx)
    sacred = await memory.derive_sacredness(ctx.session, ctx.rules, scene.atlas, scene.grounds, scene.memories)
    await dangers.derive(ctx.session, ctx.rules, scene, ctx.epoch)
    written = await dangers.write_dangers(ctx.session, ctx.rules, scene, ctx.epoch)
    charted = await knowledge.chart(ctx.session, ctx.rules, scene.atlas, ctx.epoch)
    result = {"memories": remembered, "faded": faded, "sacred": sacred, "dangers": written, "charted": charted}
    if backfilled:
        ctx.session.add(AppliedFixupRow(key=BACKFILL_FIXUP, result=result))
        await ctx.session.flush()
    return result


@reads(
    "event.severity",
    "region.danger",
    "species.danger",
    "table.applied_fixups",
    "table.battles",
    "table.beast_profiles",
    "table.bonds",
    "table.ceremonial_circuits",
    "table.chronicle",
    "table.claims",
    "table.cosmos",
    "table.dimensional_events",
    "table.dimensions",
    "table.entities",
    "table.entity_flags",
    "table.galactic_structures",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.holder_techniques",
    "table.incident_participants",
    "table.incidents",
    "table.item_profiles",
    "table.memories",
    "table.mind_profiles",
    "table.minds",
    "table.node_births",
    "table.nodes",
    "table.phenomenon_footprints",
    "table.phenomenon_profiles",
    "table.place_environment",
    "table.polity_map_knowledge",
    "table.polity_members",
    "table.polity_profiles",
    "table.polity_territories",
    "table.region_dangers",
    "table.region_environment",
    "table.region_geology",
    "table.region_memories",
    "table.region_underground",
    "table.rifts",
    "table.sediment_flows",
    "table.species_profiles",
    "table.species_ranges",
    "table.species_relations",
    "table.stars",
    "table.trade_route_profiles",
    "table.tradition_participation",
    "table.tradition_profiles",
    "table.traits",
    "table.world_maps",
    "table.world_seasons",
    "table.worlds",
)
@writes(
    "region.danger",
    "table.applied_fixups",
    "table.chronicle",
    "table.chronicle_entities",
    "table.claims",
    "table.entities",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.memories",
    "table.polity_map_knowledge",
    "table.region_dangers",
    "table.region_environment",
    "table.region_geology",
    "table.region_memories",
    "table.region_underground",
)
async def region_survey(ctx: TickContext) -> None:
    for key, value in (await survey_regions(ctx)).items():
        ctx.count(f"region_{key}", value)


@reads(
    "people.population",
    "settlement.population",
    "table.creator",
    "table.deep_passages",
    "table.dimensions",
    "table.entities",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.herds",
    "table.incident_participants",
    "table.incidents",
    "table.maimed_cohorts",
    "table.node_births",
    "table.nodes",
    "table.region_dangers",
    "table.region_environment",
    "table.region_memories",
    "table.sons",
    "table.stars",
    "table.structure_profiles",
    "table.vessel_profiles",
    "table.world_maps",
    "table.worlds",
)
@writes(
    "people.population",
    "settlement.population",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.herds",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.maimed_cohorts",
    "table.node_births",
    "table.region_environment",
    "table.structure_profiles",
)
async def danger_harm(ctx: TickContext) -> None:
    scene = await _scene(ctx)
    gone = set(await ctx.session.scalars(ended_ids()))
    perilous = {
        region: kept
        for region, rows in (await dangers.dangers_by_region(ctx.session)).items()
        if (kept := [row for row in rows if row.source_node_id not in gone])
    }
    tally = await perils.harm_settlers(ctx, scene.atlas, perilous, scene.regions)
    works = await perils.harm_works(ctx, perilous, scene.grounds)
    ctx.count("danger_fields", works.fields)
    ctx.count("danger_buildings", works.buildings)
    ctx.count("danger_vessels", works.vessels)
    ctx.count("danger_dead", tally.dead)
    ctx.count("danger_maimed", tally.maimed)
    ctx.count("danger_livestock", tally.livestock)
    ctx.count("danger_struck", tally.struck)


@reads(
    "army.morale",
    "army.size",
    "cult.zeal",
    "item.protection",
    "mortal.age",
    "mortal.agility",
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
    "spirit.unrest",
    "table.afflictions",
    "table.armies",
    "table.army_officers",
    "table.army_profiles",
    "table.army_units",
    "table.assistive_aids",
    "table.augment_effects",
    "table.augments",
    "table.avatars",
    "table.bodies",
    "table.body_customs",
    "table.bonds",
    "table.calendars",
    "table.charms",
    "table.conditions",
    "table.cosmos",
    "table.creator",
    "table.creature_anatomy",
    "table.crime_cases",
    "table.cult_offices",
    "table.cult_tenets",
    "table.culture_values",
    "table.death_readings",
    "table.deep_passages",
    "table.designated_heirs",
    "table.dimensional_events",
    "table.dimensions",
    "table.divine_wounds",
    "table.doctrine_sacraments",
    "table.entities",
    "table.entity_flags",
    "table.entity_tags",
    "table.forced_weather",
    "table.foreign_gods",
    "table.galactic_structures",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.genomes",
    "table.grave_goods",
    "table.griefs",
    "table.holder_levels",
    "table.incident_facts",
    "table.incident_participants",
    "table.incident_steps",
    "table.incidents",
    "table.incorporeal_rights",
    "table.incubating_ideas",
    "table.injuries",
    "table.insurance_policies",
    "table.insurers",
    "table.irregular_seasons",
    "table.item_profiles",
    "table.kinship_systems",
    "table.language_profiles",
    "table.law_jurisdictions",
    "table.law_profiles",
    "table.legitimacy_rules",
    "table.lexemes",
    "table.marriages",
    "table.memories",
    "table.mind_attributes",
    "table.mind_facets",
    "table.minds",
    "table.mortal_equipment",
    "table.mortal_profiles",
    "table.name_registry",
    "table.natural_law_profiles",
    "table.node_births",
    "table.nodes",
    "table.outbreaks",
    "table.passions",
    "table.people_culture",
    "table.personality_values",
    "table.place_environment",
    "table.polity_members",
    "table.prostheses",
    "table.region_environment",
    "table.region_winds",
    "table.routes",
    "table.sacraments",
    "table.sense_profiles",
    "table.sky_events",
    "table.sons",
    "table.spirit_profiles",
    "table.stars",
    "table.state_changes",
    "table.structure_profiles",
    "table.thoughts",
    "table.tradition_profiles",
    "table.traits",
    "table.transform_prospects",
    "table.war_sides",
    "table.wars",
    "table.wills",
    "table.world_domain_hooks",
    "table.world_maps",
    "table.world_seasons",
    "table.worlds",
)
@writes(
    "army.morale",
    "army.size",
    "mortal.age",
    "mortal.death_year",
    "mortal.hp",
    "mortal.lifespan",
    "people.population",
    "settlement.population",
    "table.army_units",
    "table.bodies",
    "table.body_customs",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_societies",
    "table.community_stocks",
    "table.entities",
    "table.entity_flags",
    "table.goods_flows",
    "table.grave_goods",
    "table.griefs",
    "table.incident_facts",
    "table.incident_participants",
    "table.incident_steps",
    "table.incidents",
    "table.incorporeal_rights",
    "table.injuries",
    "table.item_history",
    "table.marriages",
    "table.memories",
    "table.mind_facets",
    "table.mortal_profiles",
    "table.name_registry",
    "table.node_births",
    "table.personality_values",
    "table.region_environment",
    "table.region_hazards",
    "table.sacraments",
    "table.sons",
    "table.spirit_profiles",
    "table.thoughts",
    "table.transformations",
)
async def terrain_hazards(ctx: TickContext) -> None:
    tally = await hazards.roll_hazards(ctx)
    ctx.count("hazard_strikes", tally.strikes)
    ctx.count("hazard_dead", tally.dead)
    ctx.count("hazard_injured", tally.injured)
    ctx.count("hazard_soldiers", tally.soldiers)


@reads(
    "cult.zeal",
    "people.piety",
    "settlement.piety",
    "settlement.prosperity",
    "table.deep_passages",
    "table.entities",
    "table.nodes",
    "table.region_dangers",
    "table.region_environment",
    "table.region_memories",
    "table.world_maps",
)
@writes("cult.zeal", "people.piety", "settlement.piety", "settlement.prosperity", "table.entities")
async def sacred_pilgrims(ctx: TickContext) -> None:
    scene = await _scene(ctx)
    tally = await perils.draw_pilgrims(ctx, scene.atlas, scene.grounds)
    ctx.count("pilgrim_settlements", tally.settlements)
    ctx.count("pilgrim_communities", tally.communities)
    ctx.count("pilgrim_cults", tally.cults)


PHASES = (
    Phase("region_survey", region_survey),
    Phase("danger_harm", danger_harm),
    Phase("terrain_hazards", terrain_hazards),
    Phase("sacred_pilgrims", sacred_pilgrims),
)
