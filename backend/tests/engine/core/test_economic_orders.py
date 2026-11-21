from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.culture import IdeologyAdherentRow, IdeologyTenetRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.estates import MovementProfileRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.orders import EconomicOrderRow, OrderTransitionRow
from aerona.db.tables.polity import PolityMemberRow, PolityProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.domain.enums.culture import IdeologyTenet
from aerona.domain.enums.economy import GoodsFlow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.faction import FactionKind, MovementCause
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.orders import AllocationMode, OrderLabour, OwnershipRegime, TransitionKind, TransitionStage
from aerona.domain.enums.polity import DecisionRule, GovernmentKind
from aerona.domain.enums.society import Commodity, SocialClass
from aerona.domain.models.entity_stats import FactionStats, IdeologyStats, PolityStats
from aerona.engine.orders.economy import OrderTally, advance, run_flows
from aerona.engine.orders.pressures import demand_of, press_orders
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.society import shift_stock, stock
from aerona.engine.recording.record import record
from tests.engine.core.factories import CoreWorld, entity, settlement, tuned_rules


async def ordered_realm(session: AsyncSession, world: CoreWorld, **axes: object) -> tuple[EntityRow, EconomicOrderRow, EntityRow]:
    town = await settlement(session, "Orderford", world, world.regions[0], population=3000)
    realm = await entity(session, "The Ordered Crown", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    session.add(
        PolityProfileRow(polity_entity_id=realm.id, government=next(iter(GovernmentKind)), decision_rule=next(iter(DecisionRule)), capital_entity_id=town.id)
    )
    session.add(PolityMemberRow(polity_entity_id=realm.id, member_entity_id=town.id))
    order = EconomicOrderRow(polity_entity_id=realm.id, locked=[], **axes)
    session.add(order)
    await session.flush()
    return realm, order, town


async def test_a_strong_movement_for_abolition_presses_a_bound_realm_toward_emancipation(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "abolition", tuned_rules(economic_orders={"demand_chance_pct": 100}))
    realm, order, _town = await ordered_realm(session, world, labour=OrderLabour.SERF)
    cause = await entity(session, "The Free Hands", EntityType.FACTION, FactionStats(), world_id=world.world.id)
    session.add(FactionProfileRow(faction_entity_id=cause.id, kind=FactionKind.MOVEMENT, influence_over={}, cohort_share={}, locked=[]))
    session.add(MovementProfileRow(faction_entity_id=cause.id, cause=MovementCause.ABOLITION, polity_entity_id=realm.id, support=80, locked=[]))
    await session.flush()
    assert await demand_of(ctx, realm.id, order) is TransitionKind.EMANCIPATION
    assert await press_orders(ctx, OrderTally()) == 1
    row = await session.scalar(select(OrderTransitionRow).where(OrderTransitionRow.polity_entity_id == realm.id))
    assert row is not None and row.kind is TransitionKind.EMANCIPATION


async def test_a_creed_of_trade_held_across_the_realm_presses_a_state_economy_toward_privatisation(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "creed", tuned_rules())
    realm, order, town = await ordered_realm(session, world, ownership=OwnershipRegime.STATE)
    creed = await entity(session, "The Open Ledger", EntityType.IDEOLOGY, IdeologyStats(), world_id=world.world.id)
    session.add(IdeologyTenetRow(ideology_entity_id=creed.id, tenet=IdeologyTenet.MERCANTILISM))
    session.add(IdeologyAdherentRow(ideology_entity_id=creed.id, adherent_entity_id=town.id))
    await session.flush()
    assert await demand_of(ctx, realm.id, order) is TransitionKind.PRIVATISATION


async def test_a_failed_plan_presses_a_commanded_economy_to_loosen(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "failure", tuned_rules())
    realm, order, town = await ordered_realm(session, world, allocation=AllocationMode.COMMAND)
    assert await demand_of(ctx, realm.id, order) is None
    await record(ctx, "economy.plan_shortfall", roles={IncidentRole.SUBJECT: realm.id, IncidentRole.VICTIM: [town.id]}, facts={"planning": 10, "floor": 30})
    assert await demand_of(ctx, realm.id, order) is TransitionKind.DECOLLECTIVISATION


async def test_a_realm_in_the_middle_of_a_change_is_not_pressed_into_another(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "busy", tuned_rules(economic_orders={"demand_chance_pct": 100}))
    realm, _order, _town = await ordered_realm(session, world, labour=OrderLabour.ENSLAVED, ownership=OwnershipRegime.RULER)
    session.add(OrderTransitionRow(polity_entity_id=realm.id, kind=TransitionKind.LAND_REFORM, from_axes={}, to_axes={}, locked=[]))
    await session.flush()
    assert await press_orders(ctx, OrderTally()) == 0


SOCIETY = {
    "share_farmer": 70.0,
    "share_artisan": 10.0,
    "share_merchant": 5.0,
    "share_priest": 3.0,
    "share_warrior": 4.0,
    "share_scribe": 2.0,
    "share_noble": 6.0,
    "share_serf_or_slave": 0.0,
    "share_outcast": 0.0,
    "share_monastic": 0.0,
    "stock_food": 0,
    "stock_ore": 0,
    "stock_goods": 0,
    "price_food": 1.0,
    "price_ore": 1.0,
    "price_goods": 1.0,
}
SATISFIED = {f"satisfaction_{item.value}": 60 for item in SocialClass}


async def test_story_the_granary_and_the_plan(session: AsyncSession, world: CoreWorld) -> None:
    plan = {"redistribution_share": 100, "redistribution_storage_loss_pct": 40, "fail_from": 50, "transition_stage_years": 1}
    rules = tuned_rules(economic_orders=plan)
    ctx = await manual_context(session, "granary", rules)
    realm, order, capital = await ordered_realm(session, world, allocation=AllocationMode.REDISTRIBUTION)
    far = await settlement(session, "Farfield", world, world.regions[1], population=200)
    session.add_all(CommunitySocietyRow(entity_id=town.id, **SOCIETY, **SATISFIED) for town in (capital, far))
    session.add(PolityMemberRow(polity_entity_id=realm.id, member_entity_id=far.id))
    profile = await session.get(PolityProfileRow, realm.id)
    assert profile is not None
    profile.treasury = 10000
    await session.flush()
    await shift_stock(session, ctx.rules, far.id, Commodity.FOOD, 500, epoch=ctx.epoch, flow=GoodsFlow.EXTRACTION)
    tally = OrderTally()
    await run_flows(ctx, order, profile, [capital.id, far.id], tally)
    kept_far = await stock(session, ctx.rules, far.id, Commodity.FOOD)
    assert tally.redistributed > 0 and kept_far < 1000 and await stock(session, ctx.rules, capital.id, Commodity.FOOD) > 0
    assert kept_far + await stock(session, ctx.rules, capital.id, Commodity.FOOD) < 1000
    transition = OrderTransitionRow(
        polity_entity_id=realm.id,
        kind=TransitionKind.LAND_REFORM,
        from_axes={},
        to_axes={},
        stage=TransitionStage.TRANSFERRING,
        resistance=90,
        started_epoch=0,
        locked=[],
    )
    session.add(transition)
    await session.flush()
    await advance(ctx, transition, tally)
    assert transition.stage is TransitionStage.FAILED and tally.failed == 1
    assert await session.scalar(select(IncidentRow.id).where(IncidentRow.kind == "economy.transition_failed")) is not None
