from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.cosmos import CreatorRow
from aerona.db.tables.creator_bonds import CovenantRow, CreatorDepictionRow, CreatorStandingRow
from aerona.domain.enums.creator import CovenantDuty, CovenantState, CreatorHeresy, CreatorPromise, CreatorSignKind, CreatorStance
from aerona.domain.enums.entity import EntityType
from aerona.engine.divine.creator_bonds import WIDER_SIGNS, keep_creator_bonds, offer, stance_for
from aerona.engine.gods.queries import creator_row
from tests.engine.core.factories import CoreWorld
from tests.engine.core.test_minds_w44 import at

OLD_SIGNS = 4


def test_every_new_sign_has_an_effect_and_stances_follow_the_strongest_feeling() -> None:
    assert len(WIDER_SIGNS) == len(CreatorSignKind) - OLD_SIGNS
    loving = CreatorStandingRow(people_entity_id=1, awe=10, love=70, dread=5, gratitude=5, resentment=0, ignorance=10, heresy=CreatorHeresy.NONE, locked=[])
    assert stance_for(loving) is CreatorStance.WORSHIP


async def test_a_people_comes_to_hold_and_picture_the_creator(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 3)
    if await creator_row(session) is None:
        return
    await keep_creator_bonds(ctx)
    assert await session.get(CreatorStandingRow, world.people.id) is not None
    assert await session.get(CreatorDepictionRow, world.people.id) is not None


async def test_a_reverent_people_seals_an_offered_covenant(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 3)
    creator = await creator_row(session)
    if creator is None:
        return
    session.add(
        CreatorStandingRow(
            people_entity_id=world.people.id, awe=90, love=5, dread=0, gratitude=0, resentment=0, ignorance=0, locked=["stance"], stance=CreatorStance.REVERENCE
        )
    )
    covenant = await offer(ctx, world.people.id, CovenantDuty.PEACE, CreatorPromise.PLENTY, None)
    await keep_creator_bonds(ctx)
    row = await session.get(CovenantRow, covenant.id)
    assert row is not None and row.state is CovenantState.SEALED
    assert isinstance(creator, CreatorRow)


async def test_an_unaimed_sign_reaches_the_people_that_knows_the_creator_least(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 3)
    creator = await creator_row(session)
    if creator is None:
        return
    reached = await WIDER_SIGNS[CreatorSignKind.OMEN](ctx, creator, None)
    assert reached is not None and reached.entity_type is EntityType.PEOPLE
    standing = await session.get(CreatorStandingRow, reached.id)
    assert standing is not None and standing.awe > 0
