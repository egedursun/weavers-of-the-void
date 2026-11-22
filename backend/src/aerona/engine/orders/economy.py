import math
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.faction_kinds import of_kinds
from aerona.db.record_context import Term
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.economy import ResourceProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.households import HouseholdRow
from aerona.db.tables.orders import AXES, EconomicOrderKindRow, EconomicOrderRow, OrderTransitionRow
from aerona.db.tables.polity import OfficeRow, PolityMemberRow, PolityProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.economy import GoodsFlow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.faction import LENDER_KINDS, FactionKind
from aerona.domain.enums.loops import BalanceLoop
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.orders import (
    AllocationMode,
    Compensation,
    DistributionRule,
    OrderLabour,
    OwnershipRegime,
    TransitionKind,
    TransitionStage,
)
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.records import StepAction, StepLocus
from aerona.domain.enums.society import Commodity, KnowledgeBranch, SocialClass
from aerona.domain.enums.structure import StructureKind
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import give_coin, take_coin
from aerona.engine.loops.delay import lagged
from aerona.engine.polity.laws import law_param
from aerona.engine.primitives.knowledge import branch_level
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import connect
from aerona.engine.primitives.society import shift_stock, stock
from aerona.engine.primitives.stats import shift_stat, stat_or
from aerona.engine.recording.record import StepDraft, record
from aerona.engine.structures.damage import open_siege

C = SocialClass
OWN = OwnershipRegime
A = AllocationMode
L = OrderLabour
D = DistributionRule
BUILT_IN = (
    ("Market order", OWN.HOUSEHOLD, A.MARKET, L.FREE, D.BY_HOLDING),
    ("Redistributive order", OWN.TEMPLE, A.REDISTRIBUTION, L.CORVEE, D.BY_OFFICE),
    ("Command order", OWN.STATE, A.COMMAND, L.CONSCRIPTED, D.BY_OFFICE),
    ("Manorial order", OWN.RULER, A.OBLIGATION, L.SERF, D.BY_HOLDING),
    ("Gift order", OWN.KIN_GROUP, A.GIFT, L.KIN, D.BY_PRESTIGE),
)
FAVOURED: MappingProxyType[DistributionRule, tuple[frozenset[SocialClass], frozenset[SocialClass]]] = MappingProxyType(
    {
        D.BY_HOLDING: (frozenset({C.NOBLE, C.MERCHANT}), frozenset({C.SERF_OR_SLAVE, C.WORKER, C.FARMER})),
        D.BY_OFFICE: (frozenset({C.OFFICIAL, C.SCRIBE, C.PRIEST, C.NOBLE}), frozenset({C.MERCHANT})),
        D.BY_NEED: (frozenset({C.SERF_OR_SLAVE, C.UNEMPLOYED, C.OUTCAST, C.WORKER}), frozenset({C.NOBLE, C.MERCHANT})),
        D.BY_WORK: (frozenset({C.WORKER, C.ARTISAN, C.FARMER}), frozenset({C.NOBLE})),
        D.BY_SHARE: (frozenset({C.MERCHANT, C.PROFESSIONAL}), frozenset({C.WORKER})),
        D.EQUAL: (frozenset({C.SERF_OR_SLAVE, C.WORKER, C.FARMER, C.UNEMPLOYED, C.OUTCAST}), frozenset({C.NOBLE, C.MERCHANT, C.OFFICIAL})),
        D.BY_PRESTIGE: (frozenset({C.NOBLE, C.WARRIOR, C.PRIEST}), frozenset({C.OUTCAST})),
    }
)
AXIS_ENUMS: MappingProxyType[str, type[OwnershipRegime] | type[AllocationMode] | type[OrderLabour] | type[DistributionRule]] = MappingProxyType(
    {"ownership": OwnershipRegime, "allocation": AllocationMode, "labour": OrderLabour, "distribution": DistributionRule}
)
BOUND_LABOUR = frozenset({L.CORVEE, L.SERF, L.BOUND, L.ENSLAVED, L.CONSCRIPTED})
FREE_LABOUR = frozenset({L.FREE, L.COOPERATIVE})
CENTRES = frozenset({A.REDISTRIBUTION, A.OBLIGATION})
SHARING = frozenset({A.NEED, A.ABUNDANCE})
TARGETS: MappingProxyType[TransitionKind, dict[str, str]] = MappingProxyType(
    {
        TransitionKind.COLLECTIVISATION: {"ownership": OWN.COOPERATIVE.value},
        TransitionKind.NATIONALISATION: {"ownership": OWN.STATE.value},
        TransitionKind.PRIVATISATION: {"ownership": OWN.PRIVATE.value, "allocation": A.MARKET.value},
        TransitionKind.LAND_REFORM: {"ownership": OWN.HOUSEHOLD.value},
        TransitionKind.ENCLOSURE: {"ownership": OWN.PRIVATE.value},
        TransitionKind.EMANCIPATION: {"labour": L.FREE.value},
        TransitionKind.DECOLLECTIVISATION: {"ownership": OWN.HOUSEHOLD.value},
        TransitionKind.RESTORATION_OF_HOLDINGS: {},
    }
)
STORES = frozenset({StructureKind.TEMPLE, StructureKind.PALACE, StructureKind.GRANARY})


@dataclass
class OrderTally:
    kinds: int = 0
    orders: int = 0
    redistributed: int = 0
    dues: int = 0
    shared: int = 0
    shortfalls: int = 0
    collapses: int = 0
    stages: int = 0
    transferred: int = 0
    resisted: int = 0
    done: int = 0
    failed: int = 0


def axes_of(row: EconomicOrderRow | EconomicOrderKindRow) -> dict[str, str]:
    return {axis: getattr(row, axis).value for axis in AXES}


async def seed_kinds(ctx: TickContext, tally: OrderTally) -> None:
    if await ctx.session.scalar(select(func.count()).select_from(EconomicOrderKindRow).where(EconomicOrderKindRow.built_in.is_(True))):
        return
    for name, ownership, allocation, labour, distribution in BUILT_IN:
        ctx.session.add(
            EconomicOrderKindRow(name=name, ownership=ownership, allocation=allocation, labour=labour, distribution=distribution, built_in=True, locked=[])
        )
        tally.kinds += 1
    await ctx.session.flush()


async def kind_matching(ctx: TickContext, axes: dict[str, str]) -> int | None:
    for kind in await ctx.session.scalars(select(EconomicOrderKindRow).order_by(EconomicOrderKindRow.id)):
        if axes_of(kind) == axes:
            return kind.id
    return None


async def towns_of_realm(ctx: TickContext, polity_id: int) -> list[int]:
    return sorted(set(await ctx.session.scalars(select(PolityMemberRow.member_entity_id).where(PolityMemberRow.polity_entity_id == polity_id))))


async def read_order(ctx: TickContext, realm: PolityProfileRow) -> dict[str, str]:
    towns = await towns_of_realm(ctx, realm.polity_entity_id)
    anchor = realm.capital_entity_id or (towns[0] if towns else realm.polity_entity_id)
    serfdom = await law_param(ctx.session, anchor, LawKind.SERFDOM, "allowed")
    slavery = await law_param(ctx.session, anchor, LawKind.SLAVERY, "status")
    stores = await ctx.session.scalar(
        select(StructureProfileRow.structure_entity_id)
        .where(StructureProfileRow.host_entity_id.in_(towns or [anchor]), StructureProfileRow.kind.in_(list(STORES)))
        .limit(1)
    )
    guilds = await ctx.session.scalar(
        select(EntityRow.id).where(of_kinds(LENDER_KINDS), EntityRow.status == EntityStatus.CANON, EntityRow.location_id.in_(towns or [anchor])).limit(1)
    )
    allocation = A.REDISTRIBUTION if stores is not None and guilds is None else A.MARKET
    labour = L.SERF if serfdom else L.ENSLAVED if slavery not in {None, "banned"} else L.CORVEE if allocation is A.REDISTRIBUTION else L.FREE
    ownership = OWN.TEMPLE if allocation is A.REDISTRIBUTION else OWN.RULER if labour is L.SERF else OWN.HOUSEHOLD
    distribution = D.BY_OFFICE if allocation is A.REDISTRIBUTION else D.BY_HOLDING
    return {"ownership": ownership.value, "allocation": allocation.value, "labour": labour.value, "distribution": distribution.value}


async def seed_orders(ctx: TickContext, tally: OrderTally) -> None:
    ordered = set(await ctx.session.scalars(select(EconomicOrderRow.polity_entity_id).where(EconomicOrderRow.sector.is_(None))))
    for realm in list(await ctx.session.scalars(select(PolityProfileRow).order_by(PolityProfileRow.polity_entity_id))):
        if realm.polity_entity_id in ordered or held(realm.polity_entity_id):
            continue
        axes = await read_order(ctx, realm)
        ctx.session.add(
            EconomicOrderRow(
                polity_entity_id=realm.polity_entity_id,
                ownership=OWN(axes["ownership"]),
                allocation=A(axes["allocation"]),
                labour=L(axes["labour"]),
                distribution=D(axes["distribution"]),
                kind_id=await kind_matching(ctx, axes),
                since_epoch=ctx.epoch,
                locked=[],
            )
        )
        tally.orders += 1
    await ctx.session.flush()


async def planning_of(ctx: TickContext, order: EconomicOrderRow) -> int:
    officials = await ctx.session.scalar(
        select(func.count()).select_from(OfficeRow).where(OfficeRow.polity_entity_id == order.polity_entity_id, OfficeRow.holder_entity_id.is_not(None))
    )
    realm = await ctx.session.get(PolityProfileRow, order.polity_entity_id)
    records = await branch_level(ctx.session, realm.capital_entity_id, KnowledgeBranch.WRITING) if realm is not None and realm.capital_entity_id else 0
    return clamp_int(
        int(officials or 0) * ctx.rules.economic_orders.planning_per_official + records * ctx.rules.economic_orders.planning_per_record, 0, PERCENT
    )


def nudge(society: CommunitySocietyRow, social_class: SocialClass, amount: int) -> None:
    key = f"satisfaction_{social_class.value}"
    setattr(society, key, clamp_int(int(getattr(society, key)) + amount, 0, PERCENT))


async def share_out(ctx: TickContext, order: EconomicOrderRow, towns: list[int]) -> None:
    shift = ctx.rules.economic_orders.class_shift
    favoured, spared = FAVOURED[order.distribution]
    for town_id in towns:
        society = await ctx.session.get(CommunitySocietyRow, town_id)
        if society is None or held(town_id):
            continue
        for social_class in favoured:
            nudge(society, social_class, shift)
        for social_class in spared:
            nudge(society, social_class, -shift)
        if order.labour in BOUND_LABOUR:
            nudge(society, C.SERF_OR_SLAVE, -shift)
        elif order.labour in FREE_LABOUR:
            nudge(society, C.WORKER, shift)


async def centre_fallen(ctx: TickContext, realm: PolityProfileRow) -> bool:
    return realm.capital_entity_id is None or await open_siege(ctx.session, realm.capital_entity_id) is not None


async def collapse(ctx: TickContext, realm: EntityRow, towns: list[int], tally: OrderTally) -> None:
    for town_id in towns:
        town = await ctx.session.get(EntityRow, town_id)
        if town is not None and not held(town_id):
            shift_stat(town, "prosperity", -ctx.rules.economic_orders.centre_collapse_spread_pct // 10, ctx.rules.society.default_stat)
    tally.collapses += 1
    await record(ctx, "economy.centre_collapsed", roles={IncidentRole.SUBJECT: realm.id, IncidentRole.VICTIM: towns}, facts={"towns": len(towns)})


async def gather(ctx: TickContext, centre: int, towns: list[int], share: int, *, loss: int) -> int:
    gathered = 0
    for town_id in towns:
        if town_id == centre or held(town_id):
            continue
        sent = (await stock(ctx.session, ctx.rules, town_id, Commodity.FOOD)) * share // PERCENT
        if sent > 0 and await shift_stock(ctx.session, ctx.rules, town_id, Commodity.FOOD, -sent, epoch=ctx.epoch, flow=GoodsFlow.TRIBUTE):
            gathered += sent
    kept = gathered * (PERCENT - loss) // PERCENT
    if kept > 0:
        await shift_stock(ctx.session, ctx.rules, centre, Commodity.FOOD, kept, epoch=ctx.epoch, flow=GoodsFlow.TRIBUTE)
    return kept


async def give_out(ctx: TickContext, centre: int, towns: list[int], amount: int) -> int:
    people = {town_id: (await ctx.session.get(EntityRow, town_id)) for town_id in towns}
    weights = {town_id: max(1, stat_or(row, "population", 1)) for town_id, row in people.items() if row is not None and not held(town_id)}
    summed = sum(weights.values())
    given = 0
    for town_id, weight in sorted(weights.items()):
        part = amount * weight // max(1, summed)
        if part > 0 and town_id != centre and await shift_stock(ctx.session, ctx.rules, centre, Commodity.FOOD, -part, epoch=ctx.epoch, flow=GoodsFlow.AID):
            await shift_stock(ctx.session, ctx.rules, town_id, Commodity.FOOD, part, epoch=ctx.epoch, flow=GoodsFlow.AID)
            given += part
    return given


async def afford_centre(ctx: TickContext, realm: PolityProfileRow, towns: int) -> bool:
    cost = await lagged(ctx, BalanceLoop.REDISTRIBUTION_COLLAPSE, realm.polity_entity_id, towns * ctx.rules.economic_orders.redistribution_upkeep)
    if "treasury" in realm.locked:
        return True
    if realm.treasury < cost:
        realm.treasury = 0
        return cost <= 0
    realm.treasury -= cost
    return True


async def run_flows(ctx: TickContext, order: EconomicOrderRow, realm: PolityProfileRow, towns: list[int], tally: OrderTally) -> None:
    table = ctx.rules.economic_orders
    entity = await ctx.session.get(EntityRow, order.polity_entity_id)
    if entity is None:
        return
    centre = realm.capital_entity_id
    if order.allocation in CENTRES and await centre_fallen(ctx, realm):
        await collapse(ctx, entity, towns, tally)
        return
    if order.allocation is A.REDISTRIBUTION and centre is not None:
        if not await afford_centre(ctx, realm, len(towns)):
            await collapse(ctx, entity, towns, tally)
            return
        gathered = await gather(ctx, centre, towns, table.redistribution_share, loss=table.redistribution_storage_loss_pct)
        tally.redistributed += await give_out(ctx, centre, towns, gathered)
    elif order.allocation is A.OBLIGATION and centre is not None:
        tally.dues += await gather(ctx, centre, towns, table.dues_share, loss=0)
    elif order.allocation in SHARING and centre is not None:
        gathered = await gather(ctx, centre, towns, PERCENT // 2, loss=0)
        tally.shared += await give_out(ctx, centre, towns, gathered)
    elif order.allocation is A.COMMAND and order.planning_capacity < table.command_efficiency_floor:
        gap = table.command_efficiency_floor - order.planning_capacity
        for town_id in towns:
            town = await ctx.session.get(EntityRow, town_id)
            if town is not None and not held(town_id):
                shift_stat(town, "prosperity", -max(1, gap // 10), ctx.rules.society.default_stat)
        tally.shortfalls += 1
        await record(
            ctx,
            "economy.plan_shortfall",
            roles={IncidentRole.SUBJECT: entity.id, IncidentRole.VICTIM: towns},
            facts={"planning": order.planning_capacity, "floor": table.command_efficiency_floor},
            terms=(Term("economic_orders.command_efficiency_floor", table.command_efficiency_floor), Term("order.planning_capacity", -order.planning_capacity)),
        )


async def keep_orders(ctx: TickContext, tally: OrderTally) -> None:
    for order in list(await ctx.session.scalars(select(EconomicOrderRow).order_by(EconomicOrderRow.id))):
        realm = await ctx.session.get(PolityProfileRow, order.polity_entity_id)
        if realm is None or held(order.polity_entity_id):
            continue
        if "planning_capacity" not in order.locked:
            order.planning_capacity = await planning_of(ctx, order)
        if "kind_id" not in order.locked:
            order.kind_id = await kind_matching(ctx, axes_of(order))
        towns = await towns_of_realm(ctx, order.polity_entity_id)
        await share_out(ctx, order, towns)
        if order.sector is None:
            await run_flows(ctx, order, realm, towns, tally)


async def owner_for(ctx: TickContext, regime: OwnershipRegime, polity_id: int, town_id: int) -> int | None:
    if regime in {OWN.STATE, OWN.RULER}:
        return polity_id
    if regime in {OWN.COOPERATIVE, OWN.COMMUNITY, OWN.COMMON}:
        return town_id
    if regime in {OWN.PRIVATE, OWN.COMPANY}:
        return await ctx.session.scalar(
            select(EntityRow.id)
            .where(of_kinds([FactionKind.MERCHANT_GUILD]), EntityRow.status == EntityStatus.CANON, EntityRow.location_id == town_id)
            .order_by(EntityRow.id)
            .limit(1)
        )
    if regime in {OWN.HOUSEHOLD, OWN.KIN_GROUP}:
        return await ctx.session.scalar(
            select(HouseholdRow.head_node_id)
            .where(HouseholdRow.settlement_node_id == town_id, HouseholdRow.head_node_id.is_not(None))
            .order_by(HouseholdRow.wealth, HouseholdRow.id)
            .limit(1)
        )
    return None


async def holdings_in(ctx: TickContext, towns: list[int]) -> list[tuple[BondRow, int]]:
    town_of_place: dict[int, int] = {town: town for town in towns}
    for town_id, region_id in await ctx.session.execute(select(EntityRow.id, EntityRow.location_id).where(EntityRow.id.in_(towns)).order_by(EntityRow.id)):
        if region_id is not None:
            town_of_place.setdefault(int(region_id), int(town_id))
    found: list[tuple[BondRow, int]] = []
    rows = await ctx.session.execute(
        select(BondRow, EntityRow.location_id)
        .join(ResourceProfileRow, ResourceProfileRow.resource_entity_id == BondRow.target_node_id)
        .join(EntityRow, EntityRow.id == BondRow.target_node_id)
        .where(BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE, EntityRow.location_id.in_(sorted(town_of_place)))
        .order_by(BondRow.id)
    )
    for bond, place in rows.all():
        if place is not None:
            found.append((bond, town_of_place[int(place)]))
    return found


COMPENSATED: Mapping[Compensation, int] = total(Compensation, {Compensation.NONE: 0, Compensation.PARTIAL: 50, Compensation.FULL: 100})


async def compensate(ctx: TickContext, row: OrderTransitionRow, realm: EntityRow, loser: EntityRow) -> int:
    table = ctx.rules.economic_orders
    share = COMPENSATED[row.compensation]
    if share == 0:
        return table.uncompensated_grievance
    price = table.holding_price * share // PERCENT
    if await take_coin(ctx.session, ctx.rules, realm, price):
        await give_coin(ctx.session, ctx.rules, loser, price)
        return table.uncompensated_grievance * (PERCENT - share) // PERCENT
    return table.uncompensated_grievance


async def flee(ctx: TickContext, row: OrderTransitionRow, realm: EntityRow, loser: EntityRow, grievance: int) -> bool:
    if loser.entity_type is not EntityType.MORTAL or grievance <= 0 or held(loser.id):
        return False
    odds = grievance // 10 * ctx.rules.economic_orders.flight_per_grievance_pct
    if not ctx.rng(seed_of("economy.flight", row.id, loser.id, ctx.epoch)).chance(odds):
        return False
    towns = await towns_of_realm(ctx, realm.id)
    refuge = await ctx.session.scalar(
        select(EntityRow.id)
        .where(
            EntityRow.entity_type == EntityType.SETTLEMENT,
            EntityRow.status == EntityStatus.CANON,
            EntityRow.world_id == loser.world_id,
            EntityRow.id.not_in(towns or [0]),
        )
        .order_by(EntityRow.id)
        .limit(1)
    )
    if refuge is None:
        return False
    loser.location_id = int(refuge)
    await record(
        ctx,
        "economy.transition_fled",
        roles={IncidentRole.SUBJECT: loser.id, IncidentRole.ORIGIN: realm.id, IncidentRole.DESTINATION: int(refuge)},
        facts={"grievance": grievance},
        steps=(
            StepDraft(StepAction.LEAVE, actor=loser.id),
            StepDraft(StepAction.ARRIVE, actor=loser.id, locus_kind=StepLocus.SETTLEMENT, locus_node=int(refuge)),
        ),
        destination=int(refuge),
    )
    return True


async def transfer_holdings(ctx: TickContext, row: OrderTransitionRow, realm: EntityRow, tally: OrderTally) -> None:
    table = ctx.rules.economic_orders
    regime = OWN(row.to_axes.get("ownership", row.from_axes.get("ownership", OWN.HOUSEHOLD.value)))
    moved = 0
    holdings = await holdings_in(ctx, await towns_of_realm(ctx, realm.id))
    quota = math.ceil(len(holdings) * table.transfers_per_stage / PERCENT)
    for bond, town_id in holdings:
        if moved >= quota:
            break
        owner = await owner_for(ctx, regime, realm.id, town_id)
        loser = await ctx.session.get(EntityRow, bond.source_node_id)
        if owner is None or owner == bond.source_node_id or loser is None or held(loser.id, bond.target_node_id):
            continue
        bond.state, bond.closed_epoch, bond.closed_reason = BondState.PAST, ctx.epoch, f"taken in a change of order of {realm.name}"
        await connect(ctx.session, owner, bond.target_node_id, BondKind.OWNS, ctx.epoch, description=f"given in a change of order of {realm.name}")
        grievance = await compensate(ctx, row, realm, loser)
        await flee(ctx, row, realm, loser, grievance)
        if "resistance" not in row.locked:
            row.resistance = clamp_int(row.resistance + grievance * table.resistance_pct // PERCENT, 0, PERCENT)
        if grievance:
            tally.resisted += 1
        moved += 1
    row.transferred += moved
    tally.transferred += moved
    if moved:
        await record(
            ctx,
            "economy.holding_transferred",
            roles={IncidentRole.AUTHORITY: realm.id},
            facts={"moved": moved, "resistance": row.resistance, "compensation": row.compensation},
        )


async def finish(ctx: TickContext, row: OrderTransitionRow, realm: EntityRow, tally: OrderTally) -> None:
    order = await ctx.session.scalar(
        select(EconomicOrderRow).where(EconomicOrderRow.polity_entity_id == row.polity_entity_id, EconomicOrderRow.sector == row.sector).limit(1)
    )
    if order is not None and not held(order.polity_entity_id):
        for axis, value in row.to_axes.items():
            if axis in AXES and axis not in order.locked:
                setattr(order, axis, AXIS_ENUMS[axis](value))
        order.since_epoch = ctx.epoch
    row.stage, row.ended_epoch = TransitionStage.DONE, ctx.epoch
    tally.done += 1
    await record(
        ctx,
        "economy.transition_done",
        roles={IncidentRole.AUTHORITY: realm.id},
        facts={"transition": row.kind, "transferred": row.transferred, "sector": row.sector},
    )


async def advance(ctx: TickContext, row: OrderTransitionRow, tally: OrderTally) -> None:
    table = ctx.rules.economic_orders
    realm = await ctx.session.get(EntityRow, row.polity_entity_id)
    if realm is None or realm.status is not EntityStatus.CANON:
        row.stage = TransitionStage.FAILED
        return
    if (ctx.epoch - row.started_epoch) % max(1, table.transition_stage_epochs):
        return
    if row.stage is TransitionStage.PROCLAIMED:
        row.stage = TransitionStage.TRANSFERRING
        tally.stages += 1
        await record(ctx, "economy.transition_stage", roles={IncidentRole.AUTHORITY: realm.id}, facts={"transition": row.kind, "stage": row.stage})
        return
    await transfer_holdings(ctx, row, realm, tally)
    resistance = await lagged(ctx, BalanceLoop.COLLECTIVISATION_REVERSAL, realm.id, row.resistance, subject=row.id)
    if resistance >= table.fail_from:
        row.stage, row.ended_epoch = TransitionStage.FAILED, ctx.epoch
        profile = await ctx.session.get(PolityProfileRow, realm.id)
        if profile is not None and "stability" not in profile.locked:
            profile.stability = clamp_int(profile.stability - table.failure_stability, 0, PERCENT)
        tally.failed += 1
        await record(
            ctx,
            "economy.transition_failed",
            roles={IncidentRole.AUTHORITY: realm.id},
            facts={"transition": row.kind, "resistance": row.resistance, "stability_lost": table.failure_stability},
        )
        return
    if row.resistance >= table.fail_from // 2:
        await record(ctx, "economy.transition_resisted", roles={IncidentRole.AUTHORITY: realm.id}, facts={"transition": row.kind, "resistance": row.resistance})
    holdings = await holdings_in(ctx, await towns_of_realm(ctx, realm.id))
    if not holdings or row.transferred * PERCENT >= len(holdings) * table.transfers_to_finish:
        await finish(ctx, row, realm, tally)


async def keep_transitions(ctx: TickContext, tally: OrderTally) -> None:
    live = (TransitionStage.PROCLAIMED, TransitionStage.TRANSFERRING)
    for row in list(await ctx.session.scalars(select(OrderTransitionRow).where(OrderTransitionRow.stage.in_(live)).order_by(OrderTransitionRow.id))):
        if held(row.polity_entity_id) or "stage" in row.locked:
            continue
        await advance(ctx, row, tally)


async def order_of(session: AsyncSession, polity_id: int, sector: str | None) -> EconomicOrderRow | None:
    return await session.scalar(select(EconomicOrderRow).where(EconomicOrderRow.polity_entity_id == polity_id, EconomicOrderRow.sector == sector).limit(1))


async def open_transition(session: AsyncSession, polity_id: int, sector: str | None) -> OrderTransitionRow | None:
    return await session.scalar(
        select(OrderTransitionRow)
        .where(
            OrderTransitionRow.polity_entity_id == polity_id,
            OrderTransitionRow.sector == sector,
            OrderTransitionRow.stage.in_((TransitionStage.PROCLAIMED, TransitionStage.TRANSFERRING)),
        )
        .limit(1)
    )


async def transition_target(session: AsyncSession, polity_id: int, kind: TransitionKind) -> dict[str, str]:
    if kind is not TransitionKind.RESTORATION_OF_HOLDINGS:
        return dict(TARGETS[kind])
    last = await session.scalar(
        select(OrderTransitionRow)
        .where(OrderTransitionRow.polity_entity_id == polity_id, OrderTransitionRow.stage == TransitionStage.DONE)
        .order_by(OrderTransitionRow.ended_epoch.desc(), OrderTransitionRow.id.desc())
        .limit(1)
    )
    return dict(last.from_axes) if last is not None else {}


def changed_axes(current: dict[str, str], wanted: dict[str, str]) -> dict[str, str]:
    return {axis: value for axis, value in wanted.items() if axis in AXES and current.get(axis) != value}


def locked_axes(order: EconomicOrderRow | None, wanted: dict[str, str]) -> list[str]:
    if order is None:
        return []
    return [axis for axis in changed_axes(axes_of(order), wanted) if axis in order.locked]


async def begin_transition(ctx: TickContext, polity_id: int, sector: str | None, kind: TransitionKind, compensation: Compensation) -> OrderTransitionRow:
    order = await order_of(ctx.session, polity_id, sector)
    current = axes_of(order) if order is not None else {}
    target = await transition_target(ctx.session, polity_id, kind)
    row = OrderTransitionRow(
        polity_entity_id=polity_id,
        sector=sector,
        kind=kind,
        from_axes=current,
        to_axes={**current, **target},
        compensation=compensation,
        started_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    await record(
        ctx,
        "economy.transition_begun",
        roles={IncidentRole.AUTHORITY: polity_id},
        facts={"transition": row.kind, "compensation": row.compensation, "sector": row.sector},
        steps=(StepDraft(StepAction.PROCLAIM, actor=polity_id),),
    )
    return row


async def set_order(ctx: TickContext, polity_id: int, sector: str | None, axes: dict[str, str]) -> EconomicOrderRow:
    order = await order_of(ctx.session, polity_id, sector)
    if order is None:
        order = EconomicOrderRow(polity_entity_id=polity_id, sector=sector, since_epoch=ctx.epoch, locked=[])
        ctx.session.add(order)
    for axis, value in axes.items():
        if axis in AXES and axis not in order.locked:
            setattr(order, axis, AXIS_ENUMS[axis](value))
    order.since_epoch = ctx.epoch
    order.kind_id = await kind_matching(ctx, axes_of(order))
    await ctx.session.flush()
    await record(ctx, "economy.order_set", roles={IncidentRole.AUTHORITY: polity_id}, facts={"sector": order.sector, "axes": len(axes)})
    return order


async def keep_economy(ctx: TickContext, tally: OrderTally) -> None:
    await seed_kinds(ctx, tally)
    await seed_orders(ctx, tally)
    await keep_orders(ctx, tally)
    await keep_transitions(ctx, tally)
    await ctx.session.flush()
