from collections.abc import Mapping
from types import MappingProxyType

from sqlalchemy import select

from aerona.catalog.commodities import COMMODITIES, FOOD_KINDS
from aerona.catalog.needs import SERVE_ORDER
from aerona.constants.units import PERCENT
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.society_depth import ClassStandingRow, MobilityEventRow
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.society_depth import MobilityEvent
from aerona.engine.context import TickContext
from aerona.engine.demography.basket import build_basket, needs_of, save_basket, staples_of
from aerona.engine.demography.prices import local_prices
from aerona.engine.demography.wealth import gini, stock_value, wealth_targets
from aerona.engine.economy.household import Meal, Wear, diet_demand
from aerona.engine.economy.stocks import epoch_need, holdings, nourishment_need
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.stats import headcount

SOCIETY_DEPTH_FIXUP = "society.depth_backfill"
EVENT_KEYS: Mapping[str, MobilityEvent] = MappingProxyType({"society.ennobled": MobilityEvent.ENNOBLED, "society.ruined": MobilityEvent.RUINED})


def backfill_meal(population: int, wanted: Mapping[CommodityKind, int], held: Mapping[CommodityKind, int]) -> Meal:
    eaten = {kind: min(amount, held.get(kind, 0)) for kind, amount in wanted.items()}
    need = sum(amount * COMMODITIES[kind].nourishment for kind, amount in wanted.items())
    fed = sum(amount * COMMODITIES[kind].nourishment for kind, amount in eaten.items())
    pct = round_half_up(fed * PERCENT / need) if need > 0 and population > 0 else PERCENT
    return Meal(pct, eaten, {kind: wanted[kind] - eaten[kind] for kind in wanted if wanted[kind] > eaten[kind]}, dict(wanted))


async def backfill_community(ctx: TickContext, community: EntityRow, society: CommunitySocietyRow) -> bool:
    if await ctx.session.scalar(select(ClassStandingRow.social_class).where(ClassStandingRow.community_entity_id == community.id).limit(1)) is not None:
        return False
    population = headcount(community)
    shares = {social_class: society.share(social_class) for social_class in SocialClass}
    held = await holdings(ctx.session, community.id)
    staples = await staples_of(ctx.session, community)
    meal = backfill_meal(population, diet_demand(ctx.rules, population, staples, nourishment_need(ctx.rules, population)), held)
    wanted = {kind: epoch_need(ctx.rules, population, kind) for kind in COMMODITIES if kind not in FOOD_KINDS and epoch_need(ctx.rules, population, kind) > 0}
    worn = Wear(wanted, {kind: min(amount, held.get(kind, 0)) for kind, amount in wanted.items()})
    basket = build_basket(shares, meal, worn, staples=staples, order=SERVE_ORDER, held={}, luxuries_left=held.get(CommodityKind.LUXURIES, 0))
    await save_basket(ctx, community, basket, await needs_of(ctx.session, community.id))
    prices = await local_prices(ctx.session, ctx.rules, community.id, population)
    supply = society.stock_food + society.stock_ore + society.stock_goods
    total = stock_value(held, prices) + round_half_up(supply * ctx.rules.mobility.wealth_per_supply_pct / PERCENT)
    targets = wealth_targets(total, shares)
    rows = {row.social_class: row for row in await ctx.session.scalars(select(ClassStandingRow).where(ClassStandingRow.community_entity_id == community.id))}
    for social_class, row in rows.items():
        row.wealth = targets.get(social_class, 0)
    society.gini = gini({social_class: row.wealth for social_class, row in rows.items()}, shares)
    return True


async def backfill_events(ctx: TickContext) -> int:
    made = 0
    for incident in await ctx.session.scalars(select(IncidentRow).where(IncidentRow.kind.in_(list(EVENT_KEYS))).order_by(IncidentRow.id)):
        nodes = list(
            await ctx.session.scalars(
                select(IncidentParticipantRow.node_id).where(IncidentParticipantRow.incident_id == incident.id).order_by(IncidentParticipantRow.position)
            )
        )
        mortal = await ctx.session.get(EntityRow, nodes[0]) if nodes else None
        if mortal is None or mortal.entity_type is not EntityType.MORTAL:
            continue
        other = await ctx.session.get(EntityRow, nodes[1]) if len(nodes) > 1 else None
        ctx.session.add(
            MobilityEventRow(
                community_entity_id=None,
                event=EVENT_KEYS[incident.kind],
                count=1,
                mortal_entity_id=mortal.id,
                other_entity_id=other.id if other is not None else None,
                by_hand=False,
                epoch=incident.epoch,
            )
        )
        made += 1
    return made


async def society_depth_backfill(ctx: TickContext, communities: list[EntityRow]) -> dict[str, int]:
    if await ctx.session.get(AppliedFixupRow, SOCIETY_DEPTH_FIXUP) is not None:
        return {}
    filled = 0
    for community in communities:
        society = await ctx.session.get(CommunitySocietyRow, community.id)
        if society is not None and await backfill_community(ctx, community, society):
            filled += 1
    result = {"communities": filled, "mobility_events": await backfill_events(ctx)}
    ctx.session.add(AppliedFixupRow(key=SOCIETY_DEPTH_FIXUP, result=result))
    await ctx.session.flush()
    return result
