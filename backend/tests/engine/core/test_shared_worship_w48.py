from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.pantheon import SyncretismRow
from aerona.domain.enums.bond import BondKind, BondRole, BondState
from aerona.domain.enums.domain import Domain
from aerona.engine.divine.pantheon import compete, syncretise
from tests.engine.core.factories import CoreWorld, settlement
from tests.engine.core.test_arcana_w15 import foreign_caster
from tests.engine.core.test_minds_w44 import at


async def home_town(session: AsyncSession, world: CoreWorld) -> EntityRow:
    town = await settlement(session, "Harbour", world, world.regions[0])
    await BondRepository(session).connect(BondDraft(world.people.id, town.id, BondKind.LIVES_IN, 1, None, role=BondRole.HOMELAND))
    return town


async def worship(session: AsyncSession, source: int, god: int) -> None:
    await BondRepository(session).connect(BondDraft(source, god, BondKind.WORSHIPS, 1, None))


async def test_a_people_whose_towns_keep_a_second_god_comes_to_hold_both_as_one(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 2, pantheon_life={"merge_pct": 100})
    god = await foreign_caster(session, world)
    world.son.domain_primary = Domain.SEA
    town = await home_town(session, world)
    await worship(session, world.people.id, world.son.id)
    await worship(session, town.id, god.id)
    assert await syncretise(ctx) == 1
    joined = await session.scalar(select(SyncretismRow))
    assert joined is not None and (joined.foreign_god_id, joined.son_id, joined.people_entity_id) == (god.id, world.son.id, world.people.id)


async def test_two_gods_of_one_domain_contend_for_a_people_through_its_towns(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 2, pantheon_life={"switch_pct": 100})
    first = await foreign_caster(session, world)
    second = await foreign_caster(session, world)
    second.power = 10
    town = await home_town(session, world)
    await worship(session, world.people.id, first.id)
    await worship(session, town.id, second.id)
    assert await compete(ctx) == 1
    kept = await session.scalar(select(BondRow).where(BondRow.source_node_id == town.id, BondRow.target_node_id == second.id))
    assert kept is not None and kept.state is BondState.PAST
