from sqlalchemy import select

from aerona.catalog.kinds.trade_modes import TRADE_MODES
from aerona.catalog.life.economy import CONTESTABLE
from aerona.constants.units import PERCENT
from aerona.db.fixups import fixup_due
from aerona.db.tables.climes import RegionWindRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.polity import PolityProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.economy import TradeRouteStatus
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.economy.book import EconomyBook
from aerona.engine.economy.route_dangers import Dangers, high
from aerona.engine.economy.routes import Route, route_locked
from aerona.engine.recording.record import record
from aerona.engine.renown.currencies import realm_of_community
from aerona.rules.registry import Rules

ROUTES_FIXUP = "routes.w52"


async def end_realms(ctx: TickContext, route: Route) -> tuple[int | None, int | None]:
    first, second = route.ends
    return await realm_of_community(ctx.session, first), await realm_of_community(ctx.session, second)


async def take_officials(ctx: TickContext, route: Route, dangers: Dangers) -> None:
    if route_locked(route, "danger_officials"):
        dangers.officials = route.profile.danger_officials
        return
    corrupt: list[tuple[int, int]] = []
    for realm_id in await end_realms(ctx, route):
        profile = await ctx.session.get(PolityProfileRow, realm_id) if realm_id is not None else None
        if profile is not None and realm_id is not None:
            corrupt.append((profile.corruption, realm_id))
    worst = max(corrupt) if corrupt else (0, None)
    route.profile.danger_officials = dangers.officials = ctx.rules.route_dangers.officials_pct * worst[0] // PERCENT
    dangers.official_id = worst[1]


async def weigh_contest(ctx: TickContext, route: Route, enemies: set[tuple[int, int]]) -> None:
    profile = route.profile
    if route_locked(route, "status") or profile.status not in CONTESTABLE:
        return
    first, second = await end_realms(ctx, route)
    fought = first is not None and second is not None and first != second and ((first, second) in enemies or (second, first) in enemies)
    if fought and profile.status is TradeRouteStatus.OPEN:
        profile.status = TradeRouteStatus.CONTESTED
        await record(
            ctx, "route.contested", roles={IncidentRole.SUBJECT: route.entity.id, IncidentRole.ORIGIN: route.ends[0], IncidentRole.DESTINATION: route.ends[1]}
        )
    elif not fought and profile.status is TradeRouteStatus.CONTESTED:
        profile.status = TradeRouteStatus.OPEN


def closing_season(rules: Rules, book: EconomyBook, route: Route, monsoon: set[int]) -> int | None:
    world_id = route.entity.world_id
    seasons = book.ground.seasons_of(world_id) if world_id is not None else []
    regions = [row for row in (book.ground.regions.get(region) for region in route.path) if row is not None]
    if not seasons or not regions:
        return None
    if TRADE_MODES[route.profile.mode].seagoing and any(region in monsoon for region in route.path):
        return max(seasons, key=lambda season: (season.rain_shift, season.position)).position
    if any(high(rules, region) for region in regions):
        return min(seasons, key=lambda season: (season.temperature_shift, season.position)).position
    return None


async def mark_seasonal(ctx: TickContext, book: EconomyBook, routes: list[Route]) -> int:
    if not await fixup_due(ctx.session, ROUTES_FIXUP):
        return 0
    monsoon = set(await ctx.session.scalars(select(RegionWindRow.region_entity_id).where(RegionWindRow.monsoon > 0)))
    marked = 0
    for route in routes:
        if held(route.entity.id) or route_locked(route, "status") or route.profile.status is not TradeRouteStatus.OPEN:
            continue
        closed = closing_season(ctx.rules, book, route, monsoon)
        if closed is not None:
            route.profile.status, route.profile.closed_season = TradeRouteStatus.SEASONAL, closed
            marked += 1
            season = next((row.name for row in book.ground.seasons_of(route.entity.world_id or 0) if row.position == closed), "its closed season")
            await record(ctx, "route.season_closed", roles={IncidentRole.SUBJECT: route.entity.id}, facts={"season": season})
    ctx.session.add(AppliedFixupRow(key=ROUTES_FIXUP, result={"seasonal": marked}))
    await ctx.session.flush()
    return marked
