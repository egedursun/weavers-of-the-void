from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass, field

from sqlalchemy import or_, select

from aerona.catalog.commodities import COMMODITIES
from aerona.catalog.kinds.trade_modes import TRADE_MODES
from aerona.constants.units import PERCENT
from aerona.core.grammar import several
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.economy import (
    CurrencyRow,
    MarketPriceRow,
    TradeFlowRow,
    TradeRouteLossRow,
    TradeRouteProfileRow,
    TradeRouteRegionRow,
    TradeRouteTollRow,
)
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import PolityProfileRow
from aerona.db.tables.urban import ConvoyRow
from aerona.db.tables.warfare import ArmyRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.crafts import InsuranceCover
from aerona.domain.enums.culture import Capability, Technique
from aerona.domain.enums.discovery import TheoryDomain
from aerona.domain.enums.divine import DomainHook
from aerona.domain.enums.economy import CommodityKind, GoodsFlow, TradeLoss, TradeMode, TradeRouteStatus, WorkshopKind
from aerona.domain.enums.entity import EntityStatus, EntityType, LegendCategory
from aerona.domain.enums.environment import CoastKind, RiverClass
from aerona.domain.enums.eras import EraChannel
from aerona.domain.enums.loops import BalanceLoop
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.polity import ClauseKind
from aerona.domain.enums.settlement import TreasuryEntry
from aerona.domain.enums.society import KnowledgeBranch, SocialClass
from aerona.domain.enums.urban import PreservationMethod
from aerona.domain.enums.war import WarCause
from aerona.domain.models.entity_stats import LegendStats, TradeRouteStats
from aerona.engine.climes.shifts import sea_navigation
from aerona.engine.context import TickContext
from aerona.engine.crafts.cover import cargo_holders, claim
from aerona.engine.crafts.reckoning import price_gaps
from aerona.engine.crafts.timekeeping import clock_navigation
from aerona.engine.customs.rights import crossing
from aerona.engine.demography.tongues import trade_barrier
from aerona.engine.economy.book import EconomyBook
from aerona.engine.economy.cargo import carriage_factor, spoilage
from aerona.engine.economy.chokepoints import press_route_aims, weigh_chokepoint
from aerona.engine.economy.convoys import OPEN, harbour_limit, route_capacity
from aerona.engine.economy.credit import sell_on_credit
from aerona.engine.economy.good_kinds import GoodBook, good_book
from aerona.engine.economy.markets import Quote
from aerona.engine.economy.route_dangers import CARAVAN_TERRAIN, DANGER_KEYS, Dangers, Lairs, dangers_of, feed_beast, season_pct_of, split, spoil
from aerona.engine.economy.stocks import goods_of, lots_of
from aerona.engine.economy.toll_polities import Realms, fund_polity
from aerona.engine.environment.profile import Works
from aerona.engine.eras.effects import channel_value, tech_relief
from aerona.engine.finance.policy import PolicyBook, PolicyTally, Terms, smuggle
from aerona.engine.folkways.shunning import outsider_barrier
from aerona.engine.interconnect.flows import FlowCategory, flowing
from aerona.engine.loops.delay import lagged
from aerona.engine.lore.research_depth import capable_among
from aerona.engine.lore.truth import theory_factor
from aerona.engine.means.containers import packed_capacity
from aerona.engine.means.navigation import instrument_navigation
from aerona.engine.mind.drives import greed_drive
from aerona.engine.nature.effects import sensed
from aerona.engine.nature.senses import NAVIGATION
from aerona.engine.notes import note
from aerona.engine.orders.exchange import billed_between, exchange_cost
from aerona.engine.polity.accords import clause_pairs
from aerona.engine.polity.law_effects import toll_rate
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.prosperity import add_prosperity
from aerona.engine.primitives.records import RecordSpec, create_record, retire_in
from aerona.engine.primitives.stats import headcount, set_stats, stat
from aerona.engine.services.war import declare_war
from aerona.engine.settlement.book import credit

THOUSAND = 1000
LIVE_STATUSES = frozenset({TradeRouteStatus.FORMING, TradeRouteStatus.OPEN, TradeRouteStatus.BLOCKADED})


@dataclass
class Route:
    entity: EntityRow
    profile: TradeRouteProfileRow
    path: list[int]
    tolls: dict[int, TradeRouteTollRow] = field(default_factory=dict)

    @property
    def ends(self) -> tuple[int, int]:
        return self.profile.first_market_id, self.profile.second_market_id


@dataclass
class RouteTally:
    founded: int = 0
    opened: int = 0
    decayed: int = 0
    blockaded: int = 0
    moved: int = 0
    lost: int = 0
    tolls: int = 0
    shipwrecks: int = 0
    wars: int = 0
    noted: int = 0
    credit: int = 0
    polity_tolls: int = 0
    beast_losses: int = 0
    weather_losses: int = 0
    chokepoints: int = 0
    volumes: dict[int, int] = field(default_factory=dict)
    strategic: dict[int, int] = field(default_factory=dict)
    dangers: dict[int, Dangers] = field(default_factory=dict)
    policy: PolicyTally = field(default_factory=PolicyTally)


@dataclass(frozen=True)
class Link:
    first: int
    second: int
    volume: int
    culture: int


async def load_routes(ctx: TickContext, *, live_only: bool = True) -> list[Route]:
    profiles = {row.route_entity_id: row for row in await ctx.session.scalars(select(TradeRouteProfileRow))}
    paths: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for row in await ctx.session.scalars(select(TradeRouteRegionRow)):
        paths[row.route_entity_id].append((row.position, row.region_entity_id))
    tolls: dict[int, dict[int, TradeRouteTollRow]] = defaultdict(dict)
    for toll in await ctx.session.scalars(select(TradeRouteTollRow)):
        tolls[toll.route_entity_id][toll.region_entity_id] = toll
    routes: list[Route] = []
    for route_id, profile in sorted(profiles.items()):
        if live_only and profile.status not in LIVE_STATUSES:
            continue
        entity = await ctx.session.get(EntityRow, route_id)
        if entity is None or (live_only and entity.status is not EntityStatus.CANON):
            continue
        routes.append(Route(entity, profile, [region for _, region in sorted(paths[route_id])], tolls[route_id]))
    return routes


async def trade_links(ctx: TickContext) -> list[Link]:
    volumes: dict[int, int] = defaultdict(int)
    statement = select(TradeFlowRow.route_entity_id, TradeFlowRow.volume).where(TradeFlowRow.epoch >= ctx.epoch - 1)
    for route_id, volume in await ctx.session.execute(statement):
        volumes[route_id] += volume
    links: list[Link] = []
    for route in await load_routes(ctx):
        if route.profile.status is TradeRouteStatus.BLOCKADED:
            continue
        first, second = route.ends
        links.append(Link(first, second, volumes.get(route.entity.id, 0), stat(route.entity, "culture") or 0))
    return links


async def link_partners(ctx: TickContext) -> dict[int, dict[int, float]]:
    partners: dict[int, dict[int, float]] = defaultdict(dict)
    for link in await trade_links(ctx):
        weight = link_weight(ctx, link)
        for here, there in ((link.first, link.second), (link.second, link.first)):
            partners[here][there] = max(partners[here].get(there, 0.0), weight)
    return partners


def link_weight(ctx: TickContext, link: Link) -> float:
    table = ctx.rules.trade_routes
    busy = min(4.0, link.volume / max(1, table.renown_volume))
    return 1 + table.diffusion_pct / PERCENT * busy + link.culture / PERCENT


def region_works(works: dict[int, Works], region_id: int) -> Works:
    return works.get(region_id, Works())


def choose_mode(book: EconomyBook, first: EntityRow, second: EntityRow, path: list[int]) -> TradeMode:
    ends = [book.ground.regions.get(region) for region in (path[0], path[-1])]
    sky = book.knowledge.knows(first.id, KnowledgeBranch.SKY_NAVIGATION) or book.knowledge.knows(second.id, KnowledgeBranch.SKY_NAVIGATION)
    seafaring = book.knowledge.knows(first.id, KnowledgeBranch.SEAFARING) or book.knowledge.knows(second.id, KnowledgeBranch.SEAFARING)
    if sky:
        return TradeMode.SKY
    if seafaring and len(path) > 1 and all(end is not None and end.coast_kind is not CoastKind.NONE for end in ends):
        return TradeMode.SEA
    regions = [book.ground.regions.get(region) for region in path]
    if len(path) > 1 and all(region is not None and region.river_class is not RiverClass.NONE for region in regions):
        return TradeMode.RIVER
    if any(region is not None and region.dominant_terrain in CARAVAN_TERRAIN for region in regions):
        return TradeMode.CARAVAN
    return TradeMode.ROAD


def length_of(ctx: TickContext, mode: TradeMode, path: list[int]) -> int:
    table = ctx.rules.trade_routes
    hops = max(1, len(path) - 1)
    rule_name = TRADE_MODES[mode].length_rule
    if rule_name is None:
        return hops
    return max(1, round_half_up(hops * getattr(table, rule_name) / PERCENT))


def capacity_of(ctx: TickContext, book: EconomyBook, route: Route, works: dict[int, Works]) -> int:
    table = ctx.rules.trade_routes
    capacity = table.capacity_base
    for region in route.path:
        built = region_works(works, region)
        capacity += built.roads * table.capacity_per_road + built.bridges * table.capacity_per_bridge
    first, second = route.ends
    if TRADE_MODES[route.profile.mode].waterborne:
        for end in route.path[:1] + route.path[-1:]:
            capacity += region_works(works, end).harbours * table.capacity_per_harbour
    if TRADE_MODES[route.profile.mode].seagoing:
        for end in (first, second):
            yard = book.workshop(end, WorkshopKind.SHIPYARD)
            capacity += (yard.fleet if yard is not None else 0) * table.capacity_per_ship
        if book.blockaded & {book.affiliated.get(first, first), book.affiliated.get(second, second), first, second}:
            capacity = round_half_up(capacity * ctx.rules.naval.blockade_trade_pct / PERCENT)
    capacity += sum(region_works(works, region).waystations for region in set(route.path[1:-1]))
    return clamp_int(capacity, 0, table.capacity_cap)


async def spoken_capacity(ctx: TickContext, book: EconomyBook, route: Route, works: dict[int, Works]) -> int:
    first, second = route.ends
    capacity = capacity_of(ctx, book, route, works) * await trade_barrier(ctx.session, ctx.rules, first, second, ctx.epoch)
    capacity *= await outsider_barrier(ctx.session, ctx.rules, first, second)
    known = book.techniques.get(first, set()) | book.techniques.get(second, set())
    if Technique.JOINT_STOCK in known:
        capacity *= 1 + ctx.rules.technique_effects.joint_stock_pct / PERCENT
    if TRADE_MODES[route.profile.mode].seagoing:
        table = ctx.rules.technique_effects
        capacity *= max([await theory_factor(ctx.session, ctx.rules, end, TheoryDomain.COSMOLOGY) for end in (first, second)])
        capacity *= (
            1 + (table.navigation_pct * (Technique.NAVIGATION_STARS in known) + table.instruments_pct * (Technique.ASTRONOMY_INSTRUMENTS in known)) / PERCENT
        )
        capacity *= 1 + channel_value(ctx.rules, known, EraChannel.SEA_ROUTES) / PERCENT
    return clamp_int(round_half_up(capacity), 0, ctx.rules.trade_routes.capacity_cap)


def danger_of(book: EconomyBook, path: list[int]) -> int:
    share = book.ground.rules.regional_danger.merchant_route_pct
    dangers = [
        round_half_up(book.merchant_danger[region] * share / PERCENT) if region in book.merchant_danger else stat(book.entities[region], "danger") or 0
        for region in path
        if region in book.entities
    ]
    return round_half_up(sum(dangers) / len(dangers)) if dangers else 0


def route_locked(route: Route, key: str) -> bool:
    return key in (route.profile.locked or [])


def assess(ctx: TickContext, book: EconomyBook, route: Route, lairs: Lairs) -> Dangers:
    profile = route.profile
    found = dangers_of(ctx, book, profile.mode, route.path, lairs, route_id=route.entity.id, world_id=route.entity.world_id)
    for cause, key in DANGER_KEYS.items():
        if route_locked(route, key):
            setattr(found, cause.value, getattr(profile, key))
        else:
            setattr(profile, key, getattr(found, cause.value))
    if not route_locked(route, "danger"):
        set_stats(route.entity, danger=found.total)
    if not route_locked(route, "season_pct"):
        profile.season_pct = season_pct_of(ctx.rules, book, profile.mode, route.path, route.entity.world_id)
    return found


def season_factor(route: Route) -> float:
    return route.profile.season_pct / PERCENT


async def write_path(ctx: TickContext, route_id: int, path: list[int]) -> None:
    for row in await ctx.session.scalars(select(TradeRouteRegionRow).where(TradeRouteRegionRow.route_entity_id == route_id)):
        await ctx.session.delete(row)
    await ctx.session.flush()
    for position, region in enumerate(path):
        ctx.session.add(TradeRouteRegionRow(route_entity_id=route_id, position=position, region_entity_id=region))


async def found_route(ctx: TickContext, book: EconomyBook, first: EntityRow, second: EntityRow, path: list[int], *, works: dict[int, Works]) -> Route:
    mode = choose_mode(book, first, second, path)
    entity = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.TRADE_ROUTE,
            name=f"{TRADE_MODES[mode].words} of {first.name} and {second.name}",
            body=f"Merchants began to carry goods between {first.name} and {second.name} by {mode.value}.",
            stats=TradeRouteStats(capacity=0, danger=danger_of(book, path), renown=0, culture=0),
            power=3,
            location_id=path[0],
            world_id=first.world_id,
            subtype=mode.value,
            pending=False,
        ),
    )
    profile = TradeRouteProfileRow(
        route_entity_id=entity.id,
        first_market_id=first.id,
        second_market_id=second.id,
        mode=mode,
        status=TradeRouteStatus.FORMING,
        length=length_of(ctx, mode, path),
        founded_epoch=ctx.epoch,
        season_pct=season_pct_of(ctx.rules, book, mode, path, first.world_id),
        locked=[],
    )
    ctx.session.add(profile)
    await write_path(ctx, entity.id, path)
    await ctx.session.flush()
    route = Route(entity, profile, path)
    set_stats(entity, capacity=await spoken_capacity(ctx, book, route, works))
    return route


async def controllers(ctx: TickContext, book: EconomyBook, realms: Realms | None = None) -> dict[int, int]:
    found: dict[int, int] = {}
    statement = select(BondRow).where(BondRow.kind == BondKind.RULES, BondRow.state == BondState.ACTIVE).order_by(BondRow.id)
    for bond in await ctx.session.scalars(statement):
        target = book.entities.get(bond.target_node_id)
        if target is not None and target.entity_type is EntityType.REGION and bond.source_node_id in book.entities:
            found.setdefault(target.id, bond.source_node_id)
    for land, polity in (realms.masters(ctx.rules) if realms is not None else {}).items():
        if polity in book.entities:
            found.setdefault(land, polity)
    for community in sorted(book.communities, key=lambda entity: (-headcount(entity), entity.id)):
        region = book.ground.atlas.top_region(community.id)
        if region is not None:
            found.setdefault(region, community.id)
    return found


async def set_tolls(
    ctx: TickContext,
    book: EconomyBook,
    route: Route,
    masters: dict[int, int],
    *,
    realms: Realms | None = None,
    grants: dict[int, int] | None = None,
    waived: set[frozenset[int]] | None = None,
) -> None:
    table = ctx.rules.tolls
    first, second = route.ends
    homes = {first, second} | ({realms.polity_of(first), realms.polity_of(second)} - {None} if realms is not None else set())
    granted = (grants or {}).get(route.entity.id)
    free = waived if waived is not None else await clause_pairs(ctx.session, ClauseKind.TOLLS_WAIVED)
    for region in route.path:
        master = granted if granted is not None else masters.get(region)
        if master is None or master in homes or route_locked(route, f"untolled.{region}") or held(route.entity.id, region, master):
            continue
        if frozenset((master, first)) in free or frozenset((master, second)) in free:
            toll = route.tolls.get(region)
            if toll is not None and not toll.set_by_player:
                toll.controller_entity_id, toll.rate_pct = master, 0
            continue
        greed = await greed_drive(ctx.session, ctx.rules, master)
        decreed = await toll_rate(ctx.session, master)
        rate = clamp_int(decreed if decreed is not None else table.default_rate_pct + max(0.0, greed - 1) * table.greed_rate_pct, 0, PERCENT)
        toll = route.tolls.get(region)
        if toll is None:
            toll = TradeRouteTollRow(route_entity_id=route.entity.id, region_entity_id=region, controller_entity_id=master, rate_pct=rate)
            ctx.session.add(toll)
            route.tolls[region] = toll
            continue
        if not toll.controller_held:
            toll.controller_entity_id = master
        if not toll.set_by_player:
            toll.rate_pct = rate
    if realms is not None:
        for toll in route.tolls.values():
            toll.polity_entity_id = realms.treasury_of(toll.controller_entity_id)
    if route_locked(route, "controller_entity_id"):
        return
    if granted is not None:
        route.profile.controller_entity_id = granted
        return
    route.profile.controller_entity_id = (
        max(route.tolls.values(), key=lambda toll: (toll.rate_pct, -toll.region_entity_id)).controller_entity_id if route.tolls else None
    )


def toll_total(route: Route) -> int:
    return sum(toll.rate_pct for toll in route.tolls.values())


async def enemies_of(ctx: TickContext) -> set[tuple[int, int]]:
    pairs: set[tuple[int, int]] = set()
    statement = select(BondRow.source_node_id, BondRow.target_node_id).where(BondRow.kind == BondKind.ENEMY, BondRow.state == BondState.ACTIVE)
    for first, second in await ctx.session.execute(statement):
        pairs.add((first, second))
        pairs.add((second, first))
    return pairs


async def blocker_of(ctx: TickContext, book: EconomyBook, route: Route, enemies: set[tuple[int, int]]) -> EntityRow | None:
    statement = select(ArmyRow).where(ArmyRow.disbanded_epoch.is_(None)).order_by(ArmyRow.entity_id)
    first, second = route.ends
    halfway = set(route.path)
    for army in await ctx.session.scalars(statement):
        entity = book.entities.get(army.entity_id)
        if entity is None or book.ground.atlas.top_region(entity.id) not in halfway:
            continue
        if (army.owner_entity_id, first) in enemies or (army.owner_entity_id, second) in enemies:
            return entity
    return None


def pay(rules_wealth: int, entity: EntityRow, value: int) -> int:
    gain = round_half_up(value * rules_wealth / THOUSAND)
    current = stat(entity, "wealth")
    if current is not None:
        set_stats(entity, wealth=clamp_int(current + gain, 0, PERCENT))
    return gain


def charge(entity: EntityRow, amount: int) -> None:
    for key in ("wealth", "prosperity"):
        current = stat(entity, key)
        if current is not None:
            set_stats(entity, **{key: clamp_int(current - amount, 0, PERCENT)})
            return


async def _shipwreck(ctx: TickContext, route: Route, seller: EntityRow, tally: RouteTally) -> None:
    crew = ctx.rules.trade_routes.shipwreck_crew
    population = stat(seller, "population")
    if population is not None:
        with flowing(FlowCategory.DISASTER):
            set_stats(seller, population=max(0, population - crew))
    tally.shipwrecks += 1
    await ctx.chronicle(
        ChronicleKind.DISASTER,
        f"A storm broke the ships of {seller.name} on {route.entity.name}; {several(crew, 'sailor', 'sailors')} drowned with their cargo.",
        template_key="trade_route.shipwreck",
        entity_ids=[route.entity.id, seller.id],
    )


async def _record_trade(ctx: TickContext, market_id: int, commodity: CommodityKind, *, imported: int = 0, exported: int = 0) -> None:
    row = await ctx.session.get(MarketPriceRow, (market_id, commodity, ctx.epoch))
    if row is not None:
        row.imported += imported
        row.exported += exported


@dataclass(frozen=True)
class Lane:
    commodity: CommodityKind
    seller_id: int
    buyer_id: int
    landed: float
    volume: int
    desperate: bool = False
    terms: Terms = field(default_factory=Terms)


@dataclass(frozen=True)
class Haul:
    sent: int
    delivered: int
    material: MaterialKind | None


def lane_for(
    ctx: TickContext,
    route: Route,
    quotes: tuple[Quote, Quote],
    room: int,
    season: float,
    *,
    trust: int | None = None,
    policies: PolicyBook | None = None,
    covered: frozenset[int] = frozenset(),
    gaps: Mapping[int, float] | None = None,
    known_goods: GoodBook | None = None,
) -> Lane | None:
    goods = known_goods or GoodBook()
    table = ctx.rules.markets
    flow = ctx.rules.market
    first, second = route.ends
    left, right = quotes
    seller_id, buyer_id, cheap, dear = (first, second, left, right) if left.price <= right.price else (second, first, right, left)
    terms = policies.terms(seller_id, buyer_id, left.commodity) if policies is not None else Terms()
    if terms.blocked:
        return None
    danger = (stat(route.entity, "danger") or 0) * ((PERCENT - ctx.rules.insurance.moral_hazard_pct) / PERCENT if seller_id in covered else 1)
    carriage = (
        1
        + table.transport_cost_pct_per_hop
        * route.profile.length
        / PERCENT
        * carriage_factor(ctx.rules, goods.cargo(left.commodity), route.profile.mode, goods.bulk_scale(left.commodity))
        + table.danger_cost_pct * danger / PERCENT / PERCENT
    )
    landed = (
        cheap.price * carriage * (1 + toll_total(route) / PERCENT) * (1 + (terms.tariff_pct + terms.licence_pct) / PERCENT) * (1 - terms.subsidy_pct / PERCENT)
    )
    if terms.price_cap_pct:
        landed = min(landed, cheap.price * (PERCENT + terms.price_cap_pct) / PERCENT)
    if dear.price * PERCENT < landed * flow.flow_price_gap_pct * (gaps or {}).get(seller_id, 1.0):
        return None
    surplus = max(0, cheap.supply - max(cheap.demand, flow.flow_reserve))
    shortfall = max(0, dear.demand - dear.supply)
    trusted = 1.0 if trust is None else (ctx.rules.money.trust_trade_pct + (PERCENT - ctx.rules.money.trust_trade_pct) * trust / PERCENT) / PERCENT
    reach = terms.access * terms.informed
    volume = round_half_up(min(room, flow.flow_cap, round_half_up(surplus * flow.flow_share_pct / PERCENT * reach), shortfall) * season * trusted)
    if terms.quota_pct:
        volume = round_half_up(volume * terms.quota_pct / PERCENT)
    famine = dear.price * PERCENT >= cheap.price * flow.famine_gap_pct
    return Lane(left.commodity, seller_id, buyer_id, landed, volume, famine, terms) if volume > 0 else None


async def carried_capacity(ctx: TickContext, route: Route, fallback: int) -> int:
    carried = await route_capacity(ctx.session, route.entity.id)
    capacity = await packed_capacity(ctx, route.ends, fallback if carried is None else carried)
    harbour = await harbour_limit(ctx.session, ctx.rules, route.profile)
    return capacity if harbour is None else min(capacity, harbour)


async def kept_by(ctx: TickContext, route: Route) -> PreservationMethod:
    found = await ctx.session.scalar(
        select(ConvoyRow.preservation).where(ConvoyRow.route_entity_id == route.entity.id, ConvoyRow.status.in_(OPEN)).order_by(ConvoyRow.id.desc()).limit(1)
    )
    return found if found is not None else PreservationMethod.NONE


async def haul(ctx: TickContext, route: Route, lane: Lane, *, insured: bool = False) -> Haul:
    ledger = goods_of(ctx.session, ctx.epoch)
    danger = (stat(route.entity, "danger") or 0) * ((PERCENT - ctx.rules.technique_effects.insurance_pct) / PERCENT if insured else 1)
    if TRADE_MODES[route.profile.mode].seagoing:
        danger *= await clock_navigation(ctx.session, ctx.rules, route.ends) * await sea_navigation(ctx.session, ctx.rules, route.ends, ctx.epoch)
        danger *= await instrument_navigation(ctx, route.ends, max(1, len(route.path) - 1))
    danger *= await billed_between(ctx, route.ends)
    taken = await ledger.take(
        lane.seller_id, lane.commodity, lane.volume, GoodsFlow.TRADE, exclude=lane.terms.banned.kinds, exclude_worlds=lane.terms.banned.worlds
    )
    sent = sum(lot.quantity for lot in taken)
    goods = await good_book(ctx.session)
    spoiled = spoilage(ctx.rules, goods.cargo(lane.commodity), route.profile.mode, await kept_by(ctx, route))
    spoiled *= await tech_relief(ctx.session, ctx.rules, lane.seller_id, EraChannel.SPOILAGE)
    keep = sent - min(sent, round_half_up(lane.volume * ctx.rules.trade_routes.danger_loss_pct / PERCENT * danger / PERCENT + sent * spoiled))
    delivered = 0
    for lot in taken:
        part = min(lot.quantity, keep - delivered)
        if part > 0:
            delivered += await ledger.add(
                lane.buyer_id, lane.commodity, part, GoodsFlow.TRADE, material=lot.material, world_material_id=lot.world_material_id, quality=lot.quality
            )
    lost = sent - delivered
    if lost > 0:
        await ledger.record(lane.seller_id, lane.commodity, GoodsFlow.TRADE, lost)
        await ledger.record(lane.seller_id, lane.commodity, GoodsFlow.LOSS, -lost)
    return Haul(sent, delivered, taken[0].material if taken else None)


async def settle(ctx: TickContext, book: EconomyBook, route: Route, lane: Lane, *, delivered: int, tally: RouteTally) -> tuple[int, int]:
    rate = ctx.rules.markets.seller_wealth_per_value
    flow = ctx.rules.market
    value = round_half_up(lane.landed * delivered / PERCENT)
    seller, buyer = book.entities[lane.seller_id], book.entities[lane.buyer_id]
    pay(rate, seller, round_half_up(value * await ctx.hook_factor(seller.id, DomainHook.TRADE_GAIN)))
    add_prosperity(ctx.rules, seller, flow.flow_prosperity)
    purse = stat(buyer, "wealth")
    purse = stat(buyer, "prosperity") if purse is None else purse
    poor = (purse or 0) < flow.credit_threshold
    rng = ctx.rng(f"credit.{route.entity.id}.{lane.commodity.value}.{ctx.epoch}")
    if poor or rng.chance(flow.credit_chance):
        if await sell_on_credit(ctx, buyer, seller, lane.commodity, delivered, noted=tally.noted < flow.note_cap):
            tally.noted += 1
            tally.credit += 1
    else:
        cost = round_half_up(value * rate / THOUSAND)
        charge(buyer, cost + await exchange_cost(ctx, lane.seller_id, lane.buyer_id, cost))
    if lane.desperate and COMMODITIES[lane.commodity].nourishment > 0 and tally.noted < flow.note_cap:
        tally.noted += 1
        await note(
            ctx,
            f"{buyer.name} brought {COMMODITIES[lane.commodity].label.lower()} from {seller.name} in a time of famine.",
            key="market.famine_grain",
            ids=[buyer.id, seller.id, route.entity.id],
            kind=ChronicleKind.TRADE,
        )
    await levy_terms(ctx, lane, value, tally)
    paid = 0
    waived = frozenset({lane.seller_id, lane.buyer_id}) in book.waived
    for toll in () if waived else route.tolls.values():
        master = book.entities.get(toll.controller_entity_id)
        if master is None:
            continue
        fee = round_half_up(value * toll.rate_pct / PERCENT)
        paid += fee
        pay(ctx.rules.tolls.revenue_wealth_per_value, master, fee)
        label = route.entity.name
        if master.entity_type is EntityType.POLITY:
            tally.polity_tolls += await fund_polity(ctx, master.id, fee, label)
            continue
        share = round_half_up(fee * ctx.rules.tolls.polity_share_pct / PERCENT) if toll.polity_entity_id is not None else 0
        if share and toll.polity_entity_id is not None:
            tally.polity_tolls += await fund_polity(ctx, toll.polity_entity_id, share, f"from {master.name}: {label}")
        if master.entity_type is EntityType.SETTLEMENT:
            await credit(ctx, master, TreasuryEntry.TOLLS, fee - share, label)
        else:
            add_prosperity(ctx.rules, master, round_half_up((fee - share) * ctx.rules.tolls.revenue_wealth_per_value / THOUSAND))
    return value, paid


async def levy_terms(ctx: TickContext, lane: Lane, value: int, tally: RouteTally) -> None:
    terms = lane.terms
    if terms.tariff_pct and terms.buyer_realm is not None:
        duty = round_half_up(value * terms.tariff_pct / PERCENT * (await good_book(ctx.session)).tariff_scale(ctx.rules, lane.commodity))
        tally.policy.tariffs += await fund_polity(ctx, terms.buyer_realm, duty, "tariff")
    if terms.licence_pct and terms.buyer_realm is not None:
        fee = round_half_up(value * terms.licence_pct / PERCENT)
        tally.policy.tariffs += await fund_polity(ctx, terms.buyer_realm, fee, "trade licence")
    if terms.subsidy_pct and terms.seller_realm is not None:
        profile = await ctx.session.get(PolityProfileRow, terms.seller_realm)
        grant = min(round_half_up(value * terms.subsidy_pct / PERCENT), profile.treasury if profile is not None else 0)
        if profile is not None and grant > 0:
            profile.treasury -= grant
            tally.policy.subsidies += grant


async def mourn_losses(ctx: TickContext, book: EconomyBook, route: Route, lane: Lane, *, lost: int, tally: RouteTally) -> TradeLoss | None:
    if lost <= 0:
        return None
    lanes = ctx.rules.trade_routes
    dangers = tally.dangers.get(route.entity.id) or Dangers(**{cause.value: getattr(route.profile, key) for cause, key in DANGER_KEYS.items()})
    shares = split(lost, dangers.parts(), route.profile.mode)
    await claim(ctx.session, lane.seller_id, InsuranceCover.CARGO, round_half_up(lane.landed * lost / PERCENT * ctx.rules.insurance.cargo_payout_pct / PERCENT))
    for cause, units in sorted(shares.items(), key=lambda item: item[0].value):
        culprit = dangers.culprit(cause)
        ctx.session.add(
            TradeRouteLossRow(route_entity_id=route.entity.id, epoch=ctx.epoch, commodity=lane.commodity, cause=cause, units=units, culprit_entity_id=culprit)
        )
        calm = await ctx.hook_easing(lane.seller_id, DomainHook.SEA_CALM) * (
            1 - await sensed(ctx.session, ctx.rules, lane.seller_id, NAVIGATION, ctx.rules.senses.navigation_pct)
        )
        if cause is TradeLoss.SEA and ctx.rng(f"wreck.{route.entity.id}.{lane.commodity.value}.{ctx.epoch}").chance(lanes.shipwreck_chance * calm):
            await _shipwreck(ctx, route, book.entities[lane.seller_id], tally)
        elif cause is TradeLoss.BANDITS:
            bandits = book.entities.get(culprit) if culprit is not None else None
            if bandits is not None:
                pay(ctx.rules.markets.seller_wealth_per_value, bandits, round_half_up(lane.landed * units / PERCENT * lanes.bandit_share_pct / PERCENT))
        elif cause is TradeLoss.BEASTS:
            tally.beast_losses += units
            await feed_beast(ctx, book, route.entity, lane.commodity, units=units, beast_id=culprit)
        elif cause is TradeLoss.WEATHER:
            tally.weather_losses += units
            await spoil(ctx, route.entity, lane.commodity, units=units, mode=route.profile.mode)
    return max(shares, key=lambda cause: (shares[cause], cause.value)) if shares else None


async def coin_trust(ctx: TickContext, book: EconomyBook, ends: tuple[int, int]) -> int | None:
    trusts: list[int] = []
    for end in ends:
        row = book.societies.get(end)
        currency = await ctx.session.get(CurrencyRow, row.currency_id) if row is not None and row.currency_id is not None else None
        if currency is not None:
            trusts.append(currency.trust)
    return min(trusts) if trusts else None


async def carry(
    ctx: TickContext,
    book: EconomyBook,
    route: Route,
    quotes: dict[int, dict[CommodityKind, Quote]],
    tally: RouteTally,
    *,
    policies: PolicyBook | None = None,
) -> int:
    first, second = route.ends
    left_quotes, right_quotes = quotes.get(first), quotes.get(second)
    if left_quotes is None or right_quotes is None or route.profile.status is TradeRouteStatus.BLOCKADED:
        return 0
    capacity = await carried_capacity(ctx, route, stat(route.entity, "capacity") or 0)
    if book.closed & set(route.ends):
        capacity = round_half_up(capacity * (PERCENT - ctx.rules.plague_responses.border_trade_pct) / PERCENT)
    factor, fee, toll_realm = await crossing(ctx.session, ctx.rules, route.ends)
    capacity = round_half_up(capacity * factor)
    season = season_factor(route)
    trust = await coin_trust(ctx, book, route.ends)
    covered = await cargo_holders(ctx.session)
    gaps = await price_gaps(ctx.session, ctx.rules, route.ends)
    moved = 0
    for commodity in COMMODITIES:
        pair = (left_quotes[commodity], right_quotes[commodity])
        lane = lane_for(
            ctx, route, pair, capacity - moved, season, trust=trust, policies=policies, covered=covered, gaps=gaps, known_goods=await good_book(ctx.session)
        )
        if policies is not None:
            moved += await run_banned_lots(ctx, book, route, pair, policies, tally=tally)
        if lane is None:
            if policies is not None:
                moved += await run_contraband(ctx, book, route, pair, policies, room=capacity - moved, season=season, tally=tally)
            continue
        insured = Technique.INSURANCE in book.techniques.get(lane.seller_id, set()) | book.techniques.get(lane.buyer_id, set())
        done = await haul(ctx, route, lane, insured=insured)
        if done.sent <= 0:
            continue
        lost = done.sent - done.delivered
        value, paid = await settle(ctx, book, route, lane, delivered=done.delivered, tally=tally)
        loss = await mourn_losses(ctx, book, route, lane, lost=lost, tally=tally)
        ctx.session.add(
            TradeFlowRow(
                route_entity_id=route.entity.id,
                epoch=ctx.epoch,
                commodity=commodity,
                material=done.material,
                from_entity_id=lane.seller_id,
                to_entity_id=lane.buyer_id,
                volume=done.sent,
                lost=lost,
                loss=loss,
                value=value,
                toll_paid=paid,
            )
        )
        await _record_trade(ctx, lane.seller_id, commodity, exported=done.sent)
        await _record_trade(ctx, lane.buyer_id, commodity, imported=done.delivered)
        moved += done.sent
        if COMMODITIES[commodity].strategic:
            tally.strategic[route.entity.id] = tally.strategic.get(route.entity.id, 0) + done.sent
        tally.lost += lost
        tally.tolls += paid
        if moved >= capacity:
            break
    if toll_realm is not None and moved:
        realm = await ctx.session.get(PolityProfileRow, toll_realm)
        if realm is not None and "treasury" not in realm.locked:
            realm.treasury += round_half_up(moved * fee)
    tally.moved += moved
    tally.volumes[route.entity.id] = moved
    return moved


async def run_contraband(
    ctx: TickContext, book: EconomyBook, route: Route, pair: tuple[Quote, Quote], policies: PolicyBook, *, room: int, season: float, tally: RouteTally
) -> int:
    left, right = pair
    seller, buyer = route.ends if left.price <= right.price else (route.ends[1], route.ends[0])
    cheap, dear = (left, right) if left.price <= right.price else (right, left)
    if not policies.terms(seller, buyer, left.commodity).blocked or dear.price * PERCENT < cheap.price * ctx.rules.trade_policy.smuggle_gap_pct:
        return 0
    raw = lane_for(ctx, route, pair, room, season, known_goods=await good_book(ctx.session))
    if raw is None:
        return 0
    return await smuggle(ctx, book, policies, seller=seller, buyer=buyer, commodity=left.commodity, volume=raw.volume, landed=raw.landed, tally=tally.policy)


async def run_banned_lots(ctx: TickContext, book: EconomyBook, route: Route, pair: tuple[Quote, Quote], policies: PolicyBook, *, tally: RouteTally) -> int:
    moved = 0
    for seller, buyer in (route.ends, (route.ends[1], route.ends[0])):
        banned = policies.banned.get(buyer)
        if not banned:
            continue
        for lot in await lots_of(ctx.session, seller, pair[0].commodity):
            forbidden = lot.material in banned.kinds or (lot.world_material_id is not None and lot.world_material_id in banned.worlds)
            if lot.quantity <= 0 or not forbidden:
                continue
            landed = max(pair[0].price, pair[1].price) * 1.0
            moved += await smuggle(
                ctx,
                book,
                policies,
                seller=seller,
                buyer=buyer,
                commodity=lot.commodity,
                volume=lot.quantity,
                landed=landed,
                tally=tally.policy,
                material=lot.material,
                world_material_id=lot.world_material_id,
            )
    return moved


async def _pass_into_legend(ctx: TickContext, route: Route) -> None:
    legend = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.LEGEND,
            name=f"Tales of {route.entity.name}",
            body=f"Travellers tell of {route.entity.name}.",
            stats=LegendStats(spread=stat(route.entity, "renown") or 0),
            power=3,
            location_id=route.path[0] if route.path else None,
            world_id=route.entity.world_id,
            legend_category=LegendCategory.RESOURCE,
        ),
    )
    await BondRepository(ctx.session).connect(BondDraft(legend.id, route.entity.id, BondKind.TELLS_OF, ctx.epoch, "the famous road"))
    await ctx.chronicle(
        ChronicleKind.CULTURE,
        f"{route.entity.name} passed into legend.",
        template_key="trade_route.legend",
        entity_ids=[route.entity.id, legend.id],
    )


async def _route_war(ctx: TickContext, book: EconomyBook, route: Route, rival: EntityRow, tally: RouteTally) -> None:
    lanes = ctx.rules.trade_routes
    for end in route.ends:
        community = book.entities[end]
        row = book.societies.get(end)
        merchants = row.share(SocialClass.MERCHANT) if row is not None else 0.0
        if merchants < ctx.rules.markets.district_merchant_pct or community.id == rival.id:
            continue
        if not ctx.rng(f"route_war.{route.entity.id}.{end}.{ctx.epoch}").chance(lanes.route_war_chance):
            continue
        if await declare_war(ctx, community.id, rival.id, f"the way of {route.entity.name}", cause=WarCause.TRADE_ROUTE):
            tally.wars += 1
            return


async def _blockade(ctx: TickContext, book: EconomyBook, route: Route, blocker: EntityRow, tally: RouteTally) -> None:
    profile = route.profile
    profile.status = TradeRouteStatus.BLOCKADED
    profile.blockaded_by_entity_id = blocker.id
    tally.blockaded += 1
    for end in route.ends:
        row = book.societies.get(end)
        if row is not None:
            row.satisfaction_merchant = clamp_int(row.satisfaction_merchant - ctx.rules.trade_routes.blockade_merchant_loss, 0, PERCENT)
    await ctx.chronicle(
        ChronicleKind.WAR,
        f"{blocker.name} closed {route.entity.name}; no goods pass.",
        template_key="trade_route.blockade",
        entity_ids=[route.entity.id, blocker.id, *route.ends],
    )
    owner = await ctx.session.get(ArmyRow, blocker.id)
    master = book.entities.get(owner.owner_entity_id) if owner is not None else None
    if master is not None:
        await press_route_aims(ctx, master.id, route.entity.id)
        await _route_war(ctx, book, route, master, tally)


async def _grow(ctx: TickContext, route: Route, moved: int) -> None:
    lanes = ctx.rules.trade_routes
    if moved < lanes.renown_volume:
        return
    before = stat(route.entity, "renown") or 0
    renown = before if route_locked(route, "renown") else clamp_int(before + lanes.renown_per_epoch, 0, PERCENT)
    culture = stat(route.entity, "culture") or 0
    set_stats(route.entity, renown=renown, culture=culture if route_locked(route, "culture") else clamp_int(culture + lanes.culture_per_epoch, 0, PERCENT))
    if before < lanes.legend_renown <= renown:
        await _pass_into_legend(ctx, route)


async def _age(ctx: TickContext, book: EconomyBook, route: Route, tally: RouteTally) -> bool:
    lanes = ctx.rules.trade_routes
    profile = route.profile
    if route_locked(route, "status"):
        return True
    if profile.status is TradeRouteStatus.FORMING and profile.traffic_epochs >= lanes.formation_epochs:
        profile.status = TradeRouteStatus.OPEN
        route.entity.pending_name = True
        tally.opened += 1
        await ctx.chronicle(
            ChronicleKind.TRADE,
            f"The way between {book.entities[route.ends[0]].name} and {book.entities[route.ends[1]].name} became a road merchants know by name.",
            template_key="trade_route.formed",
            entity_ids=[route.entity.id, *route.ends],
        )
    last = profile.last_traffic_epoch if profile.last_traffic_epoch is not None else profile.founded_epoch
    if ctx.epoch - last >= lanes.decay_epochs:
        profile.status = TradeRouteStatus.DECAYED
        tally.decayed += 1
        await retire_in(ctx, route.entity, "fell out of use; grass grew over it", status=EntityStatus.DESTROYED)
        return False
    return True


def orphaned(book: EconomyBook, route: Route) -> bool:
    return any(end not in book.entities for end in route.ends)


async def close_orphan(ctx: TickContext, route: Route, tally: RouteTally) -> None:
    if route_locked(route, "status") or route.profile.status is TradeRouteStatus.CLOSED:
        return
    route.profile.status = TradeRouteStatus.CLOSED
    route.profile.blockaded_by_entity_id = None
    tally.decayed += 1
    await ctx.chronicle(
        ChronicleKind.TRADE,
        f"{route.entity.name} lost a market at one end and no trader takes it any more.",
        template_key="trade_route.orphaned",
        entity_ids=[route.entity.id],
    )


async def upkeep(ctx: TickContext, book: EconomyBook, route: Route, *, works: dict[int, Works], enemies: set[tuple[int, int]], tally: RouteTally) -> None:
    profile = route.profile
    if not route_locked(route, "capacity"):
        set_stats(route.entity, capacity=await spoken_capacity(ctx, book, route, works))
    steady = route_locked(route, "blockaded_by_entity_id") or route_locked(route, "status")
    blocker = None if steady else await blocker_of(ctx, book, route, enemies)
    if blocker is not None and profile.status is not TradeRouteStatus.BLOCKADED:
        await _blockade(ctx, book, route, blocker, tally)
        return
    if blocker is None and profile.status is TradeRouteStatus.BLOCKADED and not steady:
        profile.status = TradeRouteStatus.OPEN
        profile.blockaded_by_entity_id = None
    moved = tally.volumes.get(route.entity.id, 0)
    if moved > 0:
        profile.last_traffic_epoch = ctx.epoch
        profile.traffic_epochs += 1
    if not await _age(ctx, book, route, tally):
        return
    await _grow(ctx, route, moved)
    if not route_locked(route, "chokepoint") and weigh_chokepoint(
        ctx, book, profile, route.path, moved=moved, strategic=tally.strategic.get(route.entity.id, 0)
    ):
        tally.chokepoints += 1
    if (
        await lagged(ctx, BalanceLoop.TOLL_DIVERSION, route.entity.id, toll_total(route)) >= ctx.rules.tolls.divert_total_pct
        and not route_locked(route, "path")
        and not await divert(ctx, book, route, works)
        and profile.chokepoint
    ):
        await _chokepoint_war(ctx, book, route, tally)


async def _chokepoint_war(ctx: TickContext, book: EconomyBook, route: Route, tally: RouteTally) -> None:
    master_id = route.profile.controller_entity_id
    master = book.entities.get(master_id) if master_id is not None else None
    if master is None or not ctx.rng(f"chokepoint_war.{route.entity.id}.{ctx.epoch}").chance(ctx.rules.chokepoints.war_chance):
        return
    for end in route.ends:
        row = book.societies.get(end)
        merchants = row.share(SocialClass.MERCHANT) if row is not None else 0.0
        if merchants < ctx.rules.markets.district_merchant_pct or end == master.id:
            continue
        if await declare_war(ctx, end, master.id, f"the chokepoint of {route.entity.name}", cause=WarCause.TRADE_ROUTE):
            tally.wars += 1
            await ctx.chronicle(
                ChronicleKind.WAR,
                f"{book.entities[end].name} took up arms against {master.name} over the chokepoint of {route.entity.name}.",
                template_key="trade_route.chokepoint_war",
                entity_ids=[route.entity.id, end, master.id],
            )
            return


async def divert(ctx: TickContext, book: EconomyBook, route: Route, works: dict[int, Works]) -> bool:
    greedy = frozenset(region for region, toll in route.tolls.items() if toll.rate_pct > ctx.rules.tolls.default_rate_pct)
    if not greedy or not route.path:
        return False
    other = book.ground.atlas.region_path(route.path[0], route.path[-1], greedy)
    if other is None or other == route.path:
        return False
    route.path = other
    await write_path(ctx, route.entity.id, other)
    for region in list(route.tolls):
        if region not in other:
            await ctx.session.delete(route.tolls.pop(region))
    route.profile.length = length_of(ctx, route.profile.mode, other)
    set_stats(route.entity, capacity=await spoken_capacity(ctx, book, route, works))
    await note(
        ctx,
        f"Merchants turned off {route.entity.name} to dodge the tolls and found another way.",
        key="tolls.diverted",
        ids=[route.entity.id],
        kind=ChronicleKind.TRADE,
    )
    return True


async def contacts(
    ctx: TickContext, book: EconomyBook, markets: list[EntityRow], routes: list[Route], quotes: dict[int, dict[CommodityKind, Quote]]
) -> list[tuple[EntityRow, EntityRow, list[int]]]:
    lanes = ctx.rules.trade_routes
    joined = {frozenset(route.ends) for route in routes} | await closed_pairs(ctx)
    meeting: dict[int, int] = defaultdict(int)
    for route in routes:
        for end in route.ends:
            meeting[end] += 1
    statement = select(BondRow.source_node_id, BondRow.target_node_id).where(BondRow.kind == BondKind.TRADES_WITH, BondRow.state == BondState.ACTIVE)
    trading = {frozenset((first, second)) for first, second in await ctx.session.execute(statement)}
    candidates: list[tuple[int, int, int, EntityRow, EntityRow, list[int]]] = []
    navigators = await capable_among(ctx.session, [market.id for market in markets], Capability.BLUE_WATER_NAVIGATION)
    for index, first in enumerate(markets):
        for second in markets[index + 1 :]:
            pair = frozenset((first.id, second.id))
            if pair in joined or first.world_id != second.world_id:
                continue
            start, goal = book.ground.atlas.top_region(first.id), book.ground.atlas.top_region(second.id)
            hops = book.ground.atlas.region_hops(start, goal)
            if hops is None or (pair not in trading and hops > contact_reach(ctx, book, navigators, (first.id, start), (second.id, goal))):
                continue
            path = book.ground.atlas.region_path(start, goal)
            if path is None or not _worth_carrying(ctx, quotes.get(first.id), quotes.get(second.id)):
                continue
            candidates.append((0 if pair in trading else 1, hops, first.id, first, second, path))
    found: list[tuple[EntityRow, EntityRow, list[int]]] = []
    for _, _, _, first, second, path in sorted(candidates, key=lambda item: item[:3]):
        if len(found) >= lanes.found_cap:
            break
        if meeting[first.id] >= lanes.market_route_cap or meeting[second.id] >= lanes.market_route_cap:
            continue
        meeting[first.id] += 1
        meeting[second.id] += 1
        found.append((first, second, path))
    return found


def contact_reach(ctx: TickContext, book: EconomyBook, navigators: set[int], *ends: tuple[int, int | None]) -> int:
    reach = ctx.rules.trade_routes.contact_hops
    coastal = all(region is not None and (land := book.ground.regions.get(region)) is not None and land.coast_kind is not CoastKind.NONE for _, region in ends)
    if coastal and any(market in navigators for market, _ in ends):
        return reach + ctx.rules.research_depth.capability_reach
    return reach


async def closed_pairs(ctx: TickContext) -> set[frozenset[int]]:
    statement = select(TradeRouteProfileRow.first_market_id, TradeRouteProfileRow.second_market_id).where(
        or_(TradeRouteProfileRow.closed_by_player.is_(True), TradeRouteProfileRow.closed_by_son_id.is_not(None))
    )
    return {frozenset((first, second)) for first, second in await ctx.session.execute(statement)}


def _worth_carrying(ctx: TickContext, left: dict[CommodityKind, Quote] | None, right: dict[CommodityKind, Quote] | None) -> bool:
    if left is None or right is None:
        return False
    gap = ctx.rules.market.flow_price_gap_pct
    for commodity, quote in left.items():
        other = right[commodity]
        cheap, dear = (quote, other) if quote.price <= other.price else (other, quote)
        if dear.price * PERCENT >= cheap.price * gap and cheap.supply > cheap.demand and dear.supply < dear.demand:
            return True
    return False


async def blockade_pressure(ctx: TickContext, first_id: int, second_id: int) -> int:
    statement = select(TradeRouteProfileRow).where(
        TradeRouteProfileRow.status == TradeRouteStatus.BLOCKADED,
        (TradeRouteProfileRow.first_market_id.in_([first_id, second_id])) | (TradeRouteProfileRow.second_market_id.in_([first_id, second_id])),
    )
    blocked = len(list(await ctx.session.scalars(statement)))
    return blocked * ctx.rules.trade_routes.blockade_peace_push
