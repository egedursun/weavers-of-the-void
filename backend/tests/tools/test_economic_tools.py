from sqlalchemy import select

from aerona.db.session import Database
from aerona.db.tables.orders import EconomicOrderRow, ExchangeRateRow, OrderTransitionRow
from aerona.domain.enums.modifier import ModifierOp, ModifierSource
from aerona.domain.enums.orders import AllocationMode, DistributionRule, OrderLabour, OwnershipRegime
from aerona.engine.interconnect.registry import suppression_key
from aerona.engine.primitives.modifiers import ModifierDraft, add_modifier
from tests.tools.every_setup import ruled_realm
from tests.tools.every_setup_means import money_changer
from tests.tools.factories import EPOCH, Realm, mortal_toolkit, seed_realm, son_toolkit
from tests.tools.test_mortal_tools import ok, rejected
from tests.tools.test_son_tools import ok as son_ok
from tests.tools.test_son_tools import rejected as son_rejected

REASON = "to feed the realm through the lean years"
MARKET_ORDER = {"ownership": "private", "allocation": "market", "labour": "free", "distribution": "by_holding"}


async def realm_ruled_by_the_mortal(database: Database) -> tuple[Realm, int]:
    realm = await seed_realm(database)
    async with database.write() as session:
        found = await ruled_realm(session, realm)
    return realm, found["polity"]


async def hold(database: Database, node_id: int, mechanic: str) -> None:
    async with database.write() as session:
        await add_modifier(
            session, ModifierDraft(node_id, suppression_key(mechanic), ModifierOp.ADD, 0, ModifierSource.SUPPRESSION, "player.suppression", start_epoch=EPOCH)
        )


async def test_only_the_ruler_of_a_realm_may_set_its_economic_order(database: Database) -> None:
    realm, polity = await realm_ruled_by_the_mortal(database)
    stranger = await mortal_toolkit(database, realm.people_id)
    text = await rejected(stranger, "set_economic_order", {"polity_id": polity, **MARKET_ORDER, "reason": REASON})
    assert "you do not rule" in text
    missing = await rejected(
        await mortal_toolkit(database, realm.mortal_id), "set_economic_order", {"polity_id": realm.settlement_id, **MARKET_ORDER, "reason": REASON}
    )
    assert "there is no such realm" in missing


async def test_a_ruler_cannot_move_an_axis_of_the_order_the_god_has_locked(database: Database) -> None:
    realm, polity = await realm_ruled_by_the_mortal(database)
    async with database.write() as session:
        session.add(
            EconomicOrderRow(
                polity_entity_id=polity,
                ownership=OwnershipRegime.PRIVATE,
                allocation=AllocationMode.REDISTRIBUTION,
                labour=OrderLabour.FREE,
                distribution=DistributionRule.BY_HOLDING,
                locked=["allocation"],
            )
        )
    toolkit = await mortal_toolkit(database, realm.mortal_id)
    text = await rejected(toolkit, "set_economic_order", {"polity_id": polity, **MARKET_ORDER, "reason": REASON})
    assert "held fast" in text
    same = {**MARKET_ORDER, "allocation": "redistribution", "labour": "corvee"}
    await ok(toolkit, "set_economic_order", {"polity_id": polity, **same, "reason": REASON})
    async with database.read() as session:
        order = await session.scalar(select(EconomicOrderRow).where(EconomicOrderRow.polity_entity_id == polity))
    assert order is not None and order.allocation is AllocationMode.REDISTRIBUTION and order.labour is OrderLabour.CORVEE


async def test_a_realm_holds_one_change_of_order_at_a_time_and_no_empty_ones(database: Database) -> None:
    realm, polity = await realm_ruled_by_the_mortal(database)
    toolkit = await mortal_toolkit(database, realm.mortal_id, action_points=6)
    arguments = {"polity_id": polity, "kind": "land_reform", "compensation": "partial", "reason": REASON}
    await ok(toolkit, "begin_transition", arguments)
    text = await rejected(toolkit, "begin_transition", {**arguments, "kind": "nationalisation"})
    assert "already" in text
    async with database.read() as session:
        open_rows = list(await session.scalars(select(OrderTransitionRow).where(OrderTransitionRow.polity_entity_id == polity)))
    assert len(open_rows) == 1


async def test_a_held_realm_refuses_every_economic_tool(database: Database) -> None:
    realm, polity = await realm_ruled_by_the_mortal(database)
    await hold(database, polity, "economic_orders")
    mortal = await mortal_toolkit(database, realm.mortal_id)
    for name, arguments in (
        ("set_economic_order", {"polity_id": polity, **MARKET_ORDER, "reason": REASON}),
        ("begin_transition", {"polity_id": polity, "kind": "land_reform", "compensation": "none", "reason": REASON}),
    ):
        assert "a stronger hand holds that realm" in await rejected(mortal, name, arguments)
    son = await son_toolkit(database, realm.son_id, action_points=6)
    assert "a stronger hand holds that realm" in await son_rejected(
        son, "move_economic_order", {"polity_id": polity, "axis": "allocation", "value": "command", "reason": REASON}
    )


async def test_a_son_moves_one_axis_only_to_a_value_it_can_hold(database: Database) -> None:
    realm, polity = await realm_ruled_by_the_mortal(database)
    son = await son_toolkit(database, realm.son_id, action_points=6)
    text = await son_rejected(son, "move_economic_order", {"polity_id": polity, "axis": "allocation", "value": "serfdom", "reason": REASON})
    assert "allocation may be" in text and "command" in text
    await son_ok(son, "move_economic_order", {"polity_id": polity, "axis": "labour", "value": "serf", "reason": REASON})


async def test_money_is_changed_only_by_the_skilled_at_a_free_market(database: Database) -> None:
    realm = await seed_realm(database)
    unskilled = await mortal_toolkit(database, realm.mortal_id)
    assert "accounting" in await rejected(unskilled, "change_money", {})
    async with database.write() as session:
        await money_changer(session, realm)
    await hold(database, realm.settlement_id, "exchange")
    held_market = await mortal_toolkit(database, realm.mortal_id)
    assert "a stronger hand holds" in await rejected(held_market, "change_money", {})
    async with database.read() as session:
        rate = await session.scalar(select(ExchangeRateRow))
    assert rate is not None and rate.changer_node_id is None
