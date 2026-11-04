from collections import defaultdict
from dataclasses import dataclass, field

from sqlalchemy import select

from aerona.catalog.commodities import COMMODITIES
from aerona.constants.units import PERCENT
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.economy import CurrencyRow, MarketPriceRow, TradeFlowRow, TradeRouteProfileRow, TradeRouteRegionRow, TradeRouteTollRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.warfare import ArmyRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.culture import LanguageRegister, Technique
from aerona.domain.enums.economy import CommodityKind, GoodsFlow, TradeLoss, TradeMode, TradeRouteStatus, WorkshopKind
from aerona.domain.enums.entity import EngineKind, EntityStatus, EntityType, LegendCategory
from aerona.domain.enums.environment import CoastKind, RiverClass, TerrainKind
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.settlement import TreasuryEntry
from aerona.domain.enums.society import KnowledgeBranch, SocialClass
from aerona.domain.enums.war import WarCause
from aerona.domain.models.entity_stats import LegendStats, TradeRouteStats
from aerona.engine.context import TickContext
from aerona.engine.economy.book import EconomyBook
from aerona.engine.economy.credit import sell_on_credit
from aerona.engine.economy.markets import Quote
from aerona.engine.economy.stocks import goods_of
from aerona.engine.environment.profile import Works
from aerona.engine.interconnect.flows import FlowCategory, flowing
from aerona.engine.lore.language import register_barrier
from aerona.engine.mind.drives import greed_drive
from aerona.engine.notes import note
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.prosperity import add_prosperity
from aerona.engine.primitives.records import RecordSpec, create_record, retire_in
from aerona.engine.primitives.stats import headcount, set_stats, stat
from aerona.engine.services.war import declare_war
from aerona.engine.settlement.book import credit

THOUSAND = 1000
LIVE_STATUSES = frozenset({TradeRouteStatus.FORMING, TradeRouteStatus.OPEN, TradeRouteStatus.BLOCKADED})
CARAVAN_TERRAIN = frozenset({TerrainKind.DESERT, TerrainKind.STEPPE})
BANDIT_KINDS = frozenset({EngineKind.REBELS, EngineKind.VOID_PIRATES})
MODE_WORDS: dict[TradeMode, str] = {
    TradeMode.ROAD: "Road",
    TradeMode.RIVER: "River Way",
    TradeMode.SEA: "Sea Lane",
    TradeMode.CARAVAN: "Caravan Way",
    TradeMode.SKY: "Sky Lane",
}


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
    volumes: dict[int, int] = field(default_factory=dict)


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
    if mode is TradeMode.SEA:
        return max(1, round_half_up(hops * table.sea_length_pct / PERCENT))
    if mode is TradeMode.RIVER:
        return max(1, round_half_up(hops * table.river_length_pct / PERCENT))
    return hops


def capacity_of(ctx: TickContext, book: EconomyBook, route: Route, works: dict[int, Works]) -> int:
    table = ctx.rules.trade_routes
    capacity = table.capacity_base
    for region in route.path:
        built = region_works(works, region)
        capacity += built.roads * table.capacity_per_road + built.bridges * table.capacity_per_bridge
    first, second = route.ends
    if route.profile.mode in (TradeMode.SEA, TradeMode.RIVER):
        for end in route.path[:1] + route.path[-1:]:
            capacity += region_works(works, end).harbours * table.capacity_per_harbour
    if route.profile.mode is TradeMode.SEA:
        for end in (first, second):
            yard = book.workshop(end, WorkshopKind.SHIPYARD)
            capacity += (yard.fleet if yard is not None else 0) * table.capacity_per_ship
        if book.blockaded & {book.affiliated.get(first, first), book.affiliated.get(second, second), first, second}:
            capacity = round_half_up(capacity * ctx.rules.naval.blockade_trade_pct / PERCENT)
    halfway = set(route.path[1:-1])
    capacity += sum(
        table.capacity_per_market
        for community in book.communities
        if book.workshop(community.id, WorkshopKind.MARKET) and book.ground.atlas.top_region(community.id) in halfway
    )
    return clamp_int(capacity, 0, table.capacity_cap)


async def spoken_capacity(ctx: TickContext, book: EconomyBook, route: Route, works: dict[int, Works]) -> int:
    first, second = route.ends
    capacity = capacity_of(ctx, book, route, works) * await register_barrier(
        ctx.session, ctx.rules, first, second, ctx.epoch, ours=LanguageRegister.TRADE, theirs=LanguageRegister.TRADE
    )
    if route.profile.mode is TradeMode.SEA:
        table = ctx.rules.technique_effects
        held = book.techniques.get(first, set()) | book.techniques.get(second, set())
        capacity *= (
            1 + (table.navigation_pct * (Technique.NAVIGATION_STARS in held) + table.instruments_pct * (Technique.ASTRONOMY_INSTRUMENTS in held)) / PERCENT
        )
    return clamp_int(round_half_up(capacity), 0, ctx.rules.trade_routes.capacity_cap)


def danger_of(book: EconomyBook, path: list[int]) -> int:
    share = book.ground.rules.regional_danger.merchant_route_pct
    dangers = [
        round_half_up(book.merchant_danger[region] * share / PERCENT) if region in book.merchant_danger else stat(book.entities[region], "danger") or 0
        for region in path
        if region in book.entities
    ]
    return round_half_up(sum(dangers) / len(dangers)) if dangers else 0


def season_factor(ctx: TickContext, book: EconomyBook, route: Route) -> float:
    if route.profile.mode is not TradeMode.SEA or route.entity.world_id is None:
        return 1.0
    seasons = book.ground.seasons_of(route.entity.world_id)
    if not seasons:
        return 1.0
    worst = min(season.travel for season in seasons)
    return 1 - ctx.rules.trade_routes.sea_season_pct / PERCENT * (PERCENT - worst) / PERCENT


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
            name=f"{MODE_WORDS[mode]} of {first.name} and {second.name}",
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
    )
    ctx.session.add(profile)
    await write_path(ctx, entity.id, path)
    await ctx.session.flush()
    route = Route(entity, profile, path)
    set_stats(entity, capacity=await spoken_capacity(ctx, book, route, works))
    return route


async def controllers(ctx: TickContext, book: EconomyBook) -> dict[int, int]:
    found: dict[int, int] = {}
    statement = select(BondRow).where(BondRow.kind == BondKind.RULES, BondRow.state == BondState.ACTIVE).order_by(BondRow.id)
    for bond in await ctx.session.scalars(statement):
        target = book.entities.get(bond.target_node_id)
        if target is not None and target.entity_type is EntityType.REGION and bond.source_node_id in book.entities:
            found.setdefault(target.id, bond.source_node_id)
    for community in sorted(book.communities, key=lambda entity: (-headcount(entity), entity.id)):
        region = book.ground.atlas.top_region(community.id)
        if region is not None:
            found.setdefault(region, community.id)
    return found


async def set_tolls(ctx: TickContext, book: EconomyBook, route: Route, masters: dict[int, int]) -> None:
    table = ctx.rules.tolls
    first, second = route.ends
    for region in route.path:
        master = masters.get(region)
        if master is None or master in (first, second):
            continue
        greed = await greed_drive(ctx.session, ctx.rules, master)
        rate = clamp_int(table.default_rate_pct + max(0.0, greed - 1) * table.greed_rate_pct, 0, PERCENT)
        toll = route.tolls.get(region)
        if toll is None:
            toll = TradeRouteTollRow(route_entity_id=route.entity.id, region_entity_id=region, controller_entity_id=master, rate_pct=rate)
            ctx.session.add(toll)
            route.tolls[region] = toll
        elif not toll.set_by_player:
            toll.controller_entity_id, toll.rate_pct = master, rate
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


def bandits_on(book: EconomyBook, route: Route) -> EntityRow | None:
    halfway = set(route.path)
    found = [
        entity
        for entity in book.entities.values()
        if entity.entity_type is EntityType.FACTION and entity.engine_kind in BANDIT_KINDS and book.ground.atlas.top_region(entity.id) in halfway
    ]
    return min(found, key=lambda entity: entity.id) if found else None


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
        f"A storm broke the ships of {seller.name} on {route.entity.name}; {crew} sailors drowned with their cargo.",
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


@dataclass(frozen=True)
class Haul:
    sent: int
    delivered: int
    material: MaterialKind | None


def lane_for(ctx: TickContext, route: Route, quotes: tuple[Quote, Quote], room: int, season: float, *, trust: int | None = None) -> Lane | None:
    table = ctx.rules.markets
    flow = ctx.rules.market
    first, second = route.ends
    left, right = quotes
    seller_id, buyer_id, cheap, dear = (first, second, left, right) if left.price <= right.price else (second, first, right, left)
    danger = stat(route.entity, "danger") or 0
    carriage = 1 + table.transport_cost_pct_per_hop * route.profile.length / PERCENT + table.danger_cost_pct * danger / PERCENT / PERCENT
    landed = cheap.price * carriage * (1 + toll_total(route) / PERCENT)
    if dear.price * PERCENT < landed * flow.flow_price_gap_pct:
        return None
    surplus = max(0, cheap.supply - max(cheap.demand, flow.flow_reserve))
    shortfall = max(0, dear.demand - dear.supply)
    trusted = 1.0 if trust is None else (ctx.rules.money.trust_trade_pct + (PERCENT - ctx.rules.money.trust_trade_pct) * trust / PERCENT) / PERCENT
    volume = round_half_up(min(room, flow.flow_cap, round_half_up(surplus * flow.flow_share_pct / PERCENT), shortfall) * season * trusted)
    return Lane(left.commodity, seller_id, buyer_id, landed, volume, dear.price * PERCENT >= cheap.price * flow.famine_gap_pct) if volume > 0 else None


async def haul(ctx: TickContext, route: Route, lane: Lane) -> Haul:
    ledger = goods_of(ctx.session, ctx.epoch)
    danger = stat(route.entity, "danger") or 0
    taken = await ledger.take(lane.seller_id, lane.commodity, lane.volume, GoodsFlow.TRADE)
    sent = sum(lot.quantity for lot in taken)
    keep = sent - min(sent, round_half_up(lane.volume * ctx.rules.trade_routes.danger_loss_pct / PERCENT * danger / PERCENT))
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
    pay(rate, seller, value)
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
        charge(buyer, round_half_up(value * rate / THOUSAND))
    if lane.desperate and COMMODITIES[lane.commodity].nourishment > 0 and tally.noted < flow.note_cap:
        tally.noted += 1
        await note(
            ctx,
            f"{buyer.name} brought {COMMODITIES[lane.commodity].label.lower()} from {seller.name} in a time of famine.",
            key="market.famine_grain",
            ids=[buyer.id, seller.id, route.entity.id],
            kind=ChronicleKind.TRADE,
        )
    paid = 0
    waived = frozenset({lane.seller_id, lane.buyer_id}) in book.waived
    for toll in () if waived else route.tolls.values():
        master = book.entities.get(toll.controller_entity_id)
        if master is None:
            continue
        fee = round_half_up(value * toll.rate_pct / PERCENT)
        paid += fee
        pay(ctx.rules.tolls.revenue_wealth_per_value, master, fee)
        if master.entity_type is EntityType.SETTLEMENT:
            await credit(ctx, master, TreasuryEntry.TOLLS, fee, route.entity.name[:120])
        else:
            add_prosperity(ctx.rules, master, round_half_up(fee * ctx.rules.tolls.revenue_wealth_per_value / THOUSAND))
    return value, paid


async def mourn_losses(ctx: TickContext, book: EconomyBook, route: Route, lane: Lane, *, lost: int, tally: RouteTally) -> TradeLoss | None:
    if lost <= 0:
        return None
    lanes = ctx.rules.trade_routes
    if route.profile.mode is TradeMode.SEA:
        if ctx.rng(f"wreck.{route.entity.id}.{lane.commodity.value}.{ctx.epoch}").chance(lanes.shipwreck_chance):
            await _shipwreck(ctx, route, book.entities[lane.seller_id], tally)
        return TradeLoss.SEA
    bandits = bandits_on(book, route)
    if bandits is not None:
        pay(ctx.rules.markets.seller_wealth_per_value, bandits, round_half_up(lane.landed * lost / PERCENT * lanes.bandit_share_pct / PERCENT))
    return TradeLoss.BANDITS


async def coin_trust(ctx: TickContext, book: EconomyBook, ends: tuple[int, int]) -> int | None:
    trusts: list[int] = []
    for end in ends:
        row = book.societies.get(end)
        currency = await ctx.session.get(CurrencyRow, row.currency_id) if row is not None and row.currency_id is not None else None
        if currency is not None:
            trusts.append(currency.trust)
    return min(trusts) if trusts else None


async def carry(ctx: TickContext, book: EconomyBook, route: Route, quotes: dict[int, dict[CommodityKind, Quote]], tally: RouteTally) -> int:
    first, second = route.ends
    left_quotes, right_quotes = quotes.get(first), quotes.get(second)
    if left_quotes is None or right_quotes is None or route.profile.status is TradeRouteStatus.BLOCKADED:
        return 0
    capacity = stat(route.entity, "capacity") or 0
    season = season_factor(ctx, book, route)
    trust = await coin_trust(ctx, book, route.ends)
    moved = 0
    for commodity in COMMODITIES:
        lane = lane_for(ctx, route, (left_quotes[commodity], right_quotes[commodity]), capacity - moved, season, trust=trust)
        if lane is None:
            continue
        done = await haul(ctx, route, lane)
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
        tally.lost += lost
        tally.tolls += paid
        if moved >= capacity:
            break
    tally.moved += moved
    tally.volumes[route.entity.id] = moved
    return moved


async def _pass_into_legend(ctx: TickContext, route: Route) -> None:
    legend = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.LEGEND,
            name=f"Tales of {route.entity.name}",
            body=f"Travellers tell of {route.entity.name}, the way every caravan takes.",
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
        f"{route.entity.name} passed into legend: songs follow its caravans.",
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


async def upkeep(ctx: TickContext, book: EconomyBook, route: Route, *, works: dict[int, Works], enemies: set[tuple[int, int]], tally: RouteTally) -> None:
    lanes = ctx.rules.trade_routes
    profile = route.profile
    set_stats(route.entity, capacity=await spoken_capacity(ctx, book, route, works), danger=danger_of(book, route.path))
    blocker = await blocker_of(ctx, book, route, enemies)
    if blocker is not None and profile.status is not TradeRouteStatus.BLOCKADED:
        profile.status = TradeRouteStatus.BLOCKADED
        profile.blockaded_by_entity_id = blocker.id
        tally.blockaded += 1
        for end in route.ends:
            row = book.societies.get(end)
            if row is not None:
                row.satisfaction_merchant = clamp_int(row.satisfaction_merchant - lanes.blockade_merchant_loss, 0, PERCENT)
        await ctx.chronicle(
            ChronicleKind.WAR,
            f"{blocker.name} closed {route.entity.name}; no caravan passes.",
            template_key="trade_route.blockade",
            entity_ids=[route.entity.id, blocker.id, *route.ends],
        )
        owner = await ctx.session.get(ArmyRow, blocker.id)
        master = book.entities.get(owner.owner_entity_id) if owner is not None else None
        if master is not None:
            await _route_war(ctx, book, route, master, tally)
        return
    if blocker is None and profile.status is TradeRouteStatus.BLOCKADED:
        profile.status = TradeRouteStatus.OPEN
        profile.blockaded_by_entity_id = None
    moved = tally.volumes.get(route.entity.id, 0)
    if moved > 0:
        profile.last_traffic_epoch = ctx.epoch
        profile.traffic_epochs += 1
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
        return
    if moved >= lanes.renown_volume:
        renown = clamp_int((stat(route.entity, "renown") or 0) + lanes.renown_per_epoch, 0, PERCENT)
        before = stat(route.entity, "renown") or 0
        set_stats(route.entity, renown=renown, culture=clamp_int((stat(route.entity, "culture") or 0) + lanes.culture_per_epoch, 0, PERCENT))
        if before < lanes.legend_renown <= renown:
            await _pass_into_legend(ctx, route)
    if toll_total(route) >= ctx.rules.tolls.divert_total_pct:
        await divert(ctx, book, route, works)


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
    joined = {frozenset(route.ends) for route in routes}
    meeting: dict[int, int] = defaultdict(int)
    for route in routes:
        for end in route.ends:
            meeting[end] += 1
    statement = select(BondRow.source_node_id, BondRow.target_node_id).where(BondRow.kind == BondKind.TRADES_WITH, BondRow.state == BondState.ACTIVE)
    trading = {frozenset((first, second)) for first, second in await ctx.session.execute(statement)}
    candidates: list[tuple[int, int, int, EntityRow, EntityRow, list[int]]] = []
    for index, first in enumerate(markets):
        for second in markets[index + 1 :]:
            pair = frozenset((first.id, second.id))
            if pair in joined or first.world_id != second.world_id:
                continue
            start, goal = book.ground.atlas.top_region(first.id), book.ground.atlas.top_region(second.id)
            hops = book.ground.atlas.region_hops(start, goal)
            if hops is None or (pair not in trading and hops > lanes.contact_hops):
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
