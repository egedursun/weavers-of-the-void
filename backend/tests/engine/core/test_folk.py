from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import PolityMemberRow
from aerona.domain.enums.bond import BondKind, BondRole
from aerona.domain.enums.discovery import GreatField
from aerona.domain.enums.entity import EntityType, MortalRole
from aerona.domain.enums.mind import SkillKind
from aerona.domain.models.entity_stats import PolityStats
from aerona.engine.lore.great_people import candidate
from aerona.engine.mind.book import skills_of
from aerona.engine.primitives.folk import folk_among, homes_of, present_among
from aerona.engine.primitives.manual import manual_context
from aerona.engine.structures.functions import residents
from tests.engine.core.factories import CoreWorld, bond, entity, mortal, settlement


async def homeland(session: AsyncSession, world: CoreWorld) -> tuple[EntityRow, EntityRow, EntityRow]:
    ruled = await settlement(session, "Brookhold", world, world.regions[0])
    descended = await settlement(session, "Fernwick", world, world.regions[0])
    stranger = await settlement(session, "Elsewhere", world, world.regions[0])
    await BondRepository(session).connect(BondDraft(world.people.id, ruled.id, BondKind.RULES, 1, "homeland", role=BondRole.HOMELAND))
    await bond(session, descended.id, world.people.id, BondKind.DESCENDS_FROM)
    return ruled, descended, stranger


async def mortal_ids(session: AsyncSession, clause: object) -> set[int]:
    return set(await session.scalars(select(EntityRow.id).where(clause, EntityRow.entity_type == EntityType.MORTAL)))


async def test_a_people_is_found_in_the_towns_of_its_homeland(session: AsyncSession, world: CoreWorld) -> None:
    ruled, descended, stranger = await homeland(session, world)
    assert await homes_of(session, world.people) == {world.people.id, ruled.id, descended.id}
    here = await mortal(session, "Ana", world, ruled.id)
    there = await mortal(session, "Bel", world, descended.id)
    away = await mortal(session, "Cid", world, stranger.id)
    assert await mortal_ids(session, await present_among(session, [world.people.id])) == {here.id, there.id}
    assert away.id not in await mortal_ids(session, await present_among(session, [world.people.id]))
    assert await mortal_ids(session, await present_among(session, [stranger.id])) == {away.id}


async def test_a_polity_is_found_in_its_member_towns_and_peoples(session: AsyncSession, world: CoreWorld) -> None:
    ruled, _, stranger = await homeland(session, world)
    realm = await entity(session, "Kingdom of Vale", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    session.add_all(
        [PolityMemberRow(polity_entity_id=realm.id, member_entity_id=world.people.id), PolityMemberRow(polity_entity_id=realm.id, member_entity_id=stranger.id)]
    )
    await session.flush()
    subject = await mortal(session, "Ana", world, ruled.id)
    townsman = await mortal(session, "Bel", world, stranger.id)
    assert await mortal_ids(session, await present_among(session, [realm.id])) == {subject.id, townsman.id}


async def test_folk_include_those_sworn_to_a_place_who_live_elsewhere(session: AsyncSession, world: CoreWorld) -> None:
    ruled, _, stranger = await homeland(session, world)
    sworn = await mortal(session, "Ana", world, stranger.id)
    sworn.affiliated_entity_id = ruled.id
    await session.flush()
    assert sworn.id in await mortal_ids(session, await folk_among(session, [world.people.id]))
    assert sworn.id not in await mortal_ids(session, await present_among(session, [world.people.id]))


async def test_a_people_raises_its_great_from_its_own_towns(session: AsyncSession, world: CoreWorld) -> None:
    ruled, _, _ = await homeland(session, world)
    ctx = await manual_context(session, "test")
    sage = await mortal(session, "Ana", world, ruled.id)
    assert await candidate(ctx, world.people, GreatField.SCHOLAR) is sage


async def test_a_house_hosted_by_a_people_serves_the_folk_of_its_towns(session: AsyncSession, world: CoreWorld) -> None:
    ruled, _, _ = await homeland(session, world)
    ctx = await manual_context(session, "test")
    healer = await mortal(session, "Ana", world, ruled.id)
    healer.mortal_role = MortalRole.HEALER
    await session.flush()
    assert [row.id for row in await residents(ctx, world.people, frozenset({MortalRole.HEALER}))] == [healer.id]
    assert SkillKind.MEDICINE not in await skills_of(session, healer.id)
