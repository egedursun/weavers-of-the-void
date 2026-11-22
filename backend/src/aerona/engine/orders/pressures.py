from collections import Counter

from sqlalchemy import select

from aerona.catalog.life_traits import ALLOCATION_MODE_TRAITS, having
from aerona.constants.units import PERCENT
from aerona.db.tables.culture import IdeologyAdherentRow, IdeologyTenetRow
from aerona.db.tables.estates import MovementProfileRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.orders import EconomicOrderRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.write_guard import held
from aerona.domain.enums.culture import IdeologyTenet
from aerona.domain.enums.faction import MovementCause
from aerona.domain.enums.life_traits import AllocationModeTrait
from aerona.domain.enums.orders import Compensation, OrderLabour, OwnershipRegime, TransitionKind
from aerona.domain.enums.society import SocialClass
from aerona.engine.context import TickContext
from aerona.engine.orders.economy import OrderTally, begin_transition, open_transition, towns_of_realm
from aerona.engine.primitives.queries import living_entity

BOUND_LABOUR = frozenset({OrderLabour.SERF, OrderLabour.ENSLAVED, OrderLabour.BOUND, OrderLabour.CORVEE})
HELD_LAND = frozenset({OwnershipRegime.RULER, OwnershipRegime.TEMPLE, OwnershipRegime.PRIVATE, OwnershipRegime.COMPANY})
CENTRAL_LAND = frozenset({OwnershipRegime.STATE, OwnershipRegime.RULER, OwnershipRegime.COMMUNITY})
PLANNED = having(ALLOCATION_MODE_TRAITS, AllocationModeTrait.STATE_BUYERS)
FAILURES = ("economy.plan_shortfall", "economy.centre_collapsed")


def freeing(order: EconomicOrderRow) -> TransitionKind | None:
    if order.labour in BOUND_LABOUR:
        return TransitionKind.EMANCIPATION
    if order.ownership in HELD_LAND:
        return TransitionKind.LAND_REFORM
    return None


async def movement_demand(ctx: TickContext, realm_id: int, order: EconomicOrderRow) -> TransitionKind | None:
    query = select(MovementProfileRow).where(
        MovementProfileRow.polity_entity_id == realm_id, MovementProfileRow.support >= ctx.rules.economic_orders.demand_support
    )
    for movement in await ctx.session.scalars(query.order_by(MovementProfileRow.faction_entity_id)):
        if movement.cause is MovementCause.ABOLITION and order.labour in BOUND_LABOUR:
            return TransitionKind.EMANCIPATION
        if movement.cause is MovementCause.LAND_REFORM and order.ownership in HELD_LAND:
            return TransitionKind.LAND_REFORM
    return None


async def creed_demand(ctx: TickContext, realm_id: int, order: EconomicOrderRow) -> TransitionKind | None:
    towns = await towns_of_realm(ctx, realm_id)
    if not towns:
        return None
    held_by: Counter[int] = Counter(
        await ctx.session.scalars(select(IdeologyAdherentRow.ideology_entity_id).where(IdeologyAdherentRow.adherent_entity_id.in_(towns)))
    )
    for creed, count in sorted(held_by.items(), key=lambda item: (-item[1], item[0])):
        if count * PERCENT < len(towns) * ctx.rules.economic_orders.creed_hold_pct:
            break
        tenets = set(await ctx.session.scalars(select(IdeologyTenetRow.tenet).where(IdeologyTenetRow.ideology_entity_id == creed)))
        if IdeologyTenet.EGALITARIANISM in tenets and freeing(order) is not None:
            return freeing(order)
        if IdeologyTenet.MERCANTILISM in tenets and order.ownership in CENTRAL_LAND:
            return TransitionKind.PRIVATISATION
    return None


async def failure_demand(ctx: TickContext, realm_id: int, order: EconomicOrderRow) -> TransitionKind | None:
    if order.allocation not in PLANNED:
        return None
    failed = await ctx.session.scalar(
        select(IncidentRow.id)
        .join(IncidentParticipantRow, IncidentParticipantRow.incident_id == IncidentRow.id)
        .where(IncidentRow.kind.in_(FAILURES), IncidentRow.epoch >= ctx.epoch - 1, IncidentParticipantRow.node_id == realm_id)
        .limit(1)
    )
    return TransitionKind.DECOLLECTIVISATION if failed is not None else None


async def class_demand(ctx: TickContext, realm_id: int, order: EconomicOrderRow) -> TransitionKind | None:
    if order.labour not in BOUND_LABOUR:
        return None
    bitter = ctx.rules.mobility.bitter_satisfaction
    towns = await towns_of_realm(ctx, realm_id)
    societies = [
        society for society in await ctx.session.scalars(select(CommunitySocietyRow).where(CommunitySocietyRow.entity_id.in_(towns))) if society is not None
    ]
    if not societies:
        return None
    angry = sum(1 for society in societies if society.satisfaction(SocialClass.SERF_OR_SLAVE) < bitter and society.share(SocialClass.SERF_OR_SLAVE) > 0)
    return TransitionKind.EMANCIPATION if angry * 2 > len(societies) else None


async def demand_of(ctx: TickContext, realm_id: int, order: EconomicOrderRow) -> TransitionKind | None:
    for reader in (movement_demand, creed_demand, failure_demand, class_demand):
        found = await reader(ctx, realm_id, order)
        if found is not None:
            return found
    return None


async def press_orders(ctx: TickContext, tally: OrderTally) -> int:
    begun = 0
    query = select(EconomicOrderRow).where(EconomicOrderRow.sector.is_(None)).order_by(EconomicOrderRow.id)
    for order in list(await ctx.session.scalars(query)):
        realm_id = order.polity_entity_id
        if held(realm_id) or await living_entity(ctx.session, realm_id) is None or await open_transition(ctx.session, realm_id, None) is not None:
            continue
        kind = await demand_of(ctx, realm_id, order)
        if kind is None or not ctx.rng(f"orders.press.{realm_id}.{ctx.epoch}").chance(ctx.rules.economic_orders.demand_chance_pct):
            continue
        await begin_transition(ctx, realm_id, None, kind, Compensation.PARTIAL)
        begun += 1
    return begun
