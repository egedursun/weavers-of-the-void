import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.stats import max_essence
from aerona.core.errors import ValidationFailedError
from aerona.db.tables.interconnect import IncidentRow
from aerona.engine.gods.essence import endow
from aerona.engine.gods.essence_flow import send_essence
from aerona.engine.gods.power import end_rebellion
from aerona.engine.phases.sons import rebel_theft
from aerona.rules.registry import Rules
from aerona.services.integrity.son_essence import fit_son_essence, sons_over_their_cap
from tests.engine.gods.factories import GodsWorld, make_context, make_son


async def told(session: AsyncSession, key: str) -> int:
    return int(await session.scalar(select(func.count(IncidentRow.id)).where(IncidentRow.kind == key)) or 0)


async def test_a_rebel_takes_from_the_creator_and_no_more_than_it_can_hold(session: AsyncSession, rules: Rules, world: GodsWorld) -> None:
    rebel = await make_son(session, "Tidekeeper", world.world.id, loyalty=10)
    rebel.rebel = True
    cap = max_essence(rules, rebel.might)
    rebel.essence = cap - 3
    world.creator.essence = 200
    await session.flush()
    await rebel_theft(make_context(session, rules, 10))
    assert rebel.essence == cap
    assert world.creator.essence == 197
    assert await told(session, "sons.rebel_theft") == 1


async def test_a_rebel_takes_nothing_from_an_empty_creator(session: AsyncSession, rules: Rules, world: GodsWorld) -> None:
    rebel = await make_son(session, "Tidekeeper", world.world.id, loyalty=10, essence=10)
    rebel.rebel = True
    world.creator.essence = 0
    await session.flush()
    await rebel_theft(make_context(session, rules, 10))
    assert rebel.essence == 10
    assert await told(session, "sons.rebel_theft") == 0


async def test_a_son_who_ends_the_rebellion_takes_nothing_more(session: AsyncSession, rules: Rules, world: GodsWorld) -> None:
    rebel = await make_son(session, "Tidekeeper", world.world.id, loyalty=10, essence=10)
    rebel.rebel = True
    world.creator.essence = 200
    await session.flush()
    ctx = make_context(session, rules, 10)
    await end_rebellion(ctx, world.creator, rebel, "I keep my word.")
    await rebel_theft(ctx)
    assert (rebel.rebel, rebel.essence, world.creator.essence) == (False, 10, 200)
    assert await told(session, "gods.power.rebellion_ended") == 1


async def test_essence_sent_to_the_creator_leaves_the_son_whole_and_reaches_the_creator(session: AsyncSession, rules: Rules, world: GodsWorld) -> None:
    son = await make_son(session, "Tidekeeper", world.world.id, essence=40)
    world.creator.essence = 50
    await session.flush()
    sent = await send_essence(make_context(session, rules, 10), son, world.creator, 26, "I return what I took.")
    assert sent == 26
    assert (son.essence, world.creator.essence) == (14, 76)
    assert await told(session, "gods.essence_sent") == 1


async def test_a_sibling_takes_only_what_it_can_hold_and_the_giver_keeps_the_least(session: AsyncSession, rules: Rules, world: GodsWorld) -> None:
    giver = await make_son(session, "Tidekeeper", world.world.id, essence=40)
    taker = await make_son(session, "Stormcaller", world.world.id, essence=10)
    taker.essence = max_essence(rules, taker.might) - 4
    await session.flush()
    ctx = make_context(session, rules, 10)
    assert await send_essence(ctx, giver, taker, 20) == 4
    assert taker.essence == max_essence(rules, taker.might)
    assert giver.essence == 36
    with pytest.raises(ValidationFailedError):
        await send_essence(ctx, giver, taker, 5)
    giver.essence = rules.son_tools.gift_min_remaining
    with pytest.raises(ValidationFailedError):
        await send_essence(ctx, giver, world.creator, 1)


async def test_every_gain_stops_at_the_son_cap(session: AsyncSession, rules: Rules, world: GodsWorld) -> None:
    son = await make_son(session, "Tidekeeper", world.world.id, essence=10)
    cap = max_essence(rules, son.might)
    assert endow(rules, son, cap) == cap - 10
    assert son.essence == cap
    assert endow(rules, world.creator, 500) == 500


async def test_a_son_left_over_the_cap_is_brought_back_to_it(session: AsyncSession, rules: Rules, world: GodsWorld) -> None:
    son = await make_son(session, "Tidekeeper", world.world.id, essence=10)
    son.essence = max_essence(rules, son.might) + 14
    await session.flush()
    assert await sons_over_their_cap(session) == [son.id]
    await fit_son_essence(session, son.id)
    assert son.essence == max_essence(rules, son.might)
    assert await sons_over_their_cap(session) == []
