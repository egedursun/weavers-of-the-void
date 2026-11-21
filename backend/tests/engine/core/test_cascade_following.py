import pytest
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.key_moves import PrimaryKeyMoved
from aerona.db.tables.factions import FactionMembershipRow
from aerona.db.tables.households import DwellingRow, HouseholdRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.models.entity_stats import FactionStats
from aerona.engine.factions.book import move_member
from tests.engine.core.factories import CoreWorld, entity, mortal


async def household(session: AsyncSession, name: str, head_id: int | None = None) -> tuple[HouseholdRow, DwellingRow]:
    home = HouseholdRow(name=name, head_node_id=head_id, debts={}, locked=[])
    session.add(home)
    await session.flush()
    dwelling = DwellingRow(household_id=home.id, locked=[])
    session.add(dwelling)
    await session.flush()
    return home, dwelling


async def test_a_dwelling_the_database_removes_with_its_household_leaves_the_session_too(session: AsyncSession, world: CoreWorld) -> None:
    home, dwelling = await household(session, "The Emptied House")
    await session.delete(home)
    await session.flush()
    assert inspect(dwelling).detached
    _other, fresh = await household(session, "The Next House")
    assert inspect(fresh).persistent


async def test_a_reference_the_database_clears_is_cleared_in_the_session_too(session: AsyncSession, world: CoreWorld) -> None:
    head = await mortal(session, "Orrin Hale", world, None)
    home, _dwelling = await household(session, "The House of Orrin", head.id)
    await session.delete(head)
    await session.flush()
    assert home.head_node_id is None and not session.is_modified(home)


async def test_moving_the_key_of_a_stored_row_is_refused_and_moving_a_member_keeps_the_record(session: AsyncSession, world: CoreWorld) -> None:
    first = await entity(session, "The First Band", EntityType.FACTION, FactionStats(), world_id=world.world.id)
    second = await entity(session, "The Second Band", EntityType.FACTION, FactionStats(), world_id=world.world.id)
    member = await mortal(session, "Iska Venn", world, None)
    row = FactionMembershipRow(faction_entity_id=first.id, mortal_entity_id=member.id, locked=[])
    session.add(row)
    await session.flush()
    with pytest.warns(PrimaryKeyMoved):
        row.faction_entity_id = second.id
        row.faction_entity_id = first.id
    moved = await move_member(session, row, second.id, 3)
    await session.flush()
    assert inspect(row).deleted or inspect(row).detached
    assert await session.get(FactionMembershipRow, (second.id, member.id)) is moved and moved.joined_epoch == 3
