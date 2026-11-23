from collections.abc import Awaitable, Callable, Mapping, Sequence

from sqlalchemy import func, select

from aerona.catalog.carriers import CARRIERS
from aerona.catalog.kinds.trade_modes import TRADE_MODES
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.grammar import an
from aerona.db.tables.economy import ROUTE_DANGER_COLUMNS, TradeRouteProfileRow, TradeRouteTollRow, WorkshopRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import WorldSeasonRow
from aerona.domain.enums.economy import TradeMode, TradeRouteStatus, WorkshopKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus, EntityType
from aerona.domain.enums.operations import CarrierKind
from aerona.engine.context import TickContext
from aerona.engine.economy.book import EconomyBook
from aerona.engine.economy.routes import Route, found_route, length_of, load_routes, spoken_capacity, write_path
from aerona.engine.environment.works import works_by_region
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.records import retire_in
from aerona.engine.primitives.stats import set_stats

Value = int | str | bool | list[int] | None
STAT_KEYS = ("capacity", "danger", "renown", "culture")
PERCENT_KEYS = (*ROUTE_DANGER_COLUMNS, "season_pct", "danger", "renown", "culture")
PROFILE_KEYS = (
    *ROUTE_DANGER_COLUMNS,
    "season_pct",
    "length",
    "mode",
    "status",
    "controller_entity_id",
    "blockaded_by_entity_id",
    "chokepoint",
    "closed_season",
    "carrier",
)
EDITABLE = frozenset({*STAT_KEYS, *PROFILE_KEYS, "path"})
UNTOLLED = "untolled."
CONTROLLER_TYPES = frozenset({*COMMUNITY_TYPES, EntityType.POLITY, EntityType.MORTAL})


def hold(locked: list[str] | None, key: str) -> list[str]:
    current = list(locked or [])
    return current if key in current else [*current, key]


def release(locked: list[str] | None, keys: Sequence[str]) -> list[str]:
    return [item for item in locked or [] if item not in keys]


async def route_of(ctx: TickContext, route_id: int) -> Route:
    profile = await ctx.session.get(TradeRouteProfileRow, route_id)
    entity = await ctx.session.get(EntityRow, route_id)
    if profile is None or entity is None:
        raise NotFoundError("No such trade route.")
    found = next((route for route in await load_routes(ctx, live_only=False) if route.entity.id == route_id), None)
    if found is None:
        raise NotFoundError("No such trade route.")
    return found


def whole(key: str, value: Value, *, low: int = 0, high: int | None = None) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValidationFailedError(f"{key.replace('_', ' ').capitalize()} is a whole number.")
    if value < low or (high is not None and value > high):
        raise ValidationFailedError(f"{key.replace('_', ' ').capitalize()} runs from {low} to {high if high is not None else 'any height'}.")
    return value


async def holder(ctx: TickContext, key: str, value: Value, kinds: frozenset[EntityType]) -> int | None:
    if value is None:
        return None
    entity = await living_entity(ctx.session, whole(key, value, low=1))
    if entity is None or entity.entity_type not in kinds:
        raise ValidationFailedError(f"No living {key.replace('_entity_id', '').replace('_', ' ')} with that id.")
    return entity.id


async def set_path(ctx: TickContext, route: Route, value: Value) -> None:
    if not isinstance(value, list) or len(value) < 1 or any(not isinstance(item, int) or isinstance(item, bool) for item in value):
        raise ValidationFailedError("A route's path is a list of lands.")
    for region in value:
        entity = await ctx.session.get(EntityRow, region)
        if entity is None or entity.entity_type is not EntityType.REGION:
            raise ValidationFailedError("Every step of a route's path must be a land.")
    route.path = list(value)
    await write_path(ctx, route.entity.id, route.path)
    route.profile.length = length_of(ctx, route.profile.mode, route.path)


async def set_mode(ctx: TickContext, route: Route, value: Value) -> None:
    try:
        route.profile.mode = TradeMode(str(value))
    except ValueError as error:
        raise ValidationFailedError(f"{value} is not a way of travel.") from error
    route.entity.subtype = route.profile.mode.value


async def set_status(ctx: TickContext, route: Route, value: Value) -> None:
    try:
        status = TradeRouteStatus(str(value))
    except ValueError as error:
        raise ValidationFailedError(f"{value} is not a state a route can be in.") from error
    route.profile.status = status
    route.profile.closed_by_player = status is TradeRouteStatus.CLOSED
    if status is not TradeRouteStatus.CLOSED:
        route.profile.closed_by_son_id = None
    decayed = status is TradeRouteStatus.DECAYED
    route.entity.end_epoch = (route.entity.end_epoch or ctx.epoch) if decayed else None
    route.entity.status = EntityStatus.DESTROYED if decayed else EntityStatus.CANON


async def set_controller(ctx: TickContext, route: Route, value: Value) -> None:
    route.profile.controller_entity_id = await holder(ctx, "controller_entity_id", value, CONTROLLER_TYPES)


async def set_blockade(ctx: TickContext, route: Route, value: Value) -> None:
    profile = route.profile
    profile.blockaded_by_entity_id = await holder(ctx, "blockaded_by_entity_id", value, frozenset({EntityType.ARMY}))
    if profile.blockaded_by_entity_id is not None:
        profile.status = TradeRouteStatus.BLOCKADED
    elif profile.status is TradeRouteStatus.BLOCKADED:
        profile.status = TradeRouteStatus.OPEN


async def set_chokepoint(ctx: TickContext, route: Route, value: Value) -> None:
    if not isinstance(value, bool):
        raise ValidationFailedError("Chokepoint is yes or no.")
    route.profile.chokepoint = value


async def set_length(ctx: TickContext, route: Route, value: Value) -> None:
    route.profile.length = whole("length", value, low=1)


async def set_closed_season(ctx: TickContext, route: Route, value: Value) -> None:
    if value is None:
        route.profile.closed_season = None
        return
    count = await ctx.session.scalar(select(func.count()).select_from(WorldSeasonRow).where(WorldSeasonRow.world_id == route.entity.world_id))
    route.profile.closed_season = whole("closed_season", value, high=max(0, int(count or 0) - 1))


async def set_carrier(ctx: TickContext, route: Route, value: Value) -> None:
    if value is None:
        route.profile.carrier = None
        return
    try:
        carrier = CarrierKind(str(value))
    except ValueError as error:
        raise ValidationFailedError(f"{value} is not a way of carrying goods.") from error
    if route.profile.mode not in CARRIERS[carrier].modes:
        raise ValidationFailedError(f"{CARRIERS[carrier].label} cannot travel {an(TRADE_MODES[route.profile.mode].words.lower())}.")
    route.profile.carrier = carrier


SETTERS: dict[str, Callable[[TickContext, Route, Value], Awaitable[None]]] = {
    "path": set_path,
    "mode": set_mode,
    "status": set_status,
    "controller_entity_id": set_controller,
    "blockaded_by_entity_id": set_blockade,
    "chokepoint": set_chokepoint,
    "length": set_length,
    "closed_season": set_closed_season,
    "carrier": set_carrier,
}


async def apply(ctx: TickContext, route: Route, key: str, value: Value) -> None:
    setter = SETTERS.get(key)
    if setter is not None:
        await setter(ctx, route, value)
    elif key in STAT_KEYS:
        set_stats(route.entity, **{key: whole(key, value, high=PERCENT if key in PERCENT_KEYS else None)})
    else:
        setattr(route.profile, key, whole(key, value, high=PERCENT))


async def edit_route(ctx: TickContext, route_id: int, values: Mapping[str, Value], *, released: Sequence[str]) -> Route:
    route = await route_of(ctx, route_id)
    unknown = set(values) - EDITABLE
    unheld = {key for key in released if not key.startswith(UNTOLLED)} - EDITABLE
    if unknown or unheld:
        raise ValidationFailedError(f"Unknown route fields: {', '.join(sorted(unknown | unheld))}.")
    for key, value in values.items():
        await apply(ctx, route, key, value)
        route.profile.locked = hold(route.profile.locked, key)
    route.profile.locked = release(route.profile.locked, released)
    await ctx.session.flush()
    return route


async def found_by_hand(
    ctx: TickContext,
    first_id: int,
    second_id: int,
    *,
    mode: TradeMode | None,
    controller_id: int | None,
    toll_pct: int | None,
) -> Route:
    if first_id == second_id:
        raise ValidationFailedError("A route joins two different markets.")
    ends = [await living_entity(ctx.session, first_id), await living_entity(ctx.session, second_id)]
    first, second = ends
    if first is None or second is None or any(end.entity_type not in COMMUNITY_TYPES for end in (first, second)):
        raise ValidationFailedError("A route joins two living peoples or settlements.")
    for route in await load_routes(ctx, live_only=False):
        if frozenset(route.ends) == frozenset((first.id, second.id)) and route.entity.status is EntityStatus.CANON:
            raise ValidationFailedError(f"{first.name} and {second.name} are already joined by {route.entity.name}; open or edit it instead.")
    book = await EconomyBook.load(ctx)
    path = book.ground.atlas.region_path(book.ground.atlas.top_region(first.id), book.ground.atlas.top_region(second.id))
    if path is None:
        raise ValidationFailedError(f"No way leads from {first.name} to {second.name}.")
    for end in (first, second):
        if book.workshop(end.id, WorkshopKind.MARKET) is None:
            ctx.session.add(WorkshopRow(community_entity_id=end.id, kind=WorkshopKind.MARKET, level=1, built_epoch=ctx.epoch))
    works = await works_by_region(ctx, book.ground)
    route = await found_route(ctx, book, first, second, path, works=works)
    route.profile.status = TradeRouteStatus.OPEN
    route.profile.last_traffic_epoch = ctx.epoch
    route.entity.pending_name = True
    if mode is not None:
        await apply(ctx, route, "mode", mode.value)
        route.profile.length = length_of(ctx, mode, path)
        set_stats(route.entity, capacity=await spoken_capacity(ctx, book, route, works))
        route.profile.locked = hold(route.profile.locked, "mode")
    if controller_id is not None:
        await apply(ctx, route, "controller_entity_id", controller_id)
        route.profile.locked = hold(route.profile.locked, "controller_entity_id")
    if toll_pct is not None and controller_id is not None:
        for region in path[1:-1] or path[:1]:
            await set_toll_stop(ctx, route.entity.id, region, controller_id=controller_id, rate=toll_pct, released=())
    await ctx.session.flush()
    return route


async def set_toll_stop(
    ctx: TickContext, route_id: int, region_id: int, *, controller_id: int | None, rate: int | None, released: Sequence[str]
) -> TradeRouteTollRow:
    route = await route_of(ctx, route_id)
    if region_id not in route.path:
        raise ValidationFailedError("That land is not on the route's way.")
    toll = route.tolls.get(region_id)
    if toll is None:
        if controller_id is None:
            raise ValidationFailedError("Name who takes the toll in that land.")
        toll = TradeRouteTollRow(route_entity_id=route_id, region_entity_id=region_id, controller_entity_id=controller_id, rate_pct=0)
        ctx.session.add(toll)
    if controller_id is not None:
        toll.controller_entity_id = await holder(ctx, "controller_entity_id", controller_id, CONTROLLER_TYPES) or controller_id
        toll.controller_held = True
    if rate is not None:
        toll.rate_pct = whole("rate", rate, high=PERCENT)
        toll.set_by_player = True
    if "controller_entity_id" in released:
        toll.controller_held = False
    if "rate_pct" in released:
        toll.set_by_player = False
    route.profile.locked = release(route.profile.locked, [f"{UNTOLLED}{region_id}"])
    await ctx.session.flush()
    return toll


async def remove_toll(ctx: TickContext, route_id: int, region_id: int) -> Route:
    route = await route_of(ctx, route_id)
    if region_id not in route.path:
        raise ValidationFailedError("That land is not on the route's way.")
    toll = route.tolls.pop(region_id, None)
    if toll is not None:
        await ctx.session.delete(toll)
    route.profile.locked = hold(route.profile.locked, f"{UNTOLLED}{region_id}")
    await ctx.session.flush()
    return route


async def delete_route(ctx: TickContext, route_id: int) -> EntityRow:
    route = await route_of(ctx, route_id)
    route.profile.status = TradeRouteStatus.DECAYED
    route.profile.closed_by_player = False
    route.profile.locked = []
    await retire_in(ctx, route.entity, "struck from the world by the Creator", status=EntityStatus.DESTROYED)
    await ctx.session.flush()
    return route.entity
