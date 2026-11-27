from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.entities import EntityDraft, EntityRepository
from aerona.db.tables.economy import ResourceProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.polity import PolityMemberRow
from aerona.db.tables.records import IncidentFactRow
from aerona.db.tables.warfare import ArmyRow
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityOrigin, EntityStatus, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.war import WarEnding, WarStatus
from aerona.domain.models.entity_stats import ArmyStats, PolityStats, ResourceStats
from aerona.engine.lifecycle.mortal_death import die
from aerona.engine.phases.lifecycle_ends import affairs_of_the_ended
from aerona.engine.phases.ruins import abandon
from aerona.engine.phases.trade import _yields
from aerona.engine.polity.formation import close_landless_realms
from aerona.engine.polity.houses import HouseBook, found_house
from aerona.engine.primitives.records import retire_in
from aerona.engine.primitives.stats import stat
from aerona.engine.services.war import open_war
from aerona.engine.services.war_resolution import close_stale_wars
from tests.db.factories import seed_world
from tests.engine.core.factories import seed_core_world
from tests.engine.warfare.factories import make, make_ctx


async def deposit_on(session: AsyncSession, name: str, world_id: int) -> EntityRow:
    return await EntityRepository(session).create(
        EntityDraft(
            name=name,
            entity_type=EntityType.RESOURCE,
            description=name,
            stats=ResourceStats(),
            power_level=3,
            origin=EntityOrigin.ENGINE,
            birth_epoch=1,
            world_id=world_id,
        )
    )


async def host(session: AsyncSession, name: str, world_id: int) -> EntityRow:
    return await EntityRepository(session).create(
        EntityDraft(
            name=name,
            entity_type=EntityType.ARMY,
            description=name,
            stats=ArmyStats(size=200),
            power_level=3,
            origin=EntityOrigin.ENGINE,
            birth_epoch=1,
            world_id=world_id,
        )
    )


async def told(session: AsyncSession, kind: str) -> list[IncidentRow]:
    return list(await session.scalars(select(IncidentRow).where(IncidentRow.kind == kind).order_by(IncidentRow.id)))


async def test_a_war_whose_side_fell_after_the_battles_closes_at_the_epoch_end_and_is_told(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    standing = await make(session, "Red Folk", EntityType.PEOPLE, world_id, population=4000)
    fallen = await make(session, "Blue Town", EntityType.SETTLEMENT, world_id, population=300)
    war = await open_war(ctx, standing, fallen)
    await retire_in(ctx, fallen, "was abandoned")
    await affairs_of_the_ended(ctx)
    assert war.status is WarStatus.ENDED
    assert war.ending is WarEnding.NO_SIDE_LEFT
    [ending] = await told(session, "war.ended_no_side_left")
    roles = {row.role: row.node_id for row in await session.scalars(select(IncidentParticipantRow).where(IncidentParticipantRow.incident_id == ending.id))}
    assert roles[IncidentRole.ACTOR] == standing.id
    assert roles[IncidentRole.OPPONENT] == fallen.id


async def test_every_stale_war_closing_is_told(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    first = await make(session, "Red Folk", EntityType.PEOPLE, world_id, population=4000)
    second = await make(session, "Green Folk", EntityType.PEOPLE, world_id, population=4000)
    calm = await open_war(ctx, first, second)
    assert await close_stale_wars(ctx) == 1
    assert calm.ending is WarEnding.PEACE
    assert len(await told(session, "war.ended_peace")) == 1


async def test_the_dead_lead_no_army_in_the_field_and_keep_no_health(session: AsyncSession) -> None:
    ctx = make_ctx(session)
    world_id = (await seed_core_world(session)).world.id
    folk = await make(session, "Red Town", EntityType.SETTLEMENT, world_id, population=4000)
    marshal = await make(session, "Ama", EntityType.MORTAL, world_id, location_id=folk.id, hp=80, age=40, lifespan=70)
    field = await host(session, "Red Host", world_id)
    old = await host(session, "Old Host", world_id)
    session.add(ArmyRow(entity_id=field.id, owner_entity_id=folk.id, commander_entity_id=marshal.id, raised_epoch=9))
    session.add(ArmyRow(entity_id=old.id, owner_entity_id=folk.id, commander_entity_id=marshal.id, raised_epoch=5, disbanded_epoch=6))
    await session.flush()
    await die(ctx, marshal, cause="fell", forced=True)
    rows = {row.entity_id: row.commander_entity_id for row in await session.scalars(select(ArmyRow))}
    assert rows == {field.id: None, old.id: marshal.id}
    assert stat(marshal, "hp") == 0


async def test_a_town_that_turns_to_ruin_holds_no_people(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    town = await make(session, "Grey Town", EntityType.SETTLEMENT, world_id, population=58)
    await abandon(ctx, town)
    assert stat(town, "population") == 0
    [ruined] = await told(session, "ruins.abandoned")
    left = await session.scalar(select(IncidentFactRow.number).where(IncidentFactRow.incident_id == ruined.id, IncidentFactRow.key == "population"))
    assert left == 58


async def test_a_war_for_a_deposit_is_only_for_one_on_the_attackers_own_world(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    far = (await seed_world(session, "Farland", "Far Sun")).id
    away = await deposit_on(session, "Far Deposit", far)
    near = await deposit_on(session, "Near Deposit", world_id)
    for deposit in (away, near):
        session.add(
            ResourceProfileRow(
                resource_entity_id=deposit.id, commodity=CommodityKind.ORE, reserve=100, initial_reserve=100, richness=50, extraction_difficulty=20, quality=50
            )
        )
    await session.flush()
    wanted = [CommodityKind.ORE]
    assert await _yields(ctx, {away.id}, wanted, world_id) is None
    found = await _yields(ctx, {away.id, near.id}, wanted, world_id)
    assert found is not None and found.id == near.id


async def test_a_house_whose_last_member_died_late_in_the_age_dies_out_at_its_close(session: AsyncSession) -> None:
    ctx = make_ctx(session)
    world_id = (await seed_core_world(session)).world.id
    town = await make(session, "Red Town", EntityType.SETTLEMENT, world_id, population=4000)
    founder = await make(session, "Ama", EntityType.MORTAL, world_id, location_id=town.id, hp=80, age=40, lifespan=70)
    house = await found_house(ctx, await HouseBook.load(ctx), founder)
    await session.flush()
    await retire_in(ctx, founder, "died")
    await affairs_of_the_ended(ctx)
    assert house.status is EntityStatus.DESTROYED
    assert stat(house, "members") == 0


async def test_a_realm_whose_last_land_fell_empty_ends_at_the_close_of_the_age(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    town = await make(session, "Grey Town", EntityType.SETTLEMENT, world_id, population=300)
    realm = await EntityRepository(session).create(
        EntityDraft(
            name="The realm of Grey Town",
            entity_type=EntityType.POLITY,
            description="A realm.",
            stats=PolityStats(),
            power_level=3,
            origin=EntityOrigin.ENGINE,
            birth_epoch=1,
            world_id=world_id,
        )
    )
    session.add(PolityMemberRow(polity_entity_id=realm.id, member_entity_id=town.id, joined_epoch=1, autonomy=0, locked=[]))
    await session.flush()
    await abandon(ctx, town)
    assert await close_landless_realms(ctx) == 1
    assert realm.status is EntityStatus.DESTROYED
