from collections.abc import Collection, Iterable, Sequence
from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.travel import TRAVEL_METHODS, travel_method_profile
from aerona.constants.cosmos import JOURNEY_EVENT_LIMIT, NUMBER_WORDS
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.random import SeededRandom
from aerona.db.repositories.bonds import BondRepository
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityFlagRow, EntityRow, EntityTraitRow
from aerona.db.tables.routes import JourneyRow, RouteRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ChronicleKind, FeedCategory
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.society import CreatureTrait, KnowledgeBranch
from aerona.domain.enums.son import SonStatus
from aerona.domain.enums.travel import JourneyEventKind, JourneyIntent, JourneyStatus, RouteClosure, TravelMethod, VehicleKind
from aerona.domain.enums.world import Discovery
from aerona.domain.models.records import JourneyEvent
from aerona.engine.context import TickContext
from aerona.engine.cosmos.resources import cosmic_access
from aerona.engine.cosmos.vessels import owned_vessels
from aerona.engine.cosmos.world_types import hidden_route_method, is_realm_of_dead, mechanics_of
from aerona.engine.gods.economy import spend_cosmic_resource
from aerona.engine.primitives.knowledge import knows
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.stats import headcount, headcount_key, put_stat, stat, stat_or
from aerona.rules.registry import Rules

SPEED_KEY = "speed"
RANGE_KEY = "range"
CREW_KEY = "crew"
HP_KEY = "hp"
LIVE_JOURNEYS = (JourneyStatus.UNDERWAY, JourneyStatus.WAITING)


class RouteState(StrEnum):
    OPEN = "open"
    TEMPORARY = "temporary"
    MISALIGNED = "misaligned"
    SEALED = "sealed"
    SEVERED = "severed"
    COLLAPSED = "collapsed"
    SNAPPED = "snapped"
    FORGOTTEN = "forgotten"


@dataclass(frozen=True)
class SkyCalendar:
    epoch: int
    period: int
    aligned: bool
    cycle_aligned: bool
    alignment_until: int | None
    next_cycle: int
    opens_epoch: int | None
    closes_epoch: int | None

    @property
    def text(self) -> str:
        cycle = f"The cycle aligns every {self.period} epochs."
        if self.aligned:
            forced = (
                f" (planetary alignment, until the start of Epoch {self.alignment_until})"
                if self.alignment_until is not None and self.epoch < self.alignment_until
                else ""
            )
            closing = f"; closes at the start of Epoch {self.closes_epoch}" if self.closes_epoch is not None else ""
            return f"Planets aligned: slingshot orbits open{forced}{closing}. {cycle}"
        wait = (self.opens_epoch or self.next_cycle) - self.epoch
        return f"Slingshot orbits closed; they open at the start of Epoch {self.opens_epoch} (in {wait} epochs). {cycle}"


def sky_calendar(rules: Rules, epoch: int, alignment_until: int | None) -> SkyCalendar:
    period = max(1, rules.travel.alignment_period)
    cycle_aligned = epoch % period == 0
    forced = alignment_until is not None and epoch < alignment_until
    aligned = cycle_aligned or forced
    next_cycle = epoch + (period - epoch % period)
    closes: int | None = None
    opens: int | None = None
    if aligned and period > 1:
        closes = max(epoch + 1, alignment_until if forced and alignment_until is not None else epoch + 1)
        if closes % period == 0:
            closes += 1
    if not aligned:
        opens = next_cycle
    return SkyCalendar(epoch, period, aligned, cycle_aligned, alignment_until, next_cycle, opens, closes)


async def current_calendar(session: AsyncSession, rules: Rules, epoch: int) -> SkyCalendar:
    cosmos = await CosmosRepository(session).get()
    return sky_calendar(rules, epoch, cosmos.alignment_until_epoch if cosmos is not None else None)


@dataclass(frozen=True)
class RouteStatus:
    is_open: bool
    state: RouteState
    reason: str
    opens_epoch: int | None = None
    closes_epoch: int | None = None
    aligned: bool | None = None
    hidden: bool = False


def _closed_status(route: RouteRow, forgotten: Collection[int]) -> tuple[RouteState, str, int | None] | None:
    if route.world_a_id in forgotten or route.world_b_id in forgotten:
        return RouteState.FORGOTTEN, "The world at the end of the route was forgotten; the route is in the mist.", None
    if route.active:
        return None
    if route.temp_closed_until_epoch is not None:
        until = route.temp_closed_until_epoch
        return RouteState.SEVERED, f"A storm severed the route; its stitch closes at the start of Epoch {until}.", until
    if route.closure is RouteClosure.SNAPPED:
        return RouteState.SNAPPED, "The light sail snapped when the star lighting the route died.", None
    if route.method is TravelMethod.DIVINE_BRIDGE and route.builder_son_id is not None:
        return RouteState.COLLAPSED, "The divine bridge collapsed when its builder fell.", None
    return RouteState.SEALED, "The route is sealed; only an alignment (temporarily), the creator's hand, or a legendary quest breaks the seal.", None


def route_status(route: RouteRow, calendar: SkyCalendar, forgotten: Collection[int]) -> RouteStatus:
    hidden = not route.known
    slingshot = route.method is TravelMethod.SLINGSHOT_ORBIT
    aligned = calendar.aligned if slingshot else None
    closed = _closed_status(route, forgotten)
    if closed is not None:
        state, reason, opens = closed
        return RouteStatus(False, state, reason, opens_epoch=opens, aligned=aligned, hidden=hidden)
    if slingshot and not calendar.aligned:
        reason = f"Slingshot orbit closed: planets align at the start of Epoch {calendar.opens_epoch}."
        return RouteStatus(False, RouteState.MISALIGNED, reason, opens_epoch=calendar.opens_epoch, aligned=aligned, hidden=hidden)
    closes = [value for value in (route.temp_open_until_epoch, calendar.closes_epoch if slingshot else None) if value is not None]
    closes_epoch = min(closes) if closes else None
    if route.temp_open_until_epoch is not None:
        reason = f"The alignment lifted the seal temporarily; it re-seals at the start of Epoch {route.temp_open_until_epoch}."
        return RouteStatus(True, RouteState.TEMPORARY, reason, closes_epoch=closes_epoch, aligned=aligned, hidden=hidden)
    return RouteStatus(True, RouteState.OPEN, "The route is open.", closes_epoch=closes_epoch, aligned=aligned, hidden=hidden)


async def forgotten_world_ids(session: AsyncSession) -> set[int]:
    return set(await session.scalars(select(WorldRow.id).where(WorldRow.discovery == Discovery.FORGOTTEN)))


class RouteBook:
    def __init__(self, routes: Sequence[RouteRow], calendar: SkyCalendar, forgotten: set[int]) -> None:
        self.routes = list(routes)
        self.calendar = calendar
        self.forgotten = forgotten

    @classmethod
    async def load(cls, session: AsyncSession, rules: Rules, epoch: int) -> "RouteBook":
        routes = list(await session.scalars(select(RouteRow).order_by(RouteRow.id)))
        return cls(routes, await current_calendar(session, rules, epoch), await forgotten_world_ids(session))

    def status(self, route: RouteRow) -> RouteStatus:
        return route_status(route, self.calendar, self.forgotten)

    def is_open(self, route: RouteRow) -> bool:
        return self.status(route).is_open

    def open_known(self, world_id: int | None = None) -> list[RouteRow]:
        return [route for route in self.routes if route.known and self.is_open(route) and (world_id is None or touches(route, world_id))]

    def touching(self, world_id: int) -> list[RouteRow]:
        return [route for route in self.routes if touches(route, world_id)]

    def reachable(self, first_world: int | None, second_world: int | None) -> bool:
        if first_world is None or second_world is None:
            return False
        if first_world == second_world:
            return True
        return any(touches(route, first_world) and touches(route, second_world) for route in self.open_known())


def touches(route: RouteRow, world_id: int) -> bool:
    return world_id in (route.world_a_id, route.world_b_id)


def other_end(route: RouteRow, world_id: int) -> int:
    return route.world_b_id if route.world_a_id == world_id else route.world_a_id


def method_label(method: TravelMethod) -> str:
    return TRAVEL_METHODS[method].label


def number_word(value: int) -> str:
    return NUMBER_WORDS[value] if 0 <= value < len(NUMBER_WORDS) else str(value)


async def world_name(session: AsyncSession, world_id: int) -> str:
    world = await session.get(WorldRow, world_id)
    return world.name if world is not None else f"world {world_id}"


@dataclass(frozen=True)
class RouteSpec:
    first_world_id: int
    second_world_id: int
    method: TravelMethod
    controller_id: int | None = None
    vehicle_id: int | None = None
    builder_son_id: int | None = None
    known: bool = True
    description: str | None = None


async def _star_of(session: AsyncSession, world: WorldRow) -> int | None:
    seen: set[int] = set()
    current = world
    while current.parent_world_id is not None and current.id not in seen:
        seen.add(current.id)
        parent = await session.get(WorldRow, current.parent_world_id)
        if parent is None:
            break
        current = parent
    return current.star_id


async def open_route(session: AsyncSession, rules: Rules, rng: SeededRandom, epoch: int, spec: RouteSpec) -> RouteRow:
    if spec.method not in TRAVEL_METHODS:
        raise ValidationFailedError("Unknown travel method.")
    if spec.first_world_id == spec.second_world_id:
        raise ValidationFailedError("A route must connect two different worlds.")
    first = await session.get(WorldRow, spec.first_world_id)
    second = await session.get(WorldRow, spec.second_world_id)
    if first is None or second is None:
        raise NotFoundError("No such world.")
    if Discovery.FORGOTTEN in (first.discovery, second.discovery):
        raise ValidationFailedError("A route cannot be opened to a forgotten world.")
    statement = select(RouteRow).where(
        RouteRow.active.is_(True),
        RouteRow.method == spec.method,
        or_(
            (RouteRow.world_a_id == first.id) & (RouteRow.world_b_id == second.id),
            (RouteRow.world_a_id == second.id) & (RouteRow.world_b_id == first.id),
        ),
    )
    existing: RouteRow | None = await session.scalar(statement.order_by(RouteRow.id).limit(1))
    if existing is not None:
        existing.known = existing.known or spec.known
        await session.flush()
        return existing
    travel = rules.travel
    profile = travel_method_profile(rules, spec.method)
    terrain = mechanics_of(first.world_type).route_danger(rules) + mechanics_of(second.world_type).route_danger(rules)
    danger = clamp_int(
        profile.danger + rng.die(travel.route_danger_die) - travel.route_danger_shift + terrain, travel.route_danger_min, travel.route_danger_max
    )
    route = RouteRow(
        world_a_id=first.id,
        world_b_id=second.id,
        method=spec.method,
        duration_epochs=profile.duration_epochs,
        danger=danger,
        known=spec.known,
        controller_entity_id=spec.controller_id,
        vehicle_entity_id=spec.vehicle_id,
        builder_son_id=spec.builder_son_id,
        bound_star_id=await _star_of(session, first) if spec.method is TravelMethod.LIGHT_SAIL else None,
        description=spec.description,
        created_epoch=epoch,
        active=True,
    )
    session.add(route)
    await session.flush()
    return route


@dataclass(frozen=True)
class RouteView:
    route: RouteRow
    status: RouteStatus
    method_name: str
    first_name: str
    second_name: str
    controller_name: str | None


async def route_views(session: AsyncSession, rules: Rules, epoch: int, world_id: int | None = None, *, include_all: bool = False) -> list[RouteView]:
    book = await RouteBook.load(session, rules, epoch)
    chosen = book.routes if include_all else book.open_known()
    views: list[RouteView] = []
    for route in chosen:
        if world_id is not None and not touches(route, world_id):
            continue
        controller = await session.get(EntityRow, route.controller_entity_id) if route.controller_entity_id is not None else None
        views.append(
            RouteView(
                route,
                book.status(route),
                method_label(route.method),
                await world_name(session, route.world_a_id),
                await world_name(session, route.world_b_id),
                controller.name if controller is not None else None,
            )
        )
    return views


async def route_lines(session: AsyncSession, rules: Rules, epoch: int, world_id: int | None = None) -> list[str]:
    lines: list[str] = []
    for view in await route_views(session, rules, epoch, world_id):
        controlled = f", controlled by {view.controller_name}" if view.controller_name else ""
        route = view.route
        detail = f"{route.duration_epochs} epochs, danger {route.danger}{controlled}"
        lines.append(f"- route#{route.id}: {view.first_name} \u2194 {view.second_name}, {view.method_name} ({detail})")
    return lines


async def has_tamed_mount(session: AsyncSession, traveller_id: int) -> bool:
    statement = (
        select(EntityRow.id)
        .join(BondRow, BondRow.target_node_id == EntityRow.id)
        .where(
            BondRow.source_node_id == traveller_id,
            BondRow.kind == BondKind.TAMED,
            BondRow.state == BondState.ACTIVE,
            EntityRow.status == EntityStatus.CANON,
            or_(
                EntityRow.id.in_(select(EntityTraitRow.entity_id).where(EntityTraitRow.trait == CreatureTrait.FLYING)),
                EntityRow.id.in_(select(EntityFlagRow.entity_id).where(EntityFlagRow.flag == EntityFlag.MEGAFAUNA)),
            ),
        )
    )
    return await session.scalar(statement.limit(1)) is not None


async def _knowledge_problem(session: AsyncSession, traveller: EntityRow, route: RouteRow) -> str | None:
    spec = TRAVEL_METHODS[route.method]
    if spec.required_branch is None or await knows(session, traveller.id, spec.required_branch):
        return None
    controller = route.controller_entity_id
    if controller is not None and controller != traveller.id and await BondRepository(session).exists_between(traveller.id, controller, BondKind.TRADES_WITH):
        return None
    branch = spec.required_branch.value.replace("_", " ")
    return f'{spec.label} requires the "{branch}" knowledge (or trade with the route\'s controller).'


async def _vehicle_problem(session: AsyncSession, traveller: EntityRow, route: RouteRow) -> str | None:
    vehicle = TRAVEL_METHODS[route.method].required_vehicle
    if vehicle is VehicleKind.MOUNT and not await has_tamed_mount(session, traveller.id):
        return "For a cosmic mount you must have tamed a flying or giant creature."
    if vehicle is VehicleKind.SHIP and not await owned_vessels(session, traveller.id, VehicleKind.SHIP):
        return "You need to own a ship for this route."
    return None


async def _passage_problem(session: AsyncSession, rules: Rules, traveller: EntityRow, route: RouteRow) -> str | None:
    if route.method is TravelMethod.RIVER_OF_DEAD:
        ends = [await session.get(WorldRow, route.world_a_id), await session.get(WorldRow, route.world_b_id)]
        if not any(world is not None and is_realm_of_dead(world.world_type) for world in ends):
            return "The river of the dead only passes through the realm of the dead."
    if route.method is TravelMethod.SPACE_FOLD and await cosmic_access(session, traveller.id, rules.travel.fold_min_abundance) is None:
        return "To fold space you need access to the cosmic travel resource: own a deposit or trade with its owner."
    return None


async def can_use_route(session: AsyncSession, rules: Rules, epoch: int, traveller: EntityRow, route: RouteRow, *, book: RouteBook | None = None) -> str | None:
    if route.method not in TRAVEL_METHODS:
        return "Unknown travel method."
    for problem in (
        await _knowledge_problem(session, traveller, route),
        await _vehicle_problem(session, traveller, route),
        await _passage_problem(session, rules, traveller, route),
    ):
        if problem is not None:
            return problem
    status = (book or await RouteBook.load(session, rules, epoch)).status(route)
    return None if status.is_open else status.reason


def add_event(journey: JourneyRow, epoch: int, kind: JourneyEventKind, text: str, loss: int = 0) -> None:
    events = [*journey.events, JourneyEvent(epoch=epoch, kind=kind, text=text, loss=loss)]
    journey.events = events[-JOURNEY_EVENT_LIMIT:]


@dataclass(frozen=True)
class JourneySpec:
    traveller: EntityRow
    route: RouteRow
    intent: JourneyIntent
    population: int = 0
    vehicle: EntityRow | None = None


async def _gate_sacrifice(ctx: TickContext, spec: JourneySpec, carried: int) -> tuple[int, JourneyEvent | None]:
    if spec.route.method is not TravelMethod.ANCIENT_GATE or await knows(ctx.session, spec.traveller.id, KnowledgeBranch.GATE_LORE):
        return carried, None
    costs = ctx.rules.travel_methods
    spec.route.sacrifice_paid_epoch = ctx.epoch
    if carried > 0:
        lost = min(carried, round(carried * costs.gate_sacrifice_pct / PERCENT))
        text = f"the gate would not open without its true name; {lost} travellers were given to it"
        return carried - lost, JourneyEvent(epoch=ctx.epoch, kind=JourneyEventKind.SACRIFICE, text=text, loss=lost)
    if stat(spec.traveller, HP_KEY) is not None:
        put_stat(ctx.rules, spec.traveller, HP_KEY, stat_or(spec.traveller, HP_KEY, 0) - costs.gate_sacrifice_hp)
        text = "the gate would not open without its true name; the traveller paid in blood"
        return carried, JourneyEvent(epoch=ctx.epoch, kind=JourneyEventKind.SACRIFICE, text=text)
    return carried, None


@dataclass(frozen=True)
class VesselFit:
    carried: int
    extra_epochs: int = 0
    notes: tuple[str, ...] = ()

    def event(self, epoch: int) -> JourneyEvent | None:
        return JourneyEvent(epoch=epoch, kind=JourneyEventKind.OTHER, text="; ".join(self.notes)) if self.notes else None


def vessel_fit(rules: Rules, vehicle: EntityRow | None, duration: int, carried: int) -> VesselFit:
    if vehicle is None or vehicle.entity_type is not EntityType.VESSEL:
        return VesselFit(carried)
    travel = rules.travel
    reach, crew = stat(vehicle, RANGE_KEY), stat(vehicle, CREW_KEY)
    extra = 0
    notes: list[str] = []
    if reach is not None and duration:
        if reach < duration * travel.vessel_range_per_epoch:
            extra = 1
            notes.append(f"the range of {vehicle.name} falls short; it must rest on the way")
        elif reach >= travel.vessel_long_range and duration > 1:
            extra = -1
            notes.append(f"the long range of {vehicle.name} shortens the road")
    if travel.vessel_passengers_per_crew and crew and carried > crew * travel.vessel_passengers_per_crew:
        carried = crew * travel.vessel_passengers_per_crew
        notes.append(f"{vehicle.name} could carry only {carried} travellers")
    return VesselFit(carried, extra, tuple(notes))


async def start_journey(ctx: TickContext, spec: JourneySpec) -> JourneyRow:
    session, rules = ctx.session, ctx.rules
    traveller, route = spec.traveller, spec.route
    origin = traveller.world_id
    if not touches(route, origin):
        raise ValidationFailedError("This route does not leave the traveller's world.")
    destination = other_end(route, origin)
    key = headcount_key(traveller)
    carried = max(0, round(spec.population))
    available = stat(traveller, key)
    if available is not None:
        carried = max(0, min(carried, available - rules.limits.population_floor))
    speed = stat_or(spec.vehicle, SPEED_KEY, rules.travel.default_vessel_speed) if spec.vehicle is not None else rules.travel.default_vessel_speed
    folding = False
    wants_fold = route.method is TravelMethod.SPACE_FOLD or (
        route.method is not TravelMethod.SWALLOWED and route.duration_epochs > 1 and await knows(session, traveller.id, KnowledgeBranch.PATHFINDING)
    )
    if wants_fold:
        folding = await spend_cosmic_resource(ctx, traveller) is not None
    shortened = 1 if speed >= rules.travel.fast_vessel_speed else 0
    fit = vessel_fit(rules, spec.vehicle, route.duration_epochs, carried)
    carried = fit.carried
    remaining = max(1, 1 if folding else route.duration_epochs - shortened + fit.extra_epochs)
    leaving = carried
    carried, sacrifice = await _gate_sacrifice(ctx, spec, carried)
    if available is not None and leaving > 0:
        put_stat(rules, traveller, key, max(rules.limits.population_floor, available - leaving))
    journey = JourneyRow(
        traveller_entity_id=traveller.id,
        route_id=route.id,
        vehicle_entity_id=spec.vehicle.id if spec.vehicle is not None else None,
        origin_world_id=origin,
        destination_world_id=destination,
        intent=spec.intent,
        population=carried,
        epochs_left=remaining,
        status=JourneyStatus.UNDERWAY,
        events=[event for event in (sacrifice, fit.event(ctx.epoch)) if event is not None],
        start_epoch=ctx.epoch,
    )
    session.add(journey)
    await session.flush()
    ctx.count("journeys_started")
    return journey


async def recall_journey(ctx: TickContext, journey_id: int, by: str) -> str:
    journey = await ctx.session.get(JourneyRow, journey_id)
    if journey is None or journey.status not in LIVE_JOURNEYS:
        raise ValidationFailedError("No such expedition on the road.")
    traveller = await ctx.session.get(EntityRow, journey.traveller_entity_id)
    if traveller is not None and journey.population > 0:
        put_stat(ctx.rules, traveller, headcount_key(traveller), headcount(traveller) + journey.population)
    add_event(journey, ctx.epoch, JourneyEventKind.OTHER, f"{by} recalled the expedition; travellers returned home")
    journey.status = JourneyStatus.RECALLED
    journey.end_epoch = ctx.epoch
    target = await world_name(ctx.session, journey.destination_world_id)
    name = traveller.name if traveller is not None else "the travellers"
    text = f"{by} recalled {name}'s expedition to {target}; {journey.population} souls returned home."
    await ctx.chronicle(ChronicleKind.CREATOR_HAND, text, template_key="travel.journey_recalled", entity_ids=[journey.traveller_entity_id])
    return text


async def reveal_hidden_route(ctx: TickContext, route_id: int, by: str) -> str:
    route = await ctx.session.get(RouteRow, route_id)
    if route is None:
        raise NotFoundError("No such route.")
    if route.known:
        raise ValidationFailedError("This route is not hidden.")
    route.known = True
    book = await RouteBook.load(ctx.session, ctx.rules, ctx.epoch)
    closed = "" if book.is_open(route) else " The route is closed for now; it will be used when it opens."
    first, second = await world_name(ctx.session, route.world_a_id), await world_name(ctx.session, route.world_b_id)
    text = f"{by} revealed the hidden route between {first} and {second}: {method_label(route.method)}.{closed}"
    await ctx.chronicle(ChronicleKind.COSMIC, text, template_key="travel.route_revealed_by_hand", feed_category=FeedCategory.GATE)
    return text


async def _community_count(session: AsyncSession, world_id: int) -> int:
    statement = select(EntityRow.id).where(
        EntityRow.world_id == world_id, EntityRow.status == EntityStatus.CANON, EntityRow.entity_type.in_([EntityType.PEOPLE, EntityType.SETTLEMENT])
    )
    return len(list(await session.scalars(statement)))


async def connect_world(ctx: TickContext, world: WorldRow, target_id: int | None = None) -> RouteRow | None:
    session = ctx.session
    if world.discovery is Discovery.FORGOTTEN:
        return None
    touching = await session.scalar(select(RouteRow.id).where(or_(RouteRow.world_a_id == world.id, RouteRow.world_b_id == world.id)).limit(1))
    if touching is not None:
        return None
    others = list(await session.scalars(select(WorldRow).where(WorldRow.id != world.id, WorldRow.discovery != Discovery.FORGOTTEN).order_by(WorldRow.id)))
    if not others:
        return None
    chosen = next((other for other in others if other.id == target_id), None)
    if chosen is None:
        my_star = await _star_of(session, world)
        ranked = []
        for other in others:
            same_star = my_star is not None and await _star_of(session, other) == my_star
            ranked.append((0 if same_star else 1, -await _community_count(session, other.id), other.id, other))
        ranked.sort(key=lambda item: item[:3])
        chosen = ranked[0][3]
    method = hidden_route_method(world.world_type, chosen.world_type)
    return await open_route(
        session,
        ctx.rules,
        ctx.rng("stitch"),
        ctx.epoch,
        RouteSpec(chosen.id, world.id, method, known=False, description="The cosmos's own stitch: a passage nobody knows yet."),
    )


async def connect_all_worlds(ctx: TickContext) -> int:
    opened = 0
    for world in list(await ctx.session.scalars(select(WorldRow).where(WorldRow.discovery != Discovery.FORGOTTEN).order_by(WorldRow.id))):
        if await connect_world(ctx, world) is not None:
            opened += 1
    return opened


async def extend_alignment(session: AsyncSession, until: int) -> int:
    cosmos = await CosmosRepository(session).require_cosmos()
    cosmos.alignment_until_epoch = max(cosmos.alignment_until_epoch or 0, until)
    await session.flush()
    return cosmos.alignment_until_epoch


async def open_alignment(ctx: TickContext, methods: Iterable[TravelMethod], danger_add: int = 0, duration: int | None = None) -> int:
    session, rules = ctx.session, ctx.rules
    chosen = set(methods)
    span = duration if duration is not None else rules.sky.alignment_open_epochs
    forgotten = await forgotten_world_ids(session)
    routes = [
        route
        for route in await session.scalars(select(RouteRow).order_by(RouteRow.id))
        if route.world_a_id not in forgotten and route.world_b_id not in forgotten
    ]
    revealed = 0
    for route in routes:
        if not route.known:
            route.known = True
            revealed += 1
        if route.method not in chosen:
            continue
        if not route.active and route.temp_closed_until_epoch is not None:
            route.active = True
            route.temp_closed_until_epoch = None
            route.closure = None
        elif not route.active and route.closure in (None, RouteClosure.SEALED):
            route.active = True
            route.temp_open_until_epoch = ctx.epoch + span
            route.closure = None
        if danger_add and route.active:
            route.danger = min(rules.sky.alignment_danger_cap, route.danger + danger_add)
    if TravelMethod.SLINGSHOT_ORBIT in chosen:
        await extend_alignment(session, ctx.epoch + span)
    await session.flush()
    return revealed


@dataclass(frozen=True)
class SeverResult:
    route_id: int
    severed_until: int
    duration: int
    lost: int
    waiting: int
    revealed: bool
    text: str


async def sever_route(
    ctx: TickContext, route_id: int, *, duration: int | None = None, by: str | None = None, reason: str | None = None, write: bool = True
) -> SeverResult:
    session, rules = ctx.session, ctx.rules
    route = await session.get(RouteRow, route_id)
    if route is None:
        raise NotFoundError("No such route.")
    if not route.active:
        raise ValidationFailedError("This route is already closed.")
    rng = ctx.rng("sever")
    was_hidden = not route.known
    revealed = was_hidden and rng.chance(rules.beyond.storm_reveal_chance)
    if duration is not None and duration > 0:
        span = round(duration)
    elif by is not None:
        span = rules.beyond.sever_route_epochs
    else:
        span = rules.beyond.storm_closed_min_epochs + rng.die(rules.beyond.storm_closed_die)
    route.active = False
    route.closure = RouteClosure.SEVERED
    route.temp_closed_until_epoch = ctx.epoch + span
    route.temp_open_until_epoch = None
    route.known = route.known or revealed
    lost = waiting = 0
    for journey in await session.scalars(select(JourneyRow).where(JourneyRow.route_id == route.id, JourneyRow.status.in_(LIVE_JOURNEYS))):
        if rng.chance(rules.beyond.storm_loss_chance):
            journey.status = JourneyStatus.LOST
            journey.end_epoch = ctx.epoch
            add_event(journey, ctx.epoch, JourneyEventKind.VOID_STORM, "the void storm swallowed the expedition")
            lost += 1
        else:
            journey.status = JourneyStatus.WAITING
            waiting += 1
    first, second = await world_name(session, route.world_a_id), await world_name(session, route.world_b_id)
    opener = f"{by} unleashed a void storm{f' ({reason})' if reason else ''}: " if by else "A void storm "
    verb = "it swallowed" if by else "swallowed"
    hidden_word = "hidden " if was_hidden else ""
    text = f"{opener}{verb} the {hidden_word}route between {first} and {second}; its stitch closes at the start of Epoch {ctx.epoch + span}"
    if lost or waiting:
        text += f"; of the {lost + waiting} expeditions on the road, {lost} were lost, {waiting} survived and wait for the stitch to close"
    text += "."
    if revealed:
        text += " As the route snapped, light leaking through the crack betrayed it: it is no longer hidden; it can be used again once the storm calms."
    if write:
        kind = ChronicleKind.COSMIC if by else ChronicleKind.HORROR
        await ctx.chronicle(kind, text, template_key="travel.route_severed", feed_category=FeedCategory.GATE)
    await session.flush()
    return SeverResult(route.id, ctx.epoch + span, span, lost, waiting, revealed, text)


async def stitch_route(ctx: TickContext, route_id: int, by: str) -> str:
    session = ctx.session
    route = await session.get(RouteRow, route_id)
    if route is None:
        raise NotFoundError("No such route.")
    if route.active:
        raise ValidationFailedError("This route is already open.")
    forgotten = await forgotten_world_ids(session)
    if route.world_a_id in forgotten or route.world_b_id in forgotten:
        raise ValidationFailedError("A world at the end of this route was forgotten; the route inside the mist cannot be stitched.")
    if route.method is TravelMethod.DIVINE_BRIDGE and route.builder_son_id is not None:
        builder = await session.get(SonRow, route.builder_son_id)
        if builder is None or builder.status is not SonStatus.ACTIVE:
            raise ValidationFailedError("The bridge's builder fell; the bridge collapsed with him, nothing remains to stitch.")
    severed = route.temp_closed_until_epoch is not None or route.closure in (RouteClosure.SEVERED, RouteClosure.SNAPPED)
    route.active = True
    route.closure = None
    route.temp_closed_until_epoch = None
    route.temp_open_until_epoch = None
    action = "re-stitched the severed route" if severed else "broke the seal of the sealed route and reopened it"
    text = f"{by} {action} between {await world_name(session, route.world_a_id)} and {await world_name(session, route.world_b_id)}."
    await ctx.chronicle(ChronicleKind.COSMIC, text, template_key="travel.route_stitched", feed_category=FeedCategory.GATE)
    await session.flush()
    return text


async def _star_worlds(session: AsyncSession, star_id: int) -> set[int]:
    worlds = list(await session.scalars(select(WorldRow).order_by(WorldRow.id)))
    return {world.id for world in worlds if await _star_of(session, world) == star_id}


async def snap_sail_routes(ctx: TickContext, star_id: int) -> int:
    session = ctx.session
    lit = await _star_worlds(session, star_id)
    rng = ctx.rng("sail_snap")
    snapped = 0
    statement = select(RouteRow).where(RouteRow.method == TravelMethod.LIGHT_SAIL, RouteRow.active.is_(True)).order_by(RouteRow.id)
    for route in list(await session.scalars(statement)):
        if route.bound_star_id != star_id and route.world_a_id not in lit and route.world_b_id not in lit:
            continue
        route.active = False
        route.closure = RouteClosure.SNAPPED
        snapped += 1
        for journey in await session.scalars(select(JourneyRow).where(JourneyRow.route_id == route.id, JourneyRow.status.in_(LIVE_JOURNEYS))):
            add_event(journey, ctx.epoch, JourneyEventKind.SAIL_SNAPPED, "the sail snapped when its star died")
            journey.status = JourneyStatus.LOST if rng.chance(ctx.rules.travel_methods.sail_snap_loss_pct) else JourneyStatus.STRANDED
            journey.end_epoch = ctx.epoch if journey.status is JourneyStatus.LOST else None
    await session.flush()
    return snapped


async def restore_sail_routes(session: AsyncSession, star_id: int) -> int:
    lit = await _star_worlds(session, star_id)
    restored = 0
    statement = select(RouteRow).where(RouteRow.closure == RouteClosure.SNAPPED).order_by(RouteRow.id)
    for route in list(await session.scalars(statement)):
        if route.bound_star_id == star_id or route.world_a_id in lit or route.world_b_id in lit:
            route.active = True
            route.closure = None
            restored += 1
            for journey in await session.scalars(select(JourneyRow).where(JourneyRow.route_id == route.id, JourneyRow.status == JourneyStatus.STRANDED)):
                journey.status = JourneyStatus.UNDERWAY
    await session.flush()
    return restored


@dataclass(frozen=True)
class JourneyView:
    journey: JourneyRow
    traveller_name: str | None
    target_name: str
    vehicle_name: str | None


async def journey_views(session: AsyncSession, limit: int) -> list[JourneyView]:
    statement = select(JourneyRow).order_by(JourneyRow.id.desc()).limit(limit)
    views: list[JourneyView] = []
    for journey in await session.scalars(statement):
        traveller = await session.get(EntityRow, journey.traveller_entity_id)
        vehicle = await session.get(EntityRow, journey.vehicle_entity_id) if journey.vehicle_entity_id is not None else None
        views.append(
            JourneyView(
                journey, traveller.name if traveller else None, await world_name(session, journey.destination_world_id), vehicle.name if vehicle else None
            )
        )
    return views
