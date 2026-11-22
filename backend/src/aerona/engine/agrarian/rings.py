import heapq
from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.life.agrarian import RING_ORDER
from aerona.catalog.market_ranks import RANKS, by_order, higher_markets, widest_reach
from aerona.constants.units import PERCENT
from aerona.db.tables.agrarian import CentralPlaceRow, LandRingRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.settlement import SettlementInfrastructureRow, SettlementProfileRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.agrarian import CentralityRank, LandUseRing
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.environment import RiverClass
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.settlement import SizeTier
from aerona.domain.enums.structure import StructureKind
from aerona.engine.context import TickContext
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.stats import stat_or
from aerona.engine.recording.record import record

MARKET_TIERS = frozenset({SizeTier.TOWN, SizeTier.CITY, SizeTier.METROPOLIS, SizeTier.MEGALOPOLIS, SizeTier.WORLD_CITY})
UNREACHED = 99_999


@dataclass
class SpatialTally:
    ranked: int = 0
    markets: int = 0
    rings: int = 0
    moved: int = 0
    gaps: int = 0


@dataclass
class Place:
    town: EntityRow
    region: int
    people: int
    tier: SizeTier


class Reach:
    def __init__(self, atlas: RegionAtlas) -> None:
        self.atlas = atlas
        self.cache: dict[tuple[int, int], dict[int, int]] = {}

    def within(self, region: int, hops: int) -> dict[int, int]:
        key = (region, hops)
        if key in self.cache:
            return self.cache[key]
        found = {region: 0}
        frontier = [region]
        for depth in range(1, hops + 1):
            following: list[int] = []
            for current in frontier:
                for other in self.atlas.neighbour_regions(current):
                    if other not in found and not self.atlas.is_water(other):
                        found[other] = depth
                        following.append(other)
            frontier = following
        self.cache[key] = found
        return found


def put(row: object, field: str, value: object) -> None:
    if field not in (getattr(row, "locked", None) or []):
        setattr(row, field, value)


async def places_by_world(ctx: TickContext, atlas: RegionAtlas) -> dict[int, list[Place]]:
    rows = await ctx.session.execute(
        select(EntityRow, SettlementProfileRow)
        .join(SettlementProfileRow, SettlementProfileRow.settlement_entity_id == EntityRow.id)
        .where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    found: dict[int, list[Place]] = defaultdict(list)
    for town, profile in rows.all():
        region = atlas.top_region(town.id)
        if region is not None and town.world_id is not None:
            found[town.world_id].append(Place(town, region, stat_or(town, "population", 0), profile.size_tier))
    return found


def catchment(reach: Reach, people_in: dict[int, int], region: int, hops: int) -> int:
    return sum(people_in.get(other, 0) for other in reach.within(region, hops))


def rank_for(ctx: TickContext, reach: Reach, people_in: dict[int, int], place: Place, chosen: dict[int, CentralityRank]) -> CentralityRank:
    ranks = by_order(descending=True)
    for rank in ranks[:-1]:
        spec = RANKS[rank]
        hops = spec.reach(ctx.rules)
        rivals = {region for region, other in chosen.items() if RANKS[other].order >= spec.order}
        if catchment(reach, people_in, place.region, hops) >= spec.threshold(ctx.rules) and not rivals & set(reach.within(place.region, hops)):
            return rank
    return ranks[-1]


def centrality(ctx: TickContext, rank: CentralityRank, buyers: int) -> int:
    spec = RANKS[rank]
    goal = spec.goal(ctx.rules)
    return clamp_int(spec.centrality(ctx.rules) + ctx.rules.central_places.catchment_centrality * min(1.0, buyers / max(1, goal)), 0, PERCENT)


def range_of(ctx: TickContext, rank: CentralityRank) -> int:
    return RANKS[rank].reach(ctx.rules)


def server_of(ctx: TickContext, reach: Reach, place: Place, rank: CentralityRank, ranked: list[tuple[Place, CentralityRank]]) -> int | None:
    higher = higher_markets(rank)
    near = reach.within(place.region, widest_reach(ctx.rules))
    options = [(near[other.region], other.town.id) for other, other_rank in ranked if other_rank in higher and other.region in near and other is not place]
    return min(options)[1] if options else None


async def rank_world(ctx: TickContext, reach: Reach, places: list[Place], tally: SpatialTally) -> set[int]:
    people_in: dict[int, int] = defaultdict(int)
    for place in places:
        people_in[place.region] += place.people
    rows = {
        row.settlement_entity_id: row
        for row in await ctx.session.scalars(select(CentralPlaceRow).where(CentralPlaceRow.settlement_entity_id.in_([place.town.id for place in places])))
    }
    chosen: dict[int, CentralityRank] = {}
    ranked: list[tuple[Place, CentralityRank]] = []
    for place in sorted(places, key=lambda item: (-item.people, item.town.id)):
        row = rows.get(place.town.id)
        rank = row.rank if row is not None and ("rank" in row.locked or held(place.town.id)) else rank_for(ctx, reach, people_in, place, chosen)
        if RANKS[rank].market:
            chosen.setdefault(place.region, rank)
        ranked.append((place, rank))
    for place, rank in ranked:
        if held(place.town.id):
            continue
        row = rows.get(place.town.id)
        if row is None:
            row = CentralPlaceRow(settlement_entity_id=place.town.id, locked=[])
            ctx.session.add(row)
        buyers = catchment(reach, people_in, place.region, range_of(ctx, rank))
        put(row, "rank", rank)
        put(row, "catchment", buyers)
        put(row, "served_by_entity_id", server_of(ctx, reach, place, rank, ranked))
        put(row, "centrality", centrality(ctx, row.rank, buyers))
        row.updated_epoch = ctx.epoch
        tally.ranked += 1
    markets = {place.region for place, rank in ranked if RANKS[rank].market}
    if not markets:
        markets = {place.region for place in places if place.tier in MARKET_TIERS}
    tally.markets += len(markets)
    return markets


async def eased_regions(ctx: TickContext, atlas: RegionAtlas) -> tuple[set[int], set[int]]:
    roads: set[int] = set()
    canals: set[int] = set()
    for settlement_id, level in await ctx.session.execute(select(SettlementInfrastructureRow.settlement_entity_id, SettlementInfrastructureRow.roads)):
        region = atlas.top_region(settlement_id)
        if region is not None and level >= 1:
            roads.add(region)
    works = await ctx.session.execute(
        select(StructureProfileRow.structure_entity_id, StructureProfileRow.kind)
        .join(EntityRow, EntityRow.id == StructureProfileRow.structure_entity_id)
        .where(StructureProfileRow.kind.in_([StructureKind.ROAD, StructureKind.CANAL]), EntityRow.status == EntityStatus.CANON)
    )
    for structure_id, kind in works.all():
        region = atlas.top_region(structure_id)
        if region is not None:
            (canals if kind is StructureKind.CANAL else roads).add(region)
    return roads, canals


@dataclass(frozen=True)
class Ways:
    lands: dict[int, RegionEnvironmentRow]
    roads: set[int]
    canals: set[int]


def hop_cost(ctx: TickContext, ways: Ways, first: int, second: int) -> tuple[int, bool]:
    table = ctx.rules.thunen
    cost = table.hop_cost * PERCENT
    river = False
    one, two = ways.lands.get(first), ways.lands.get(second)
    if one is not None and two is not None and one.river_class is not RiverClass.NONE and two.river_class is not RiverClass.NONE:
        cost = cost * table.river_cost_pct // PERCENT
        river = True
    if second in ways.canals:
        cost = cost * table.canal_cost_pct // PERCENT
    elif second in ways.roads:
        cost = cost * table.road_cost_pct // PERCENT
    return max(1, cost // PERCENT), river


def carry(ctx: TickContext, atlas: RegionAtlas, ways: Ways, markets: set[int], market_town: dict[int, int]) -> dict[int, tuple[int, bool, int]]:
    best: dict[int, tuple[int, bool, int]] = {}
    queue: list[tuple[int, int, bool, int]] = [(0, region, False, market_town[region]) for region in sorted(markets)]
    heapq.heapify(queue)
    while queue:
        cost, region, by_water, town = heapq.heappop(queue)
        if region in best:
            continue
        best[region] = (cost, by_water, town)
        if cost > ctx.rules.thunen.ranching_reach + ctx.rules.central_places.gap_from + ctx.rules.central_places.gap_span:
            continue
        for other in atlas.neighbour_regions(region):
            if other in best or atlas.is_water(other):
                continue
            step, river = hop_cost(ctx, ways, region, other)
            heapq.heappush(queue, (cost + step, other, by_water or river, town))
    return best


def ring_at(ctx: TickContext, cost: int | None) -> LandUseRing:
    table = ctx.rules.thunen
    if cost is None:
        return LandUseRing.WILDS
    if cost == 0:
        return LandUseRing.GARDENS
    for ring, reach in ((LandUseRing.FORESTRY, table.forestry_reach), (LandUseRing.GRAIN, table.grain_reach), (LandUseRing.RANCHING, table.ranching_reach)):
        if cost <= reach:
            return ring
    return LandUseRing.WILDS


def gap_at(ctx: TickContext, cost: int | None, any_market: bool) -> int:
    table = ctx.rules.central_places
    if not any_market:
        return 0
    if cost is None:
        return PERCENT
    return clamp_int((cost - table.gap_from) * PERCENT / table.gap_span, 0, PERCENT)


async def draw_rings(ctx: TickContext, atlas: RegionAtlas, ways: Ways, *, world: int, markets: dict[int, int], tally: SpatialTally) -> None:
    carried = carry(ctx, atlas, ways, set(markets), markets)
    rows = {row.region_entity_id: row for row in await ctx.session.scalars(select(LandRingRow).where(LandRingRow.region_entity_id.in_(list(ways.lands))))}
    for region_id, land in sorted(ways.lands.items()):
        if land.world_id != world or atlas.is_water(region_id) or held(region_id):
            continue
        reached = carried.get(region_id)
        cost = reached[0] if reached is not None else None
        row = rows.get(region_id)
        before = row.ring if row is not None else None
        if row is None:
            row = LandRingRow(region_entity_id=region_id, locked=[])
            ctx.session.add(row)
        put(row, "market_entity_id", reached[2] if reached is not None else None)
        put(row, "distance", min(UNREACHED, cost) if cost is not None else 0)
        put(row, "by_water", bool(reached and reached[1]))
        put(row, "ring", ring_at(ctx, cost))
        put(row, "gap", gap_at(ctx, cost, bool(markets)))
        row.updated_epoch = ctx.epoch
        tally.rings += 1
        if row.gap >= PERCENT // 2:
            tally.gaps += 1
        if before is not None and before is not row.ring and RING_ORDER.index(row.ring) < RING_ORDER.index(before) and row.market_entity_id is not None:
            tally.moved += 1
            await record(
                ctx,
                "thunen.ring_moved",
                roles={IncidentRole.SUBJECT: region_id},
                facts={"market": row.market_entity_id, "before": before, "after": row.ring, "distance": row.distance},
                place=region_id,
            )


async def keep_spatial(ctx: TickContext, tally: SpatialTally) -> None:
    atlas = await RegionAtlas.load(ctx.session)
    reach = Reach(atlas)
    by_world = await places_by_world(ctx, atlas)
    roads, canals = await eased_regions(ctx, atlas)
    lands = {row.entity_id: row for row in await ctx.session.scalars(select(RegionEnvironmentRow))}
    ways = Ways(lands, roads, canals)
    worlds = sorted({land.world_id for land in lands.values()} | set(by_world))
    for world in worlds:
        places = by_world.get(world, [])
        market_regions = await rank_world(ctx, reach, places, tally) if places else set()
        towns = sorted(places, key=lambda item: (-item.people, item.town.id))
        markets = {region: next(place.town.id for place in towns if place.region == region) for region in market_regions}
        await draw_rings(ctx, atlas, ways, world=world, markets=markets, tally=tally)
    await ctx.session.flush()
