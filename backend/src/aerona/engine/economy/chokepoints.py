from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.economy import TradeRouteProfileRow, TradeRouteTollRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.military import WarAimRow
from aerona.db.tables.polity import TreatyClauseRow, TreatyProfileRow
from aerona.db.tables.warfare import ArmyRow, WarRow
from aerona.domain.enums.economy import TradeRouteStatus
from aerona.domain.enums.military import WarAimKind
from aerona.domain.enums.polity import ClauseKind, TreatyStatus
from aerona.domain.enums.war import WarStatus
from aerona.engine.context import TickContext
from aerona.engine.economy.book import EconomyBook
from aerona.engine.polity.book import RealmBook
from aerona.engine.polity.treaties import Clause
from aerona.engine.primitives.numbers import clamp_int

LIVE = (TradeRouteStatus.FORMING, TradeRouteStatus.OPEN, TradeRouteStatus.BLOCKADED)
ROUTE_KEY = "route_id"


def route_of(params: dict[str, int | str | bool] | None) -> int | None:
    value = (params or {}).get(ROUTE_KEY)
    return int(value) if isinstance(value, str) and value.isdigit() else None


async def route_grants(session: AsyncSession) -> dict[int, int]:
    live = select(TreatyProfileRow.treaty_entity_id).where(TreatyProfileRow.status == TreatyStatus.IN_FORCE)
    statement = select(TreatyClauseRow).where(TreatyClauseRow.kind == ClauseKind.ROUTE_CONTROL, TreatyClauseRow.treaty_entity_id.in_(live))
    grants: dict[int, int] = {}
    for clause in await session.scalars(statement.order_by(TreatyClauseRow.id)):
        route = route_of(clause.params)
        if route is not None and clause.beneficiary_node_id is not None:
            grants[route] = clause.beneficiary_node_id
    return grants


async def contested_route(session: AsyncSession, attacker_id: int, defender_id: int) -> int | None:
    profiles = list(
        await session.scalars(
            select(TradeRouteProfileRow)
            .where(TradeRouteProfileRow.status.in_(LIVE), TradeRouteProfileRow.closed_by_player.is_(False))
            .order_by(TradeRouteProfileRow.route_entity_id)
        )
    )
    held: dict[int, set[int]] = {}
    for toll in await session.scalars(select(TradeRouteTollRow)):
        held.setdefault(toll.route_entity_id, set()).update({toll.controller_entity_id, *([toll.polity_entity_id] if toll.polity_entity_id else [])})
    blockers = {row.entity_id: row.owner_entity_id for row in await session.scalars(select(ArmyRow).where(ArmyRow.disbanded_epoch.is_(None)))}

    def mastered(profile: TradeRouteProfileRow) -> bool:
        blocker = blockers.get(profile.blockaded_by_entity_id) if profile.blockaded_by_entity_id is not None else None
        return defender_id in held.get(profile.route_entity_id, set()) or defender_id in (profile.controller_entity_id, blocker)

    ranked = [
        (0 if attacker_id in (profile.first_market_id, profile.second_market_id) else 1, 0 if mastered(profile) else 1, profile.route_entity_id)
        for profile in profiles
        if mastered(profile) or {attacker_id, defender_id} == {profile.first_market_id, profile.second_market_id}
    ]
    return min(ranked)[2] if ranked else None


def weigh_chokepoint(ctx: TickContext, book: EconomyBook, profile: TradeRouteProfileRow, path: list[int], *, moved: int, strategic: int) -> bool:
    if moved <= 0:
        return profile.chokepoint
    vital = strategic * PERCENT >= moved * ctx.rules.chokepoints.strategic_share_pct
    narrow = len(path) > 2 and book.ground.atlas.region_path(path[0], path[-1], frozenset(path[1:-1])) is None
    profile.chokepoint = vital and narrow
    return profile.chokepoint


async def press_route_aims(ctx: TickContext, owner_id: int, route_id: int) -> int:
    statement = (
        select(WarAimRow)
        .join(WarRow, WarRow.id == WarAimRow.war_id)
        .where(
            WarRow.status != WarStatus.ENDED,
            WarAimRow.side_entity_id == owner_id,
            WarAimRow.kind == WarAimKind.SEIZE_ROUTE,
            or_(WarAimRow.target_entity_id == route_id, WarAimRow.target_entity_id.is_(None)),
        )
    )
    pressed = 0
    for aim in await ctx.session.scalars(statement.order_by(WarAimRow.id)):
        aim.achieved = clamp_int(aim.achieved + ctx.rules.chokepoints.blockade_aim_score, 0, PERCENT)
        pressed += 1
    return pressed


async def seize_route(ctx: TickContext, route_id: int, victor_id: int) -> bool:
    profile = await ctx.session.get(TradeRouteProfileRow, route_id)
    if profile is None:
        return False
    if "controller_entity_id" not in (profile.locked or []):
        profile.controller_entity_id = victor_id
    for toll in await ctx.session.scalars(select(TradeRouteTollRow).where(TradeRouteTollRow.route_entity_id == route_id)):
        if not toll.controller_held:
            toll.controller_entity_id = victor_id
    return True


async def route_term(ctx: TickContext, war: WarRow, aim: WarAimRow, sides: tuple[EntityRow, EntityRow], book: RealmBook) -> tuple[str, Clause] | None:
    victor, loser = sides
    route_id = aim.target_entity_id
    if aim.achieved < ctx.rules.peace.cession_score or route_id is None or not await seize_route(ctx, route_id, victor.id):
        return None
    route = await ctx.session.get(EntityRow, route_id)
    name = route.name if route is not None else "the road"
    return f"{victor.name} took {name} and its tolls from {loser.name}", Clause(ClauseKind.ROUTE_CONTROL, loser.id, victor.id, {ROUTE_KEY: str(route_id)})
