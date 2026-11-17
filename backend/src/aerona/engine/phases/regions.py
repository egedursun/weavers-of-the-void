from sqlalchemy import select

from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.engine.context import TickContext
from aerona.engine.environment import dangers, hazards, knowledge, memory, perils
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.primitives.distance import RegionAtlas

BACKFILL_FIXUP = "region.terrain_backfill"


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
    backfilled = await ctx.session.get(AppliedFixupRow, BACKFILL_FIXUP) is None
    remembered = await memory.remember(ctx.session, ctx.rules, atlas, 0 if backfilled else ctx.epoch - 1)
    faded = await memory.fade_memories(ctx.session, ctx.rules, ctx.epoch)
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
    "table.cosmos",
    "table.dimensional_events",
    "table.dimensions",
    "table.entities",
    "table.entity_flags",
    "table.galactic_structures",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.holder_techniques",
    "table.incidents",
    "table.item_profiles",
    "table.nodes",
    "table.phenomenon_footprints",
    "table.phenomenon_profiles",
    "table.place_environment",
    "table.polity_map_knowledge",
    "table.polity_members",
    "table.polity_territories",
    "table.region_dangers",
    "table.region_environment",
    "table.region_memories",
    "table.rifts",
    "table.species_profiles",
    "table.species_ranges",
    "table.species_relations",
    "table.stars",
    "table.trade_route_profiles",
    "table.tradition_participation",
    "table.tradition_profiles",
    "table.world_maps",
    "table.worlds",
)
@writes(
    "region.danger",
    "table.applied_fixups",
    "table.entities",
    "table.polity_map_knowledge",
    "table.region_dangers",
    "table.region_environment",
    "table.region_memories",
)
async def region_survey(ctx: TickContext) -> None:
    for key, value in (await survey_regions(ctx)).items():
        ctx.count(f"region_{key}", value)


@reads(
    "people.population",
    "settlement.population",
    "table.entities",
    "table.herds",
    "table.incident_participants",
    "table.incidents",
    "table.maimed_cohorts",
    "table.nodes",
    "table.region_dangers",
    "table.region_environment",
    "table.region_memories",
    "table.world_maps",
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
)
async def danger_harm(ctx: TickContext) -> None:
    scene = await _scene(ctx)
    tally = await perils.harm_settlers(ctx, scene.atlas, await dangers.dangers_by_region(ctx.session), scene.regions)
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
    "table.creature_anatomy",
    "table.crime_cases",
    "table.cult_offices",
    "table.cult_tenets",
    "table.culture_values",
    "table.designated_heirs",
    "table.divine_wounds",
    "table.entities",
    "table.entity_flags",
    "table.entity_tags",
    "table.forced_weather",
    "table.foreign_gods",
    "table.genomes",
    "table.holder_levels",
    "table.incident_participants",
    "table.incidents",
    "table.incorporeal_rights",
    "table.incubating_ideas",
    "table.injuries",
    "table.insurance_policies",
    "table.insurers",
    "table.item_profiles",
    "table.language_profiles",
    "table.law_jurisdictions",
    "table.lexemes",
    "table.marriages",
    "table.memories",
    "table.mind_attributes",
    "table.minds",
    "table.mortal_equipment",
    "table.mortal_profiles",
    "table.name_registry",
    "table.nodes",
    "table.outbreaks",
    "table.passions",
    "table.people_culture",
    "table.place_environment",
    "table.polity_members",
    "table.prostheses",
    "table.region_environment",
    "table.region_winds",
    "table.routes",
    "table.sacraments",
    "table.sky_events",
    "table.sons",
    "table.spirit_profiles",
    "table.stars",
    "table.tradition_profiles",
    "table.traits",
    "table.transform_prospects",
    "table.world_domain_hooks",
    "table.world_maps",
    "table.world_seasons",
    "table.worlds",
)
@writes(
    "army.morale",
    "army.size",
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
    "table.entities",
    "table.entity_flags",
    "table.incident_facts",
    "table.incident_participants",
    "table.incident_steps",
    "table.incidents",
    "table.injuries",
    "table.memories",
    "table.mortal_profiles",
    "table.name_registry",
    "table.region_environment",
    "table.region_hazards",
    "table.sacraments",
    "table.sons",
    "table.spirit_profiles",
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
    "table.entities",
    "table.nodes",
    "table.region_environment",
    "table.region_memories",
    "table.world_maps",
)
@writes("cult.zeal", "people.piety", "settlement.piety", "settlement.prosperity")
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
