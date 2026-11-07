from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.cartography.graph import RegionGraph
from aerona.cartography.model import ElevationClass, RegionRecord
from aerona.constants.engine import ADJACENT_HOPS, LOCATION_CHAIN_MAX_HOPS, UNKNOWN_DISTANCE
from aerona.db.read_memo import memo_of, table_names
from aerona.db.tables.celestial import WorldMapRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityType
from aerona.engine.primitives.map_store import stored_regions
from aerona.rules.registry import Rules

ATLAS_TABLES = table_names((EntityRow, WorldMapRow))
MAP_TABLES = table_names((WorldMapRow,))


@dataclass(frozen=True)
class Placement:
    entity_id: int
    entity_type: EntityType
    world_id: int
    location_id: int | None


@dataclass(frozen=True)
class Terrain:
    graphs: dict[int, RegionGraph]
    records: dict[int, RegionRecord]

    @classmethod
    def of(cls, records: dict[int, list[RegionRecord]]) -> "Terrain":
        return cls(
            {world_id: RegionGraph(world_records) for world_id, world_records in records.items()},
            {record.id: record for world_records in records.values() for record in world_records},
        )


async def terrain_of(session: AsyncSession) -> Terrain:
    memo = memo_of(session, "atlas.terrain", MAP_TABLES)
    if memo is not None and "terrain" in memo:
        found: Terrain = memo["terrain"]
        return found
    terrain = Terrain.of(await stored_regions(session))
    if memo is not None:
        memo["terrain"] = terrain
    return terrain


class RegionAtlas:
    def __init__(self, placements: dict[int, Placement], records: dict[int, list[RegionRecord]], terrain: Terrain | None = None) -> None:
        shared = terrain or Terrain.of(records)
        self._placements = placements
        self._graphs = shared.graphs
        self._records = shared.records
        self._top: dict[int, int | None] = {}

    @classmethod
    async def load(cls, session: AsyncSession) -> "RegionAtlas":
        memo = memo_of(session, "atlas", ATLAS_TABLES)
        if memo is not None and "atlas" in memo:
            found: RegionAtlas = memo["atlas"]
            return found
        rows = await session.execute(select(EntityRow.id, EntityRow.entity_type, EntityRow.world_id, EntityRow.location_id))
        placements = {row[0]: Placement(row[0], row[1], row[2], row[3]) for row in rows}
        atlas = cls(placements, {}, await terrain_of(session))
        if memo is not None:
            memo["atlas"] = atlas
        return atlas

    def remember(self, entity: EntityRow) -> None:
        self._placements[entity.id] = Placement(entity.id, entity.entity_type, entity.world_id, entity.location_id)
        self._top.clear()

    def top_region(self, entity_id: int | None) -> int | None:
        if entity_id is None:
            return None
        if entity_id in self._top:
            return self._top[entity_id]
        found: int | None = None
        current = self._placements.get(entity_id)
        seen: set[int] = set()
        hops = 0
        while current is not None and current.entity_id not in seen and hops <= LOCATION_CHAIN_MAX_HOPS:
            seen.add(current.entity_id)
            if current.entity_type is EntityType.REGION:
                found = current.entity_id
            current = self._placements.get(current.location_id) if current.location_id is not None else None
            hops += 1
        self._top[entity_id] = found
        return found

    def communities_in(self, region_id: int) -> list[int]:
        return sorted(
            placement.entity_id
            for placement in self._placements.values()
            if placement.entity_type in COMMUNITY_TYPES and self.top_region(placement.entity_id) == region_id
        )

    def world_of(self, entity_id: int) -> int | None:
        placement = self._placements.get(entity_id)
        return placement.world_id if placement is not None else None

    def same_region(self, first: int, second: int) -> bool:
        region = self.top_region(first)
        return region is not None and region == self.top_region(second)

    def region_hops(self, first_region: int | None, second_region: int | None) -> int | None:
        if first_region is None or second_region is None:
            return None
        if first_region == second_region:
            return 0
        world = self.world_of(first_region)
        if world is None or world != self.world_of(second_region):
            return None
        graph = self._graphs.get(world)
        return graph.hop_distance(first_region, second_region) if graph is not None else None

    def region_path(self, first_region: int | None, second_region: int | None, avoid: frozenset[int] = frozenset()) -> list[int] | None:
        if first_region is None or second_region is None:
            return None
        world = self.world_of(first_region)
        if world is None or world != self.world_of(second_region):
            return None
        graph = self._graphs.get(world)
        return graph.path(first_region, second_region, avoid) if graph is not None else None

    def hops(self, first: int, second: int) -> int | None:
        return self.region_hops(self.top_region(first), self.top_region(second))

    def distance(self, first: int, second: int) -> int:
        hops = self.hops(first, second)
        return UNKNOWN_DISTANCE if hops is None else hops

    def adjacent(self, first: int, second: int) -> bool:
        hops = self.hops(first, second)
        return hops is not None and hops <= ADJACENT_HOPS

    def near(self, first: int, second: int, seafaring_reach: int | None) -> bool:
        hops = self.hops(first, second)
        if hops is None:
            return False
        reach = seafaring_reach if seafaring_reach is not None else ADJACENT_HOPS
        return hops <= reach

    def neighbour_regions(self, region_id: int) -> list[int]:
        world = self.world_of(region_id)
        graph = self._graphs.get(world) if world is not None else None
        if graph is None:
            return []
        return [other for other in graph.within(region_id, ADJACENT_HOPS) if other != region_id]

    def is_water(self, region_id: int) -> bool:
        record = self._records.get(region_id)
        return record is not None and (record.is_water or record.elevation_class is ElevationClass.WATER)

    def record(self, region_id: int) -> RegionRecord | None:
        return self._records.get(region_id)


def seafaring_reach(rules: Rules, seafaring: bool, sea_ban: bool) -> int | None:
    return rules.world_engine.seafaring_reach_hops if seafaring and not sea_ban else None
