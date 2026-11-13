import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.commodities import FOOD_KINDS
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.cosmic_state import VesselProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.gatherings import CollectionMemberRow, CollectionPlaceRow, CollectionRow, GatheringGuestRow
from aerona.db.tables.mind import CultureEthicRow, SkillRow
from aerona.db.tables.place import PlaceProfileRow
from aerona.db.tables.sites import BattlefieldFeatureRow, ExcavationStageRow, SiteHolderRow, SiteRoomRow
from aerona.db.tables.storyteller import StorytellerRow, TensionRecordRow
from aerona.domain.enums.bond import BondKind, BondRole
from aerona.domain.enums.entity import EntityFlag, EntityType
from aerona.domain.enums.environment import TerrainKind
from aerona.domain.enums.gathering import CollectionKind, CollectionRole, GatheringKind, GatheringStatus, Milestone
from aerona.domain.enums.military import VesselStatus
from aerona.domain.enums.mind import ActKind, EthicalStance, MemoryKind, SkillKind, SkillSource
from aerona.domain.enums.place import PlaceKind
from aerona.domain.enums.site import BattlefieldFeature, ExcavationStage, ExcavationStatus, SiteChallenge, SiteRoomKind
from aerona.domain.enums.storyteller import StorytellerProfile, TensionBand
from aerona.domain.enums.travel import VehicleKind
from aerona.domain.models.entity_stats import PlaceStats, StructureStats, VesselStats
from aerona.domain.models.genesis import GenesisSettings
from aerona.engine.context import TickContext
from aerona.engine.cosmos.features import add_stock
from aerona.engine.economy.stocks import holding
from aerona.engine.gatherings import control
from aerona.engine.gatherings.hold import massacre_chance
from aerona.engine.military.engineering import earthworks_of
from aerona.engine.mind.memories import memories_about
from aerona.engine.phases.vendettas import walk_raided
from aerona.engine.primitives.queries import add_flag
from aerona.engine.sites.digs import DigTally, dig_sites, diggable, tend_battlefields
from aerona.engine.sites.rooms import RoomTally, keep_sites
from aerona.engine.storyteller.pace import StorytellerTally, band_of, boost_of, measure, storyteller_of
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, bond, entity, mortal, settlement
from tests.engine.cosmos.test_wilds_typed import land


async def place(session: AsyncSession, world: CoreWorld, name: str, kind: PlaceKind) -> EntityRow:
    row = await entity(session, name, EntityType.PLACE, PlaceStats(), world_id=world.world.id, location_id=world.regions[0].id)
    session.add(PlaceProfileRow(entity_id=row.id, kind=kind, locked=[]))
    await session.flush()
    return row


async def test_a_convened_feast_is_held_with_its_summoned_guests(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    host = await mortal(session, "Aben", world, world.regions[0].id)
    guest = await mortal(session, "Corra", world, world.regions[0].id)
    row = await control.convene(ctx, host.id, GatheringKind.FEAST, place_id=None, honoured_id=None, milestone=None, guests=[guest.id], hold_now=True)
    assert row.status is not GatheringStatus.PLANNED
    assert row.by_player
    assert row.year is not None
    assert row.year >= 0
    guests = {item.node_id: item for item in await session.scalars(select(GatheringGuestRow).where(GatheringGuestRow.gathering_id == row.id))}
    assert guest.id in guests
    assert guests[guest.id].attended is True


async def test_every_kind_of_node_the_gods_summon_comes(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    host = await mortal(session, "Ilse", world, world.regions[0].id)
    summoned = [world.son.id, world.world.id, world.creator.id, world.people.id]
    row = await control.convene(ctx, host.id, GatheringKind.WEDDING, place_id=None, honoured_id=None, milestone=None, guests=summoned, hold_now=True)
    came = {item.node_id: item.attended for item in await session.scalars(select(GatheringGuestRow).where(GatheringGuestRow.gathering_id == row.id))}
    assert {node: came.get(node) for node in summoned} == dict.fromkeys(summoned, True)


async def test_a_people_holding_a_feast_invites_its_own_folk(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Brindle", world, world.regions[0])
    folk = await mortal(session, "Juno", world, town.id)
    folk.affiliated_entity_id = world.people.id
    await session.flush()
    row = await control.convene(ctx, world.people.id, GatheringKind.FEAST, place_id=None, honoured_id=None, milestone=None, guests=[], hold_now=False)
    invited = set(await session.scalars(select(GatheringGuestRow.node_id).where(GatheringGuestRow.gathering_id == row.id)))
    assert folk.id in invited


async def test_a_planned_gathering_waits_until_the_gods_hold_it(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    host = await mortal(session, "Dain", world, world.regions[0].id)
    row = await control.convene(ctx, host.id, GatheringKind.COUNCIL, place_id=None, honoured_id=None, milestone=None, guests=[], hold_now=False)
    assert row.status is GatheringStatus.PLANNED
    held = await control.hold_planned(ctx, row.id)
    assert held.status is not GatheringStatus.PLANNED
    edited = await control.edit_gathering(ctx, row.id, {"prestige": 77}, [])
    assert edited.prestige == 77
    assert "prestige" in edited.locked


async def test_a_history_is_set_down_rewritten_and_struck(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    leader = await mortal(session, "Eshe", world, world.regions[0].id)
    other = await mortal(session, "Fenn", world, world.regions[0].id)
    row = await control.create_collection(
        ctx,
        CollectionKind.JOURNEY,
        name="",
        world_id=world.world.id,
        members={leader.id: CollectionRole.LEADER},
        places=[world.regions[0].id],
        parent_id=None,
    )
    assert row.name
    assert {"name", "kind", "parent_id"} <= set(row.locked)
    await control.set_member(ctx, row.id, other.id, CollectionRole.WITNESS)
    roles = {item.node_id: item.role for item in await session.scalars(select(CollectionMemberRow).where(CollectionMemberRow.collection_id == row.id))}
    assert roles == {leader.id: CollectionRole.LEADER, other.id: CollectionRole.WITNESS}
    await control.set_place(ctx, row.id, world.regions[0].id, present=False)
    assert not list(await session.scalars(select(CollectionPlaceRow).where(CollectionPlaceRow.collection_id == row.id)))
    await control.edit_collection(ctx, row.id, {"end_epoch": ctx.epoch}, [])
    assert row.end_epoch == ctx.epoch
    await control.delete_collection(ctx, row.id)
    assert await session.get(CollectionRow, row.id) is None


async def test_a_world_without_a_storyteller_takes_the_one_chosen_at_genesis(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    world.cosmos.genesis_settings = GenesisSettings(magic=50, danger=50, peoples=1, storyteller=StorytellerProfile.CHAOTIC)
    await session.flush()
    assert (await storyteller_of(ctx, world.world.id)).profile is StorytellerProfile.CHAOTIC


def test_the_storyteller_heats_and_quiets_against_its_aim() -> None:
    rules = Rules()
    assert band_of(rules, 50, 50) is TensionBand.IN_BAND
    assert band_of(rules, 100, 0) is TensionBand.HEATED
    assert band_of(rules, 0, 100) is TensionBand.QUIET
    assert boost_of(rules, 0, 100, TensionBand.QUIET) > 0
    assert boost_of(rules, 100, 0, TensionBand.HEATED) < 0
    assert boost_of(rules, 50, 50, TensionBand.IN_BAND) == 0


async def test_the_storyteller_weighs_each_world_and_keeps_what_the_gods_hold(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    row = await control.set_storyteller(ctx, world.world.id, StorytellerProfile.RISING, {"tension": 90}, [])
    assert row.profile is StorytellerProfile.RISING
    await measure(ctx, world.world, StorytellerTally())
    stored = await session.get(StorytellerRow, world.world.id)
    assert stored is not None
    assert stored.tension == 90
    assert list(await session.scalars(select(TensionRecordRow).where(TensionRecordRow.world_id == world.world.id)))


async def test_a_lair_is_furnished_once_and_walked_to_its_heart(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    lair = await place(session, world, "Deep Den", PlaceKind.LAIR)
    await keep_sites(ctx, RoomTally())
    rooms = list(await session.scalars(select(SiteRoomRow).where(SiteRoomRow.site_entity_id == lair.id).order_by(SiteRoomRow.position)))
    assert [room.kind for room in rooms] == [SiteRoomKind.GATE, SiteRoomKind.HALL, SiteRoomKind.LAIR, SiteRoomKind.STORE]
    await keep_sites(ctx, RoomTally())
    assert len(list(await session.scalars(select(SiteRoomRow).where(SiteRoomRow.site_entity_id == lair.id)))) == len(rooms)
    for room in rooms:
        await control.edit_room(ctx, room.id, {"challenge": SiteChallenge.NONE.value}, [])
    delver = await mortal(session, "Gale", world, world.regions[0].id, strength=90)
    walk = await control.force_delve(ctx, delver.id, lair.id)
    assert walk.cleared == len(rooms)
    assert walk.reached_heart
    holder = await control.set_holder(ctx, lair.id, delver.id)
    assert await session.get(SiteHolderRow, holder.id) is not None


async def test_a_dig_goes_stage_by_stage_until_the_gods_end_it(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    ruin = await place(session, world, "Old Mound", PlaceKind.RUIN)
    leader = await mortal(session, "Hale", world, world.regions[0].id)
    session.add(SkillRow(holder_node_id=leader.id, skill=SkillKind.LORE, level=80, peak=80, last_used_epoch=1, source=SkillSource.PRACTICE))
    await session.flush()
    dig = await control.begin_dig(ctx, ruin.id, leader.id, None)
    assert dig.stage is ExcavationStage.SURVEY
    stages = list(await session.scalars(select(ExcavationStageRow).where(ExcavationStageRow.excavation_id == dig.id)))
    assert stages[0].stage is ExcavationStage.SURVEY
    for stage in stages:
        await control.edit_stage(ctx, stage.id, {"technique": None, "risk": "none"}, [])
    advanced = await control.advance_dig(ctx, dig.id)
    assert advanced.stage is ExcavationStage.CLEARING
    assert stages[0].resolved_epoch == ctx.epoch
    ended = await control.edit_dig(ctx, dig.id, {"status": ExcavationStatus.ABANDONED.value}, [])
    assert ended.status is ExcavationStatus.ABANDONED
    assert "status" in ended.locked


async def test_a_battlefield_mark_is_laid_and_held(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    field = await place(session, world, "Red Field", PlaceKind.RUIN)
    feature = await control.create_feature(ctx, field.id, BattlefieldFeature.MASS_GRAVE, 60)
    edited = await control.edit_feature(ctx, feature.id, {"strength": 15}, [])
    assert edited.strength == 15
    assert "strength" in edited.locked
    await control.delete_feature(ctx, feature.id)
    assert await session.get(BattlefieldFeatureRow, feature.id) is None


async def test_ruins_of_earlier_creations_and_wrecks_can_be_dug(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    ruin = await entity(session, "Old Seat", EntityType.STRUCTURE, StructureStats(), world_id=world.world.id, location_id=world.regions[0].id)
    await add_flag(session, ruin.id, EntityFlag.PREVIOUS_CREATION, ctx.epoch)
    hull = await entity(session, "Lost Hull", EntityType.VESSEL, VesselStats(), world_id=world.world.id, location_id=world.regions[0].id)
    session.add(VesselProfileRow(entity_id=hull.id, kind=VehicleKind.SHIP, status=VesselStatus.WRECKED, locked=[]))
    await session.flush()
    assert await diggable(session, ruin)
    assert await diggable(session, hull)
    assert not await diggable(session, world.regions[0])
    assert {ruin.id, hull.id} <= {site.id for site in await dig_sites(session)}


async def test_a_massacre_is_unthinkable_where_killing_a_guest_is(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Hearth", world, world.regions[0])
    await BondRepository(session).connect(BondDraft(world.people.id, town.id, BondKind.LIVES_IN, ctx.epoch, role=BondRole.HOMELAND))
    host = await mortal(session, "Kade", world, town.id)
    assert await massacre_chance(ctx, host) == ctx.rules.gatherings.massacre_pct
    session.add(CultureEthicRow(holder_entity_id=world.people.id, act=ActKind.GUEST_KILLING, stance=EthicalStance.SHAMEFUL, locked=[]))
    await session.flush()
    assert await massacre_chance(ctx, host) == pytest.approx(ctx.rules.gatherings.massacre_pct * ctx.rules.gatherings.massacre_shameful_pct / 100)
    ethic = await session.get(CultureEthicRow, (world.people.id, ActKind.GUEST_KILLING))
    assert ethic is not None
    ethic.stance = EthicalStance.UNTHINKABLE
    await session.flush()
    assert await massacre_chance(ctx, host) == 0


async def test_a_feast_serves_food_from_its_hosts_stores(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Larder", world, world.regions[0])
    host = await mortal(session, "Lio", world, town.id)
    guest = await mortal(session, "Mara", world, town.id)
    await add_stock(ctx, town, FOOD_KINDS[0], 500)
    before = await holding(session, town.id, FOOD_KINDS[0])
    row = await control.convene(ctx, host.id, GatheringKind.FEAST, place_id=None, honoured_id=None, milestone=None, guests=[guest.id], hold_now=True)
    assert row.food > 0
    assert await holding(session, town.id, FOOD_KINDS[0]) == before - row.food


async def test_a_milestone_leaves_a_memory_with_those_who_came(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    host = await mortal(session, "Nell", world, world.regions[0].id)
    guest = await mortal(session, "Oren", world, world.regions[0].id)
    await control.convene(ctx, host.id, GatheringKind.MILESTONE, place_id=None, honoured_id=None, milestone=Milestone.BIRTH, guests=[guest.id], hold_now=True)
    kinds = {row.kind for row in await memories_about(session, guest.id, host.id)}
    assert MemoryKind.FORMATIVE in kinds


async def test_a_feud_raid_walks_the_rooms_of_the_town_it_strikes(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    raiders = await settlement(session, "Raiders", world, world.regions[0])
    target = await settlement(session, "Target", world, world.regions[0])
    leader = await mortal(session, "Pell", world, raiders.id, strength=90)
    await bond(session, leader.id, raiders.id, BondKind.RULES)
    room = await control.create_room(ctx, target.id, SiteRoomKind.STORE, challenge=SiteChallenge.NONE, difficulty=0, position=None)
    told = await walk_raided(ctx, raiders, target)
    assert leader.name in told
    assert room.cleared_epoch == ctx.epoch
    assert room.cleared_by_entity_id == leader.id


async def test_old_earthworks_keep_their_land_fortified(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    field = await place(session, world, "Long Dyke", PlaceKind.RUIN)
    region = await land(session, world.regions[0].id, world.world.id, TerrainKind.PLAIN, 50)
    feature = await control.create_feature(ctx, field.id, BattlefieldFeature.EARTHWORKS, 60)
    feature.epoch = ctx.epoch - 1
    await tend_battlefields(ctx, DigTally())
    assert earthworks_of(region) >= 60 - ctx.rules.excavations.feature_decay
