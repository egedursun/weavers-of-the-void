from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.gift_occasions import GIFT_STATES, HOLDING, OCCASIONS
from aerona.db.tables.cycles import CircuitRow, GiftRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.military import FeudRow
from aerona.domain.enums.cycles import GiftOccasion, GiftState
from aerona.domain.enums.military import FeudStatus
from aerona.engine.cycles.gifts import GiftTally, amends, give, owed_back, pass_circuit, release_gift_debt, return_gift
from aerona.engine.economy.purse import coin_of
from aerona.engine.lore.taboos import guest_killed
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, mortal
from tests.engine.core.test_cycles_w21 import context, realm_of, town_of

RULES = Rules()
OPEN_HANDED = {"return_years": 50, "refuse_below": -100, "outgive_pct": 0}


async def state_of(session: AsyncSession, gift_id: int) -> GiftState | None:
    return await session.scalar(select(GiftRow.state).where(GiftRow.id == gift_id))


async def kinds(session: AsyncSession) -> set[str]:
    return set(await session.scalars(select(IncidentRow.kind)))


def test_every_occasion_and_state_has_its_catalogue_entry_and_the_occasion_sets_the_debt() -> None:
    assert set(OCCASIONS) == set(GiftOccasion) and set(GIFT_STATES) == set(GiftState)
    assert OCCASIONS[GiftOccasion.AMENDS].debt(RULES) == 0 and OCCASIONS[GiftOccasion.PATRONAGE].debt(RULES) == 0
    assert OCCASIONS[GiftOccasion.FUNERAL].debt(RULES) > 0 and OCCASIONS[GiftOccasion.HOSPITALITY].debt(RULES) > 0
    assert GiftState.PASSED_ON not in HOLDING and GiftState.OPEN in HOLDING


async def test_occasions_set_what_is_owed_and_a_funeral_gift_waits_for_the_givers_loss(session: AsyncSession, world: CoreWorld) -> None:
    first = await realm_of(session, world, await town_of(session, world, "Ashby"), treasury=1000)
    second = await realm_of(session, world, await town_of(session, world, "Farside", region=1), treasury=1000)
    ctx = await context(session, reciprocity=OPEN_HANDED)
    patron = await give(ctx, first.id, second.id, 50, GiftOccasion.PATRONAGE, tell=True)
    assert patron is not None and patron.state is GiftState.RETURNED
    funeral = await give(ctx, first.id, second.id, 40, GiftOccasion.FUNERAL, tell=True)
    assert funeral is not None and funeral.state is GiftState.OPEN and funeral.due_epoch is None
    birth = await give(ctx, first.id, second.id, 40, GiftOccasion.BIRTH)
    assert birth is not None and owed_back(ctx.rules, birth) == 40 * ctx.rules.gifts.birth_debt // 100
    assert {"gift.given", "gift.given_freely"} <= await kinds(session)


async def test_an_answer_of_far_more_exceeds_the_gift_and_outgiving_drains_both_houses(session: AsyncSession, world: CoreWorld) -> None:
    first = await realm_of(session, world, await town_of(session, world, "Ashby"), treasury=5000)
    second = await realm_of(session, world, await town_of(session, world, "Farside", region=1), treasury=5000)
    ctx = await context(session, reciprocity=OPEN_HANDED, gifts={"rivalry_drain_pct": 10})
    gift = await give(ctx, first.id, second.id, 100, GiftOccasion.COURTESY)
    assert gift is not None
    answer = await return_gift(ctx, gift, value=150)
    assert answer is not None and gift.state is GiftState.EXCEEDED and answer.state is GiftState.OPEN
    before = await coin_of(session, ctx.rules, first)
    again = await return_gift(ctx, answer, value=250)
    assert again is not None and await state_of(session, answer.id) is GiftState.EXCEEDED
    assert await coin_of(session, ctx.rules, first) < before
    rivalry = await session.scalars(select(IncidentRow).where(IncidentRow.kind == "gift.exceeded"))
    assert len(list(rivalry)) == 2


async def test_a_giver_may_release_a_debt_by_grace(session: AsyncSession, world: CoreWorld) -> None:
    first = await realm_of(session, world, await town_of(session, world, "Ashby"), treasury=1000)
    second = await realm_of(session, world, await town_of(session, world, "Farside", region=1), treasury=1000)
    ctx = await context(session, reciprocity=OPEN_HANDED)
    gift = await give(ctx, first.id, second.id, 60, GiftOccasion.COURTESY)
    assert gift is not None and await release_gift_debt(ctx, gift)
    assert gift.state is GiftState.RELEASED and not await release_gift_debt(ctx, gift)
    assert "gift.released" in await kinds(session)


async def test_a_circuit_gift_is_passed_on_to_the_next_stop(session: AsyncSession, world: CoreWorld) -> None:
    towns = [await town_of(session, world, name, region=index % 2) for index, name in enumerate(("Ashby", "Farside", "Kell"))]
    circuit = CircuitRow(name="the ring", item_entity_id=None, stops=[town.id for town in towns], position=0, passes=0, started_epoch=1, locked=[])
    session.add(circuit)
    await session.flush()
    ctx = await context(session)
    assert await pass_circuit(ctx, circuit, GiftTally())
    assert await pass_circuit(ctx, circuit, GiftTally())
    gifts = list(await session.scalars(select(GiftRow).order_by(GiftRow.id)))
    assert gifts[0].state is GiftState.PASSED_ON and gifts[0].circuit_id == circuit.id
    assert "gift.passed_on" in await kinds(session)


async def test_accepted_amends_end_a_feud(session: AsyncSession, world: CoreWorld) -> None:
    first = await realm_of(session, world, await town_of(session, world, "Ashby"), treasury=1000)
    second = await realm_of(session, world, await town_of(session, world, "Farside", region=1), treasury=1000)
    feud = FeudRow(first_entity_id=first.id, second_entity_id=second.id, intensity=40, grievance=40, status=FeudStatus.ACTIVE, locked=[])
    session.add(feud)
    await session.flush()
    ctx = await context(session, reciprocity=OPEN_HANDED, gifts={"amends_pct": 100, "amends_grievance_cut": 60})
    tally = GiftTally()
    await amends(ctx, tally)
    assert tally.amends == 1 and feud.grievance == 0
    gift = await session.scalar(select(GiftRow).where(GiftRow.occasion == GiftOccasion.AMENDS))
    assert gift is not None and gift.giver_node_id == second.id


async def test_killing_after_guest_gifts_breaks_guest_right(session: AsyncSession, world: CoreWorld) -> None:
    town = await town_of(session, world, "Ashby")
    host = await mortal(session, "Host", world, town.id)
    guest = await mortal(session, "Guest", world, town.id)
    ctx = await context(session, reciprocity=OPEN_HANDED)
    assert await give(ctx, host.id, guest.id, 0, GiftOccasion.HOSPITALITY, pay=False) is not None
    await guest_killed(ctx, host.id, guest)
    assert "lore.guest_killing" in await kinds(session)
