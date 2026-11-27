from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.sons import SonRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.engine.phases.sons import domain_rivalry
from aerona.rules.registry import Rules
from tests.engine.gods.factories import GodsWorld, make_context, make_son


async def allied_pair(session: AsyncSession, world: GodsWorld, relation: int) -> tuple[int, int]:
    first = await make_son(session, "Tidekeeper", world.world.id)
    second = await make_son(session, "Stormcaller", world.world.id)
    await BondRepository(session).connect(BondDraft(first.id, second.id, BondKind.ALLY, 4, "A covenant sworn before the council."))
    await SonRepository(session).change_relation(first.id, second.id, relation)
    await session.flush()
    return first.id, second.id


async def ally_bonds(session: AsyncSession) -> int:
    return int(await session.scalar(select(func.count(BondRow.id)).where(BondRow.kind == BondKind.ALLY, BondRow.state == BondState.ACTIVE)) or 0)


async def test_a_covenant_lapses_once_the_two_sons_are_enemies(session: AsyncSession, rules: Rules, world: GodsWorld) -> None:
    await allied_pair(session, world, -98)
    await domain_rivalry(make_context(session, rules, 10))
    assert await ally_bonds(session) == 0
    assert await session.scalar(select(func.count(IncidentRow.id)).where(IncidentRow.kind == "sons.covenant_lapsed")) == 1


async def test_a_covenant_holds_while_the_sons_stay_on_terms(session: AsyncSession, rules: Rules, world: GodsWorld) -> None:
    await allied_pair(session, world, 10)
    await domain_rivalry(make_context(session, rules, 10))
    assert await ally_bonds(session) == 1
