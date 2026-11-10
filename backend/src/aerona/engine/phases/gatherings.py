from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus
from aerona.domain.enums.storyteller import RecoveryKind, TensionBand
from aerona.engine.context import TickContext
from aerona.engine.gatherings.hold import GatheringTally, gather_all
from aerona.engine.gatherings.occasions import occasions
from aerona.engine.history.collections import CollectionTally, close_quiet, from_occupations, from_purges, from_schemes, gather_incidents
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.lore.traditions import bless_harvest
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.phases.world_balance import living_worlds
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.sites.digs import DigTally, mark_battlefields, start_digs, tend_battlefields, tend_digs
from aerona.engine.sites.rooms import RoomTally, keep_sites
from aerona.engine.storyteller.pace import StorytellerTally, measure, recovered


def count(ctx: TickContext, prefix: str, tally: object) -> None:
    for key, value in vars(tally).items():
        ctx.count(f"{prefix}_{key}", value)


@reads(
    "cult.zeal",
    "settlement.wealth",
    "table.bonds",
    "table.collection_members",
    "table.collection_places",
    "table.crime_cases",
    "table.gathering_guests",
    "table.gatherings",
    "table.incident_collections",
    "table.incidents",
    "table.mind_facets",
    "table.minds",
    "table.nodes",
    "table.offices",
    "table.place_profiles",
    "table.polity_members",
    "table.polity_profiles",
    "table.schemes",
    "table.secrets",
    "table.structure_profiles",
    "table.title_holders",
    "table.world_seasons",
)
@writes(
    "cult.zeal",
    "table.chronicle",
    "table.chronicle_entities",
    "table.collection_members",
    "table.collection_places",
    "table.entities",
    "table.epoch_year_cursors",
    "table.gathering_guests",
    "table.gatherings",
    "table.incident_collections",
    "table.incident_participants",
    "table.incidents",
    "table.mortal_profiles",
    "table.polity_profiles",
    "table.relationships",
    "table.thoughts",
)
async def gatherings(ctx: TickContext) -> None:
    tally = GatheringTally()
    atlas = await RegionAtlas.load(ctx.session)
    await gather_all(ctx, await occasions(ctx, atlas), atlas, tally)
    count(ctx, "gathering", tally)


@reads(
    "table.collection_members",
    "table.collection_places",
    "table.crime_cases",
    "table.incident_collections",
    "table.incident_participants",
    "table.incidents",
    "table.nodes",
    "table.occupations",
    "table.schemes",
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
    await note(ctx, f"After hard years, the harvest of {community.name} came in full.", key="storyteller.recovery", ids=[community.id])
    return True


@reads("table.cosmos", "table.incidents", "table.storytellers")
@writes(
    "table.chronicle",
    "table.chronicle_entities",
    "table.epoch_year_cursors",
    "table.incident_participants",
    "table.incidents",
    "table.region_environment",
    "table.storytellers",
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


@reads("table.place_profiles", "table.polity_members", "table.settlement_profiles", "table.site_holders", "table.site_rooms", "table.structure_profiles")
@writes("table.room_contents", "table.site_holders", "table.site_rooms")
async def site_rooms(ctx: TickContext) -> None:
    tally = RoomTally()
    await keep_sites(ctx, tally)
    count(ctx, "site", tally)


@reads("table.excavations")
async def excavations(ctx: TickContext) -> None:
    tally = DigTally()
    atlas = await RegionAtlas.load(ctx.session)
    await start_digs(ctx, atlas, tally)
    await tend_digs(ctx, tally)
    count(ctx, "dig", tally)


@reads("table.battlefield_features", "table.battles")
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
