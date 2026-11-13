from dataclasses import dataclass

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.discovery import ArtFormPractitionerRow
from aerona.db.tables.economy import TradeFlowRow, TradeRouteProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import TreatyClauseRow, TreatyProfileRow
from aerona.db.tables.settlement import SettlementInfrastructureRow
from aerona.db.tables.urban import ConvoyRow, FleetRow
from aerona.db.tables.warfare import WarSideRow
from aerona.db.write_guard import held
from aerona.domain.enums.disease import OutbreakStatus, SpreadPath
from aerona.domain.enums.economy import TradeMode, TradeRouteStatus
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.intrigue import BeliefSource
from aerona.domain.enums.polity import ClauseKind, TreatyStatus
from aerona.domain.enums.urban import ConvoyStatus, Preservation, TransportKind
from aerona.engine.context import TickContext
from aerona.engine.cuisine.dishes import carry_dish
from aerona.engine.disease.book import DiseaseBook
from aerona.engine.disease.outbreaks import open_outbreak
from aerona.engine.economy.purse import take_coin
from aerona.engine.factions.privateers import privateers_against
from aerona.engine.intrigue.beliefs import DEFENCE, believe
from aerona.engine.lore.art_forms import practise
from aerona.engine.notes import note
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import move_stat, shift_bounded, stat, stat_or
from aerona.engine.renown.currencies import realm_of_community
from aerona.engine.vehicles.caravans import carrier_group, raid_carriers
from aerona.rules.registry import Rules

WEALTH = "wealth"

VEHICLE_OF = {TradeMode.SEA: TransportKind.SHIPS, TradeMode.RIVER: TransportKind.RIVER_BOATS, TradeMode.ROAD: TransportKind.WAGONS}
ANIMAL_KINDS = frozenset({TransportKind.PACK_ANIMALS})
OPEN = (ConvoyStatus.LOADING, ConvoyStatus.TRAVELLING, ConvoyStatus.DELAYED)
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
    each = rules.convoys.per_animal if fleet.kind in ANIMAL_KINDS else rules.convoys.per_vehicle
    kept = rules.fleets.worn_pct / PERCENT + (1 - rules.fleets.worn_pct / PERCENT) * fleet.condition / PERCENT
    return round_half_up(fleet.count * each * kept)


async def route_capacity(session: AsyncSession, route_id: int) -> int | None:
    rows = list(await session.scalars(select(ConvoyRow.capacity).where(ConvoyRow.route_entity_id == route_id, ConvoyRow.status.in_(OPEN))))
    return sum(rows) if rows else None


async def harbour_limit(session: AsyncSession, rules: Rules, profile: TradeRouteProfileRow) -> int | None:
    if profile.mode is not TradeMode.SEA:
        return None
    limits = []
    for end in (profile.first_market_id, profile.second_market_id):
        port = await session.get(SettlementInfrastructureRow, end)
        if port is not None:
            limits.append(port.harbour_capacity * rules.ports.per_berth)
    return min(limits) if limits else None


async def fleet_of(ctx: TickContext, owner_id: int, mode: TradeMode, capacity: int) -> FleetRow:
    kind = VEHICLE_OF.get(mode, TransportKind.PACK_ANIMALS)
    fleet = await ctx.session.get(FleetRow, (owner_id, kind))
    if fleet is None:
        each = ctx.rules.convoys.per_animal if kind in ANIMAL_KINDS else ctx.rules.convoys.per_vehicle
        fleet = FleetRow(owner_entity_id=owner_id, kind=kind, count=max(1, capacity // max(1, each)), age=0, condition=PERCENT, locked=[])
        ctx.session.add(fleet)
        await ctx.session.flush()
    return fleet


def preservation_for(cargo: dict[str, int], mode: TradeMode) -> Preservation:
    return Preservation.SALTED if mode in (TradeMode.SEA, TradeMode.RIVER) and cargo else Preservation.NONE


async def load_cargo(ctx: TickContext, route_id: int) -> dict[str, int]:
    found: dict[str, int] = {}
    for commodity, volume in await ctx.session.execute(
        select(TradeFlowRow.commodity, TradeFlowRow.volume).where(TradeFlowRow.route_entity_id == route_id, TradeFlowRow.epoch == ctx.epoch - 1)
    ):
        found[commodity.value] = found.get(commodity.value, 0) + volume
    return found


async def dispatch(ctx: TickContext, route: EntityRow, profile: TradeRouteProfileRow, tally: ConvoyTally) -> None:
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
    origin = await ctx.session.get(EntityRow, profile.first_market_id)
    rng = ctx.rng(f"convoy.{route.id}")
    passengers = {PILGRIMS: rng.integer(0, table.pilgrims), MIGRANTS: rng.integer(0, table.pilgrims), MISSIONARIES: rng.integer(0, table.pilgrims // 2)}
    ctx.session.add(
        ConvoyRow(
            owner_entity_id=owner_id,
            route_entity_id=route.id,
            cargo=cargo,
            preservation=preservation_for(cargo, profile.mode),
            animals=animals,
            vehicles=vehicles,
            guards=round_half_up(stat_or(origin, "defense", 0) / 10) if origin is not None else 0,
            passengers=passengers,
            season=ctx.epoch,
            status=ConvoyStatus.TRAVELLING,
            region_entity_id=None,
            capacity=capacity,
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
    storm = table.storm_pct * profile.danger_sea / PERCENT if profile.mode is TradeMode.SEA else 0.0
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


async def resolve(ctx: TickContext, convoy: ConvoyRow, tally: ConvoyTally, book: DiseaseBook, atlas: RegionAtlas) -> None:
    profile = await ctx.session.get(TradeRouteProfileRow, convoy.route_entity_id)
    if profile is None or "status" in convoy.locked:
        return
    privateers = await privateers_against(ctx.session, convoy.owner_entity_id)
    mine, theirs = await sides_of(ctx.session, convoy, profile)
    war = mine is not None and theirs is not None and mine != theirs and await opposed(ctx.session, mine, theirs)
    status = fate_of(
        ctx.rules,
        convoy,
        profile,
        ctx.rng(f"convoy_fate.{convoy.id}").random() * PERCENT,
        privateers=privateers,
        war=war,
        escorted=await escorted_by_treaty(ctx.session, mine, theirs),
    )
    convoy.status = status
    if status is ConvoyStatus.ARRIVED:
        convoy.arrived_epoch = ctx.epoch
        tally.arrived += 1
        await arrive(ctx, convoy, profile, book, atlas)
    elif status is ConvoyStatus.DELAYED:
        tally.delayed += 1
    else:
        convoy.cargo = {}
        tally.raided += int(status is ConvoyStatus.RAIDED)
        tally.lost += int(status is ConvoyStatus.LOST)
        carriers = await carrier_group(ctx.session, convoy.owner_entity_id, profile.mode) if convoy.owner_entity_id is not None else None
        if carriers is not None:
            struck = await raid_carriers(ctx, carriers.group, 2 if status is ConvoyStatus.LOST else 1, f"convoy.{convoy.id}")
            tally.carriers_lost += struck.lost
        route = await ctx.session.get(EntityRow, convoy.route_entity_id)
        if route is not None and status is ConvoyStatus.RAIDED:
            await note(ctx, f"A convoy on {route.name} was raided and its goods taken.", key="trade.convoy_raided", ids=[route.id])
        elif route is not None:
            await note(ctx, f"A convoy on {route.name} was lost at sea.", key="trade.convoy_lost", ids=[route.id])


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
        .where(EntityRow.status == EntityStatus.CANON, TradeRouteProfileRow.status == TradeRouteStatus.OPEN)
        .order_by(EntityRow.id)
    )
    for route, profile in routes.all():
        sent = len(list(await ctx.session.scalars(select(ConvoyRow.id).where(ConvoyRow.route_entity_id == route.id, ConvoyRow.status.in_(OPEN)))))
        if not held(route.id) and sent < ctx.rules.convoys.per_route:
            await dispatch(ctx, route, profile, tally)
    await ctx.session.flush()
