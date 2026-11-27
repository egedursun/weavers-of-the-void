from dataclasses import dataclass
from math import ceil

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.carriers import CARRIER_OF, CARRIERS
from aerona.catalog.kinds.trade_modes import TRADE_MODES
from aerona.catalog.life.economy import OPEN, SHUTTING_RESPONSES
from aerona.catalog.life_traits import CARRYING_ROUTES
from aerona.catalog.preservation import PRESERVATION, WATER_DEFAULT
from aerona.constants.units import PERCENT
from aerona.db.tables.discovery import ArtFormPractitionerRow
from aerona.db.tables.economy import TradeFlowRow, TradeRouteProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import WorldSeasonRow
from aerona.db.tables.evolution import PlagueResponseRow
from aerona.db.tables.polity import TreatyClauseRow, TreatyProfileRow
from aerona.db.tables.settlement import SettlementInfrastructureRow
from aerona.db.tables.urban import ConvoyRow, FleetRow
from aerona.db.tables.warfare import WarSideRow
from aerona.db.write_guard import held
from aerona.domain.enums.disease import OutbreakStatus, SpreadPath
from aerona.domain.enums.economy import TradeMode, TradeRouteStatus
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.intrigue import BeliefSource
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import ClauseKind, TreatyStatus
from aerona.domain.enums.urban import ConvoyStatus, PreservationMethod, TransportKind
from aerona.engine.context import TickContext
from aerona.engine.cuisine.dishes import carry_dish
from aerona.engine.disease.book import DiseaseBook
from aerona.engine.disease.outbreaks import open_outbreak
from aerona.engine.economy.purse import take_coin
from aerona.engine.factions.privateers import privateers_against
from aerona.engine.intrigue.beliefs import DEFENCE, believe
from aerona.engine.lore.art_forms import practise
from aerona.engine.lore.research import has_technique
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.standing import still_standing
from aerona.engine.primitives.stats import move_stat, shift_bounded, stat, stat_or
from aerona.engine.recording.record import record
from aerona.engine.renown.currencies import realm_of_community
from aerona.engine.vehicles.caravans import carrier_group, raid_carriers
from aerona.rules.registry import Rules

WEALTH = "wealth"

ANIMAL_KINDS = frozenset(kind for kind in TransportKind if CARRIERS[CARRIER_OF[kind]].upkeep == "feed" and CARRIERS[CARRIER_OF[kind]].capacity <= 10)
SICK_SEVERITY = 20
MIGRANTS = "migrants"
MISSIONARIES = "missionaries"
PILGRIMS = "pilgrims"


@dataclass
class ConvoyTally:
    sent: int = 0
    arrived: int = 0
    raided: int = 0
    lost: int = 0
    delayed: int = 0
    worn: int = 0
    carriers_lost: int = 0


def fleet_capacity(rules: Rules, fleet: FleetRow) -> int:
    each = rules.convoys.per_animal if fleet.kind in ANIMAL_KINDS else rules.convoys.per_vehicle * max(1, CARRIERS[CARRIER_OF[fleet.kind]].capacity) // 10
    kept = rules.fleets.worn_pct / PERCENT + (1 - rules.fleets.worn_pct / PERCENT) * fleet.condition / PERCENT
    return round_half_up(fleet.count * each * kept)


async def route_capacity(session: AsyncSession, route_id: int) -> int | None:
    rows = list(await session.scalars(select(ConvoyRow.capacity).where(ConvoyRow.route_entity_id == route_id, ConvoyRow.status.in_(OPEN))))
    return sum(rows) if rows else None


async def harbour_limit(session: AsyncSession, rules: Rules, profile: TradeRouteProfileRow) -> int | None:
    if not TRADE_MODES[profile.mode].seagoing:
        return None
    limits = []
    for end in (profile.first_market_id, profile.second_market_id):
        port = await session.get(SettlementInfrastructureRow, end)
        if port is not None:
            limits.append(port.harbour_capacity * rules.ports.per_berth)
    return min(limits) if limits else None


async def vehicle_for(ctx: TickContext, owner_id: int, mode: TradeMode) -> TransportKind:
    fitting = []
    for kind in TransportKind:
        spec = CARRIERS[CARRIER_OF[kind]]
        if spec.capacity > 0 and mode in spec.modes and (spec.technique is None or await has_technique(ctx.session, owner_id, spec.technique)):
            fitting.append(kind)
    return max(fitting, key=lambda kind: (CARRIERS[CARRIER_OF[kind]].capacity, kind.value), default=TransportKind.PACK_ANIMALS)


async def fleet_of(ctx: TickContext, owner_id: int, mode: TradeMode, capacity: int) -> FleetRow:
    kind = await vehicle_for(ctx, owner_id, mode)
    fleet = await ctx.session.get(FleetRow, (owner_id, kind))
    if fleet is None:
        each = ctx.rules.convoys.per_animal if kind in ANIMAL_KINDS else ctx.rules.convoys.per_vehicle
        fleet = FleetRow(owner_entity_id=owner_id, kind=kind, count=max(1, capacity // max(1, each)), age=0, condition=PERCENT, locked=[])
        ctx.session.add(fleet)
        await ctx.session.flush()
    return fleet


async def preservation_for(ctx: TickContext, owner_id: int, cargo: dict[str, int], mode: TradeMode) -> PreservationMethod:
    if not cargo:
        return PreservationMethod.NONE
    known = [method for method, spec in PRESERVATION.items() if spec.technique is not None and await has_technique(ctx.session, owner_id, spec.technique)]
    if known:
        return max(known, key=lambda method: PRESERVATION[method].keeping(ctx.rules))
    return WATER_DEFAULT if TRADE_MODES[mode].waterborne else PreservationMethod.NONE


async def load_cargo(ctx: TickContext, route_id: int) -> dict[str, int]:
    found: dict[str, int] = {}
    for commodity, volume in await ctx.session.execute(
        select(TradeFlowRow.commodity, TradeFlowRow.volume).where(TradeFlowRow.route_entity_id == route_id, TradeFlowRow.epoch == ctx.epoch - 1)
    ):
        found[commodity.value] = found.get(commodity.value, 0) + volume
    return found


def split_evenly(amount: int, parts: int) -> list[int]:
    whole, extra = divmod(max(0, amount), max(1, parts))
    return [whole + (1 if index < extra else 0) for index in range(max(1, parts))]


def split_cargo(cargo: dict[str, int], parts: int) -> list[dict[str, int]]:
    loads: list[dict[str, int]] = [{} for _ in range(max(1, parts))]
    for commodity, amount in sorted(cargo.items()):
        for load, share in zip(loads, split_evenly(amount, parts), strict=True):
            if share > 0:
                load[commodity] = share
    return loads


def convoys_wanted(rules: Rules, cargo: dict[str, int]) -> int:
    table = rules.convoys
    return min(table.per_epoch(table.per_route), max(1, ceil(sum(cargo.values()) / table.traffic_per_convoy)))


async def dispatch(ctx: TickContext, route: EntityRow, profile: TradeRouteProfileRow, tally: ConvoyTally, parts: int = 1) -> None:
    table = ctx.rules.convoys
    owner_id = profile.controller_entity_id or profile.first_market_id
    fleet = await fleet_of(ctx, owner_id, profile.mode, stat_or(route, "capacity", 0))
    capacity = fleet_capacity(ctx.rules, fleet)
    cargo = await load_cargo(ctx, route.id)
    vehicles = 0 if fleet.kind in ANIMAL_KINDS else fleet.count
    carriers = await carrier_group(ctx.session, owner_id, profile.mode)
    if carriers is not None:
        capacity = max(capacity, carriers.cargo)
        vehicles = max(vehicles, carriers.group.count)
    animals = fleet.count if fleet.kind in ANIMAL_KINDS else 0
    parts = max(1, min(parts, vehicles + animals))
    origin = await ctx.session.get(EntityRow, profile.first_market_id)
    preservation = await preservation_for(ctx, owner_id, cargo, profile.mode)
    guards = round_half_up(stat_or(origin, "defense", 0) / 10) if origin is not None else 0
    shares = zip(split_cargo(cargo, parts), split_evenly(capacity, parts), split_evenly(vehicles, parts), split_evenly(animals, parts), strict=True)
    for part, (load, room, wagons, beasts) in enumerate(shares):
        rng = ctx.rng(f"convoy.{route.id}" if part == 0 else f"convoy.{route.id}.{part}")
        passengers = {PILGRIMS: rng.integer(0, table.pilgrims), MIGRANTS: rng.integer(0, table.pilgrims), MISSIONARIES: rng.integer(0, table.pilgrims // 2)}
        ctx.session.add(
            ConvoyRow(
                owner_entity_id=owner_id,
                route_entity_id=route.id,
                cargo=load,
                preservation=preservation if load else PreservationMethod.NONE,
                animals=beasts,
                vehicles=wagons,
                guards=guards,
                passengers=passengers,
                season=ctx.epoch,
                status=ConvoyStatus.TRAVELLING,
                region_entity_id=None,
                capacity=room,
                departed_epoch=ctx.epoch,
                locked=[],
            )
        )
        tally.sent += 1


def fate_of(
    rules: Rules, convoy: ConvoyRow, profile: TradeRouteProfileRow, roll: float, *, privateers: bool = False, war: bool = False, escorted: bool = False
) -> ConvoyStatus:
    table = rules.convoys
    hunted = (rules.crime_orgs.privateer_pct if privateers else 0) + (table.war_raid_pct if war else 0) - (table.escort_relief if escorted else 0)
    raid = max(0.0, table.raid_pct * (profile.danger_bandits + profile.danger_beasts) / PERCENT + hunted - convoy.guards * table.guard_relief)
    storm = table.storm_pct * profile.danger_sea / PERCENT if TRADE_MODES[profile.mode].seagoing else 0.0
    delay = table.delay_pct * profile.danger_weather / PERCENT
    if roll < raid:
        return ConvoyStatus.RAIDED
    if roll < raid + storm:
        return ConvoyStatus.LOST
    if roll < raid + storm + delay and convoy.status is not ConvoyStatus.DELAYED:
        return ConvoyStatus.DELAYED
    return ConvoyStatus.ARRIVED


async def sides_of(session: AsyncSession, convoy: ConvoyRow, profile: TradeRouteProfileRow) -> tuple[int | None, int | None]:
    owner = convoy.owner_entity_id if convoy.owner_entity_id is not None else profile.first_market_id
    return await realm_of_community(session, owner) or owner, await realm_of_community(session, profile.second_market_id) or profile.second_market_id


async def opposed(session: AsyncSession, first: int, second: int) -> bool:
    mine = {row.war_id: row.side for row in await session.scalars(select(WarSideRow).where(WarSideRow.entity_id == first, WarSideRow.left_epoch.is_(None)))}
    theirs = await session.scalars(select(WarSideRow).where(WarSideRow.entity_id == second, WarSideRow.left_epoch.is_(None)))
    return any(row.war_id in mine and mine[row.war_id] is not row.side for row in theirs)


async def escorted_by_treaty(session: AsyncSession, first: int | None, second: int | None) -> bool:
    if first is None or second is None or first == second:
        return False
    found = await session.scalar(
        select(TreatyClauseRow.id)
        .join(TreatyProfileRow, TreatyProfileRow.treaty_entity_id == TreatyClauseRow.treaty_entity_id)
        .where(
            TreatyProfileRow.status == TreatyStatus.IN_FORCE,
            TreatyClauseRow.kind == ClauseKind.TRADE_RIGHTS,
            or_(
                (TreatyClauseRow.obligor_node_id == first) & (TreatyClauseRow.beneficiary_node_id == second),
                (TreatyClauseRow.obligor_node_id == second) & (TreatyClauseRow.beneficiary_node_id == first),
            ),
        )
        .limit(1)
    )
    return found is not None


async def carry_culture(ctx: TickContext, origin: EntityRow, destination: EntityRow) -> None:
    table = ctx.rules.convoys
    rng = ctx.rng(f"convoy.culture.{origin.id}.{destination.id}.{ctx.epoch}")
    forms = list(
        await ctx.session.scalars(
            select(ArtFormPractitionerRow).where(ArtFormPractitionerRow.practitioner_entity_id == origin.id).order_by(ArtFormPractitionerRow.art_form_entity_id)
        )
    )
    for row in forms:
        if await ctx.session.get(ArtFormPractitionerRow, (row.art_form_entity_id, destination.id)) is None and rng.chance(table.art_pct):
            await practise(ctx, row.art_form_entity_id, destination.id, row.mastery // 2)
            break
    news = {WEALTH: stat_or(origin, WEALTH, stat(origin, "prosperity") or 0), DEFENCE: stat_or(origin, DEFENCE, 0)}
    for key, truth in news.items():
        await believe(ctx, destination.id, origin.id, key, truth, source=BeliefSource.MESSAGE, confidence=table.news_confidence)


async def arrive(ctx: TickContext, convoy: ConvoyRow, profile: TradeRouteProfileRow, book: DiseaseBook, atlas: RegionAtlas) -> None:
    origin = await ctx.session.get(EntityRow, profile.first_market_id)
    destination = await ctx.session.get(EntityRow, profile.second_market_id)
    if origin is None or destination is None or held(destination.id):
        return
    if not await still_standing(ctx.session, origin.id) or not await still_standing(ctx.session, destination.id):
        convoy.status = ConvoyStatus.STRANDED
        return
    convoy.region_entity_id = atlas.top_region(destination.id)
    move_stat(origin, destination, "population", convoy.passengers.get(MIGRANTS, 0))
    await carry_dish(ctx, origin, destination)
    shift_bounded(ctx.rules, destination, "piety", convoy.passengers.get(MISSIONARIES, 0) * ctx.rules.convoys.conversion / PERCENT)
    await carry_culture(ctx, origin, destination)
    origin_region = atlas.top_region(origin.id)
    for outbreak in book.outbreaks:
        disease = book.diseases.get(outbreak.disease_entity_id)
        if (
            disease is not None
            and outbreak.region_entity_id == origin_region
            and outbreak.status is not OutbreakStatus.ENDED
            and convoy.region_entity_id is not None
        ):
            await open_outbreak(ctx, book, disease, convoy.region_entity_id, path=SpreadPath.ROUTE, severity=SICK_SEVERITY, source=outbreak)
            break


async def held_back_by(ctx: TickContext, convoy: ConvoyRow, profile: TradeRouteProfileRow) -> ConvoyStatus | None:
    destination = profile.second_market_id
    shut = await ctx.session.scalar(
        select(PlagueResponseRow.disease_entity_id)
        .where(PlagueResponseRow.community_entity_id == destination, PlagueResponseRow.response.in_(SHUTTING_RESPONSES))
        .limit(1)
    )
    if shut is not None and convoy.departed_epoch >= ctx.epoch - ctx.rules.convoys.epochs(ctx.rules.convoys.quarantine_years):
        return ConvoyStatus.QUARANTINED
    if (
        profile.status is TradeRouteStatus.SEASONAL
        and profile.closed_season is not None
        and ctx.rng(f"convoy.stranded.{convoy.id}.{ctx.epoch}").chance(ctx.rules.convoys.stranded_pct)
    ):
        return ConvoyStatus.STRANDED
    return None


async def season_name(ctx: TickContext, route_id: int, position: int | None) -> str:
    route = await ctx.session.get(EntityRow, route_id)
    if route is None or route.world_id is None or position is None:
        return "its closed season"
    name = await ctx.session.scalar(select(WorldSeasonRow.name).where(WorldSeasonRow.world_id == route.world_id, WorldSeasonRow.position == position))
    return name or "its closed season"


async def wait_out(ctx: TickContext, convoy: ConvoyRow, profile: TradeRouteProfileRow, state: ConvoyStatus, tally: ConvoyTally) -> None:
    if state is ConvoyStatus.STRANDED:
        convoy.cargo = {key: max(0, value - value * ctx.rules.convoys.stranded_upkeep // PERCENT) for key, value in convoy.cargo.items()}
        season = await season_name(ctx, convoy.route_entity_id, profile.closed_season)
        await record(ctx, "convoy.stranded", roles={IncidentRole.SUBJECT: convoy.route_entity_id}, facts={"season": season})
    else:
        await record(ctx, "convoy.quarantined", roles={IncidentRole.SUBJECT: convoy.route_entity_id, IncidentRole.PLACE: profile.second_market_id})
    tally.delayed += 1


async def resolve(ctx: TickContext, convoy: ConvoyRow, tally: ConvoyTally, book: DiseaseBook, atlas: RegionAtlas) -> None:
    profile = await ctx.session.get(TradeRouteProfileRow, convoy.route_entity_id)
    if profile is None or "status" in convoy.locked:
        return
    privateers = await privateers_against(ctx.session, convoy.owner_entity_id)
    mine, theirs = await sides_of(ctx.session, convoy, profile)
    war = mine is not None and theirs is not None and mine != theirs and await opposed(ctx.session, mine, theirs)
    roll = ctx.rng(f"convoy_fate.{convoy.id}").random() * PERCENT
    status = fate_of(
        ctx.rules,
        convoy,
        profile,
        roll,
        privateers=privateers,
        war=war,
        escorted=await escorted_by_treaty(ctx.session, mine, theirs),
    )
    held_back = await held_back_by(ctx, convoy, profile)
    if held_back is not None:
        convoy.status = held_back
        await wait_out(ctx, convoy, profile, held_back, tally)
        return
    convoy.status = status
    if status is ConvoyStatus.ARRIVED:
        convoy.arrived_epoch = ctx.epoch
        tally.arrived += 1
        await arrive(ctx, convoy, profile, book, atlas)
    elif status is ConvoyStatus.DELAYED:
        tally.delayed += 1
    else:
        cargo_lost = sum(convoy.cargo.values())
        convoy.cargo = {}
        tally.raided += int(status is ConvoyStatus.RAIDED)
        tally.lost += int(status is ConvoyStatus.LOST)
        carriers = await carrier_group(ctx.session, convoy.owner_entity_id, profile.mode) if convoy.owner_entity_id is not None else None
        if carriers is not None:
            struck = await raid_carriers(ctx, carriers.group, 2 if status is ConvoyStatus.LOST else 1, f"convoy.{convoy.id}")
            tally.carriers_lost += struck.lost
        fate = "raided" if status is ConvoyStatus.RAIDED else "lost"
        carried = {"cargo_lost": cargo_lost} if cargo_lost > 0 else {}
        await record(
            ctx,
            f"trade.convoy_{fate}" if cargo_lost > 0 else f"trade.convoy_{fate}_unladen",
            roles={IncidentRole.SUBJECT: convoy.route_entity_id, IncidentRole.OWNER: convoy.owner_entity_id, IncidentRole.OPPONENT: theirs if war else None},
            facts={
                "mode": profile.mode,
                **carried,
                "roll": round(roll),
                "at_war": int(war),
                "carriers_lost": struck.lost if carriers is not None else 0,
            },
        )


async def wear_fleets(ctx: TickContext, tally: ConvoyTally) -> None:
    table = ctx.rules.fleets
    for fleet in list(await ctx.session.scalars(select(FleetRow).order_by(FleetRow.owner_entity_id, FleetRow.kind))):
        owner = await ctx.session.get(EntityRow, fleet.owner_entity_id)
        if owner is None or held(owner.id):
            continue
        if "age" not in fleet.locked:
            fleet.age += 1
        if "condition" not in fleet.locked:
            fleet.condition = clamp_int(fleet.condition - table.wear, 0, PERCENT)
        await take_coin(ctx.session, ctx.rules, owner, fleet.count * table.upkeep)
        if fleet.condition < table.replace_at and await take_coin(ctx.session, ctx.rules, owner, fleet.count * table.replace_cost):
            fleet.condition, fleet.age = PERCENT, 0
            tally.worn += 1


async def run_convoys(ctx: TickContext, tally: ConvoyTally) -> None:
    book = await DiseaseBook.load(ctx.session, ctx.rules, ctx.epoch)
    atlas = await RegionAtlas.load(ctx.session)
    for convoy in list(await ctx.session.scalars(select(ConvoyRow).where(ConvoyRow.status.in_(OPEN)).order_by(ConvoyRow.id))):
        if not held(convoy.route_entity_id):
            await resolve(ctx, convoy, tally, book, atlas)
    routes = await ctx.session.execute(
        select(EntityRow, TradeRouteProfileRow)
        .join(TradeRouteProfileRow, TradeRouteProfileRow.route_entity_id == EntityRow.id)
        .where(EntityRow.status == EntityStatus.CANON, TradeRouteProfileRow.status.in_(CARRYING_ROUTES))
        .order_by(EntityRow.id)
    )
    most = ctx.rules.convoys.per_epoch(ctx.rules.convoys.per_route)
    for route, profile in routes.all():
        if held(route.id):
            continue
        sent = len(list(await ctx.session.scalars(select(ConvoyRow.id).where(ConvoyRow.route_entity_id == route.id, ConvoyRow.status.in_(OPEN)))))
        parts = min(convoys_wanted(ctx.rules, await load_cargo(ctx, route.id)), most - sent)
        if parts > 0:
            await dispatch(ctx, route, profile, tally, parts)
    await ctx.session.flush()
