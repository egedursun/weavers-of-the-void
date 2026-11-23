from sqlalchemy import select

from aerona.catalog.orders import DONE_CONDITIONS, ORDER_CONDITIONS, ORDER_LITERALNESS, ORDER_TIMES, TIMED_CONDITIONS
from aerona.db.tables.celestial import SkyEventRow
from aerona.db.tables.constructs import ConstructRow, InstructionOrderRow, InstructionSetRow
from aerona.db.tables.ecology import BeastProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.intrigue import TrueNameRow
from aerona.domain.enums.constructs import CommandToken, OrderCondition, OrderKind, OrderTime
from aerona.domain.enums.ecology import BeastTemper
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.society import Commodity
from aerona.domain.enums.world import SkyEventKind
from aerona.domain.models.entity_stats import BeastStats
from aerona.engine.constructs.orders import Charge, OrderTally, holds, obey, resolve_holder
from aerona.engine.primitives.society import stock
from aerona.services.integrity.w52_agent_a import command_by_word, nameless_commands, run_by_day, untimed_orders
from tests.engine.society.factories import Realm, context, make, mortal, tuned
from tests.engine.society.test_society_depth import stocked_town


async def built(realm: Realm, maker: EntityRow) -> tuple[EntityRow, ConstructRow, InstructionSetRow]:
    body = await make(realm.session, "Clay worker", EntityType.BEAST, BeastStats(hp=60), world_id=realm.world.id, location_id=realm.region.id)
    realm.session.add(BeastProfileRow(beast_entity_id=body.id, temper=BeastTemper.BOUND, bound_to_node_id=maker.id, lifespan=1_000_000, hoard={}, locked=[]))
    row = ConstructRow(entity_id=body.id, maker_entity_id=maker.id, locked=[])
    rules = InstructionSetRow(owner_entity_id=body.id, command_token=CommandToken.WORD, holder_node_id=maker.id, locked=[])
    realm.session.add_all([row, rules])
    await realm.session.flush()
    return body, row, rules


def test_every_order_kind_reads_its_literalness_and_the_new_conditions_their_traits() -> None:
    rules = tuned(instructions={"carry_literalness": 40})
    assert ORDER_LITERALNESS[OrderKind.CARRY](rules) == 40 and ORDER_LITERALNESS[OrderKind.TEND](rules) > 0
    assert OrderCondition.UNTIL_DONE in DONE_CONDITIONS and OrderCondition.AT_SET_TIMES in TIMED_CONDITIONS
    assert ORDER_CONDITIONS[OrderCondition.UNTIL_DONE].ends_when_done and ORDER_TIMES[OrderTime.SKY_EVENT].sky


async def test_carrying_and_tending_fill_the_stores_and_an_order_until_done_lapses_when_nothing_is_left(realm: Realm) -> None:
    session = realm.session
    maker = await mortal(realm, "Maker")
    town = await stocked_town(realm, "Kiln")
    body, row, rules = await built(realm, maker)
    session.add(InstructionOrderRow(set_id=rules.id, kind=OrderKind.CARRY, target_node_id=town.id, condition=OrderCondition.ALWAYS, locked=[]))
    session.add(InstructionOrderRow(set_id=rules.id, kind=OrderKind.TEND, target_node_id=town.id, condition=OrderCondition.ALWAYS, locked=[]))
    session.add(InstructionOrderRow(set_id=rules.id, kind=OrderKind.BUILD, target_node_id=town.id, condition=OrderCondition.UNTIL_DONE, locked=[]))
    await session.flush()
    ctx = context(session, tuned(instructions={"carry_goods": 5, "tend_food": 6}))
    tally = OrderTally()
    await obey(ctx, body, row, rules, tally)
    goods, food = await stock(session, ctx.rules, town.id, Commodity.GOODS), await stock(session, ctx.rules, town.id, Commodity.FOOD)
    await obey(ctx, body, row, rules, tally)
    assert await stock(session, ctx.rules, town.id, Commodity.GOODS) == goods + 5
    assert await stock(session, ctx.rules, town.id, Commodity.FOOD) == food + 6
    build = await session.scalar(select(InstructionOrderRow).where(InstructionOrderRow.kind == OrderKind.BUILD))
    assert build is not None and build.lapsed and tally.lapsed == 1
    told = await session.scalar(select(IncidentRow).where(IncidentRow.kind == "orders.lapsed").limit(1))
    assert told is not None


async def test_an_order_kept_at_a_sign_runs_only_then(realm: Realm) -> None:
    session = realm.session
    maker = await mortal(realm, "Maker")
    body, row, rules = await built(realm, maker)
    order = InstructionOrderRow(set_id=rules.id, kind=OrderKind.GUARD, condition=OrderCondition.AT_SET_TIMES, times=OrderTime.SKY_EVENT, locked=[])
    session.add(order)
    await session.flush()
    ctx = context(session, epoch=4)
    charge = Charge(body, row, rules, order, None, maker)
    assert not await holds(ctx, charge)
    session.add(SkyEventRow(kind=SkyEventKind.COMET, epoch=4, world_id=realm.world.id))
    await session.flush()
    assert await holds(ctx, charge)


async def test_one_who_knows_a_made_thing_s_true_name_commands_it(realm: Realm) -> None:
    session = realm.session
    maker, thief = await mortal(realm, "Maker"), await mortal(realm, "Thief")
    body, _row, rules = await built(realm, maker)
    session.add(TrueNameRow(bearer_node_id=body.id, name="Orr", known_by=[thief.id], since_epoch=1, locked=[]))
    await session.flush()
    holder = await resolve_holder(context(session), body, rules, OrderTally())
    assert holder is not None and holder.id == thief.id
    told = await session.scalar(select(IncidentRow).where(IncidentRow.kind == "orders.seized").limit(1))
    assert told is not None


async def test_a_timed_order_without_times_runs_by_day_and_a_nameless_true_name_token_falls_to_a_word(realm: Realm) -> None:
    session = realm.session
    maker = await mortal(realm, "Maker")
    _body, _row, rules = await built(realm, maker)
    order = InstructionOrderRow(set_id=rules.id, kind=OrderKind.GUARD, condition=OrderCondition.AT_SET_TIMES, locked=[])
    session.add(order)
    rules.command_token = CommandToken.TRUE_NAME
    await session.flush()
    assert await untimed_orders(session) == [order.id]
    await run_by_day(session, order.id)
    assert order.times is OrderTime.DAY
    assert await nameless_commands(session) == [rules.id]
    await command_by_word(session, rules.id)
    assert rules.command_token is CommandToken.WORD
