from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.session import Database
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.kinds import GoodKindRow, KindHoldingRow
from aerona.db.write_guard import HELD_SCOPE, HeldScope
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.kinds import GoodCategory, KindConcept, KindSpread, KindStance
from aerona.domain.models.entity_stats import PeopleStats
from aerona.engine.kinds.life import keep_kinds
from aerona.rules.registry import Rules
from tests.conftest import OpenDatabase
from tests.engine.cosmos.factories import EPOCH, Cosmos, make_entity, seed_cosmos, tick, tuned
from tests.tools.factories import connect

LATE = EPOCH + 10


@pytest.fixture
async def session(tmp_path: Path, open_database: OpenDatabase) -> AsyncIterator[AsyncSession]:
    database: Database = open_database(tmp_path / "kinds.db")
    async with database.write() as found:
        yield found
    await database.dispose()


@pytest.fixture
async def cosmos(session: AsyncSession) -> Cosmos:
    return await seed_cosmos(session)


async def partners(session: AsyncSession, cosmos: Cosmos) -> tuple[EntityRow, EntityRow]:
    maker = await make_entity(session, "Orrin", EntityType.PEOPLE, PeopleStats(population=4000), world_id=cosmos.home.id)
    partner = await make_entity(session, "Vessa", EntityType.PEOPLE, PeopleStats(population=4000), world_id=cosmos.home.id)
    await connect(session, maker.id, partner.id, BondKind.TRADES_WITH)
    return maker, partner


async def held_good(session: AsyncSession, cosmos: Cosmos, holder: EntityRow, *, prestige: int = 0, since: int = EPOCH, strength: int = 100) -> GoodKindRow:
    good = GoodKindRow(
        name="Ember Loaf", category=GoodCategory.GRAIN, world_id=cosmos.home.id, origin_node_id=holder.id, prestige=prestige, created_epoch=0, locked=[]
    )
    session.add(good)
    await session.flush()
    session.add(
        KindHoldingRow(
            concept=KindConcept.GOOD, kind_id=good.id, holder_node_id=holder.id, stance=KindStance.MAKES, strength=strength, since_epoch=since, locked=[]
        )
    )
    await session.flush()
    return good


async def holding(session: AsyncSession, good: GoodKindRow, holder: EntityRow) -> KindHoldingRow | None:
    return await session.scalar(select(KindHoldingRow).where(KindHoldingRow.kind_id == good.id, KindHoldingRow.holder_node_id == holder.id))


def quiet(rules: Rules, **values: int) -> Rules:
    base = {"spread_pct": 0, "prestige_spread_pct": 0, "novelty_gain": 0, "novelty_fade": 0, "prestige_hold_pct": 0}
    return tuned(rules, "kinds", **{**base, **values})


async def test_a_kind_passes_to_a_trading_partner(session: AsyncSession, cosmos: Cosmos) -> None:
    maker, partner = await partners(session, cosmos)
    good = await held_good(session, cosmos, maker)
    tally = await keep_kinds(tick(session, quiet(Rules(), spread_pct=100)))
    taken = await holding(session, good, partner)
    assert tally.spread == 1
    assert taken is not None and taken.spread is KindSpread.TRADE and taken.stance is KindStance.USES


async def test_prestige_alone_carries_a_kind_and_a_plain_kind_stays(session: AsyncSession, cosmos: Cosmos) -> None:
    maker, partner = await partners(session, cosmos)
    plain = await held_good(session, cosmos, maker, prestige=0)
    await keep_kinds(tick(session, quiet(Rules(), prestige_spread_pct=200)))
    assert await holding(session, plain, partner) is None
    prized = await held_good(session, cosmos, maker, prestige=100)
    await keep_kinds(tick(session, quiet(Rules(), prestige_spread_pct=200)))
    assert await holding(session, prized, partner) is not None


async def test_a_new_kind_gains_strength_and_an_old_one_fades(session: AsyncSession, cosmos: Cosmos) -> None:
    maker, _ = await partners(session, cosmos)
    rules = quiet(Rules(), novelty_gain=6, novelty_fade=3, novelty_epochs=4)
    fresh = await held_good(session, cosmos, maker, since=LATE, strength=50)
    stale = await held_good(session, cosmos, maker, since=0, strength=50)
    tally = await keep_kinds(tick(session, rules, epoch=LATE))
    fresh_holding, stale_holding = await holding(session, fresh, maker), await holding(session, stale, maker)
    assert fresh_holding is not None and fresh_holding.strength == 56
    assert stale_holding is not None and stale_holding.strength == 47
    assert tally.faded == 1


async def test_an_unheld_kind_retires_and_a_built_in_one_stays(session: AsyncSession, cosmos: Cosmos) -> None:
    lost = GoodKindRow(name="Old Meal", category=GoodCategory.GRAIN, world_id=cosmos.home.id, created_epoch=0, locked=[])
    kept = GoodKindRow(name="Common Grain", category=GoodCategory.GRAIN, built_in=True, created_epoch=0, locked=[])
    session.add_all([lost, kept])
    await session.flush()
    tally = await keep_kinds(tick(session, quiet(Rules(), retire_epochs=1)))
    assert lost.retired and not kept.retired
    assert tally.retired == 1


async def test_a_held_people_neither_passes_nor_changes_its_kinds(session: AsyncSession, cosmos: Cosmos) -> None:
    maker, partner = await partners(session, cosmos)
    good = await held_good(session, cosmos, maker, since=0, strength=50)
    token = HELD_SCOPE.set(HeldScope(only=None, nodes=frozenset({maker.id})))
    try:
        await keep_kinds(tick(session, quiet(Rules(), spread_pct=100, novelty_fade=5), epoch=LATE))
    finally:
        HELD_SCOPE.reset(token)
    own = await holding(session, good, maker)
    assert own is not None and own.strength == 50
    assert await holding(session, good, partner) is None
