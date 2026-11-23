from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.storyteller import RecoveryKind, TensionBand
from aerona.engine.context import TickContext
from aerona.engine.gatherings.hold import GatheringTally, gather_all
from aerona.engine.gatherings.occasions import occasions
from aerona.engine.gatherings.wider_occasions import wider_occasions
from aerona.engine.history.collections import CollectionTally, close_quiet, from_occupations, from_purges, from_schemes, gather_incidents
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.lore.traditions import bless_harvest
from aerona.engine.phase import Phase
from aerona.engine.phases.world_balance import living_worlds
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.recording.record import record as record_incident
from aerona.engine.sites.digs import DigTally, mark_battlefields, start_digs, tend_battlefields, tend_digs
from aerona.engine.sites.rooms import RoomTally, keep_sites
from aerona.engine.storyteller.pace import StorytellerTally, measure, recovered


def count(ctx: TickContext, prefix: str, tally: object) -> None:
    for key, value in vars(tally).items():
        ctx.count(f"{prefix}_{key}", value)


@reads(
    "army.size",
    "beast.strength",
    "cult.zeal",
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
    "people.wealth",
    "settlement.population",
    "settlement.wealth",
    "table.armies",
    "table.army_units",
    "table.augment_effects",
    "table.augments",
    "table.bonds",
    "table.charms",
    "table.chronicle",
    "table.collection_members",
    "table.collection_places",
    "table.commemorations",
    "table.community_societies",
    "table.community_stocks",
    "table.conditions",
    "table.creator",
    "table.crime_cases",
    "table.crowd_feelings",
    "table.cult_tenets",
    "table.culture_ethics",
    "table.culture_values",
    "table.dimensions",
    "table.entities",
    "table.entity_flags",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.gathering_guests",
    "table.gatherings",
    "table.holder_levels",
    "table.hooks",
    "table.incident_collections",
    "table.incident_participants",
    "table.incidents",
    "table.incubating_ideas",
    "table.injuries",
    "table.item_profiles",
    "table.law_jurisdictions",
    "table.law_profiles",
    "table.made_realm_profiles",
    "table.made_realms",
    "table.memories",
    "table.mind_attributes",
    "table.mind_facets",
    "table.minds",
    "table.mortal_profiles",
    "table.network_nodes",
    "table.node_births",
    "table.node_materials",
    "table.nodes",
    "table.offices",
    "table.people_culture",
    "table.personality_values",
    "table.place_profiles",
    "table.polity_members",
    "table.polity_profiles",
    "table.prostheses",
    "table.purity",
    "table.schemes",
    "table.secrets",
    "table.settlement_profiles",
    "table.skills",
    "table.sons",
    "table.stars",
    "table.structure_profiles",
    "table.thoughts",
    "table.time_budgets",
    "table.title_holders",
    "table.tradition_participation",
    "table.tradition_profiles",
    "table.traits",
    "table.world_seasons",
    "table.worlds",
)
@writes(
    "army.size",
    "cult.zeal",
    "mortal.hp",
    "people.population",
    "people.wealth",
    "settlement.population",
    "settlement.wealth",
    "table.army_units",
    "table.bodies",
    "table.body_customs",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.collection_members",
    "table.collection_places",
    "table.community_stocks",
    "table.crowd_feelings",
    "table.entities",
    "table.gathering_guests",
    "table.gatherings",
    "table.goods_flows",
    "table.hooks",
    "table.incident_collections",
    "table.incident_facts",
    "table.incident_participants",
    "table.incident_steps",
    "table.incidents",
    "table.injuries",
    "table.memories",
    "table.mind_facets",
    "table.mortal_profiles",
    "table.people_culture",
    "table.personality_values",
    "table.polity_profiles",
    "table.relationships",
    "table.schemes",
    "table.secrets",
    "table.settlement_profiles",
    "table.thoughts",
)
async def gatherings(ctx: TickContext) -> None:
    tally = GatheringTally()
    atlas = await RegionAtlas.load(ctx.session)
    await gather_all(ctx, [*await occasions(ctx, atlas), *[found for found in await wider_occasions(ctx) if not held(found.host_id)]], atlas, tally)
    count(ctx, "gathering", tally)


@reads(
    "table.collection_incidents",
    "table.collection_members",
    "table.collection_places",
    "table.creator",
    "table.crime_cases",
    "table.dimensions",
    "table.entities",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.incident_collections",
    "table.incident_participants",
    "table.incidents",
    "table.nodes",
    "table.occupations",
    "table.schemes",
    "table.sons",
    "table.stars",
    "table.worlds",
)
@writes("table.collection_incidents", "table.collection_members", "table.collection_places", "table.incident_collections")
async def event_collections(ctx: TickContext) -> None:
    tally = CollectionTally()
    await gather_incidents(ctx, tally)
    await from_schemes(ctx, tally)
    await from_purges(ctx, tally)
    await from_occupations(ctx, tally)
    await close_quiet(ctx, tally)
    count(ctx, "collection", tally)


async def hardest_pressed(ctx: TickContext, world_id: int) -> EntityRow | None:
    found: EntityRow | None = await ctx.session.scalar(
        select(EntityRow)
        .where(EntityRow.world_id == world_id, EntityRow.entity_type.in_(list(COMMUNITY_TYPES)), EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.importance.desc(), EntityRow.id)
        .limit(1)
    )
    return found


async def recover(ctx: TickContext, world_id: int, boost: int, atlas: RegionAtlas) -> bool:
    chance = await recovered(ctx, world_id, RecoveryKind.HARVEST, abs(boost))
    if not ctx.rng(f"storyteller.harvest.{world_id}.{ctx.epoch}").chance(min(PERCENT, round_half_up(chance))):
        return False
    community = await hardest_pressed(ctx, world_id)
    if community is None or held(community.id) or not await bless_harvest(ctx, community, atlas, ctx.rules.storyteller.harvest_gift):
        return False
    await record_incident(
        ctx,
        "storyteller.recovery",
        roles={IncidentRole.BENEFICIARY: community.id},
        facts={
            "gift": ctx.rules.storyteller.harvest_gift,
            "chance": chance,
        },
    )
    return True


@reads(
    "table.chronicle",
    "table.chronicle_entities",
    "table.cosmos",
    "table.creator",
    "table.dimensions",
    "table.dominions",
    "table.entities",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.god_designs",
    "table.god_scales",
    "table.hidden_truths",
    "table.households",
    "table.incident_participants",
    "table.incidents",
    "table.living_lines",
    "table.mind_profiles",
    "table.natural_law_profiles",
    "table.network_nodes",
    "table.node_births",
    "table.nodes",
    "table.polity_stress",
    "table.power_sources",
    "table.powers",
    "table.region_dominion",
    "table.region_environment",
    "table.regional_tensions",
    "table.replicator_lines",
    "table.sons",
    "table.stars",
    "table.storytellers",
    "table.subsystem_tensions",
    "table.wars",
    "table.worlds",
)
@writes(
    "table.chronicle",
    "table.chronicle_entities",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.region_environment",
    "table.regional_tensions",
    "table.storytellers",
    "table.subsystem_tensions",
    "table.tension_records",
)
async def storyteller(ctx: TickContext) -> None:
    tally = StorytellerTally()
    atlas = await RegionAtlas.load(ctx.session)
    for world in await living_worlds(ctx.session):
        row = await measure(ctx, world, tally)
        if row is not None and row.band is TensionBand.HEATED and await recover(ctx, world.id, row.boost_pct, atlas):
            tally.recoveries += 1
    count(ctx, "storyteller", tally)


@reads(
    "table.entities",
    "table.made_realm_profiles",
    "table.mind_profiles",
    "table.nodes",
    "table.place_profiles",
    "table.polity_members",
    "table.relics",
    "table.settlement_profiles",
    "table.site_holders",
    "table.site_rooms",
    "table.structure_profiles",
)
@writes("table.room_contents", "table.site_holders", "table.site_rooms")
async def site_rooms(ctx: TickContext) -> None:
    tally = RoomTally()
    await keep_sites(ctx, tally)
    count(ctx, "site", tally)


@reads(
    "table.collection_members",
    "table.collection_places",
    "table.creator",
    "table.dimensions",
    "table.entities",
    "table.excavation_stages",
    "table.excavations",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.incident_participants",
    "table.incidents",
    "table.mind_profiles",
    "table.node_births",
    "table.nodes",
    "table.polity_members",
    "table.skills",
    "table.sons",
    "table.stars",
    "table.worlds",
)
@writes(
    "table.chronicle",
    "table.chronicle_entities",
    "table.collection_members",
    "table.collection_places",
    "table.excavation_stages",
    "table.excavations",
    "table.incident_collections",
    "table.incident_participants",
    "table.incidents",
)
async def excavations(ctx: TickContext) -> None:
    tally = DigTally()
    atlas = await RegionAtlas.load(ctx.session)
    await start_digs(ctx, atlas, tally)
    await tend_digs(ctx, tally)
    count(ctx, "dig", tally)


@reads("table.battlefield_features", "table.battles", "table.bonds", "table.entities", "table.name_registry", "table.node_births", "table.nodes")
@writes(
    "table.battlefield_features",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.name_registry",
    "table.spirit_profiles",
)
async def battlefields(ctx: TickContext) -> None:
    tally = DigTally()
    await mark_battlefields(ctx, tally)
    await tend_battlefields(ctx, tally)
    count(ctx, "battlefield", tally)


PHASES = (
    Phase("gatherings", gatherings),
    Phase("event_collections", event_collections),
    Phase("storyteller", storyteller),
    Phase("site_rooms", site_rooms),
    Phase("excavations", excavations),
    Phase("battlefields", battlefields),
)
