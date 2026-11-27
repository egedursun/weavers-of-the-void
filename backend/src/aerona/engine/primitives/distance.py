from dataclasses import dataclass

from sqlalchemy import event, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import ORMExecuteState, Session

from aerona.cartography.graph import RegionGraph
from aerona.cartography.model import ElevationClass, RegionRecord
from aerona.constants.engine import ADJACENT_HOPS, LOCATION_CHAIN_MAX_HOPS, UNKNOWN_DISTANCE
from aerona.db.read_memo import memo_of, register_index, table_names, touched_rows
from aerona.db.tables.celestial import WorldMapRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.geology import DeepPassageRow
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus, EntityType
from aerona.domain.enums.environment import MovementMode
from aerona.domain.enums.geology import UndergroundStratum
from aerona.engine.primitives.deep import Cell, DeepEdge, LayeredGraph, Level, passage_kind
from aerona.engine.primitives.map_store import stored_regions
from aerona.rules.registry import Rules

ATLAS_TABLES = table_names((EntityRow, WorldMapRow, DeepPassageRow))
MAP_TABLES = table_names((WorldMapRow,))


@dataclass(frozen=True)
class Placement:
    entity_id: int
    entity_type: EntityType
    world_id: int
    location_id: int | None
    living: bool = True
    stratum: UndergroundStratum | None = None


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


PLACEMENT_SQL = text("SELECT id, entity_type, world_id, location_id, status, stratum FROM entities")
LIVE_PLACEMENTS = "aerona.live_placements"
ENTITY_TYPES = {kind.value: kind for kind in EntityType}
STRATA_BY_VALUE: dict[str | None, UndergroundStratum] = {stratum.value: stratum for stratum in UndergroundStratum}


def follow_placements(sync: Session, *_: object) -> None:
    live: dict[int, Placement] | None = sync.info.get(LIVE_PLACEMENTS)
    if live is None:
        return
    new, dirty, deleted = touched_rows(sync, EntityRow)
    for row in (*new, *dirty):
        if row.id is not None:
            live[row.id] = Placement(row.id, row.entity_type, row.world_id, row.location_id, row.status == EntityStatus.CANON, row.stratum)
    for row in deleted:
        live.pop(row.id, None)


def drop_placements(sync: Session, *_: object) -> None:
    sync.info.pop(LIVE_PLACEMENTS, None)


def drop_placements_on_write(state: ORMExecuteState) -> None:
    if not state.is_select and getattr(getattr(state.statement, "table", None), "name", EntityRow.__tablename__) == EntityRow.__tablename__:
        drop_placements(state.session)


event.listen(Session, "after_flush", follow_placements)
event.listen(Session, "after_soft_rollback", drop_placements)
event.listen(Session, "do_orm_execute", drop_placements_on_write)
register_index(LIVE_PLACEMENTS)


async def placements_of(session: AsyncSession) -> dict[int, Placement]:
    await session.flush()
    live: dict[int, Placement] | None = session.sync_session.info.get(LIVE_PLACEMENTS)
    if live is None:
        live = {
            entity_id: Placement(entity_id, ENTITY_TYPES[kind], world_id, location_id, status == EntityStatus.CANON.value, STRATA_BY_VALUE.get(stratum))
            for entity_id, kind, world_id, location_id, status, stratum in (await session.execute(PLACEMENT_SQL)).all()
        }
        session.sync_session.info[LIVE_PLACEMENTS] = live
    return dict(live)


class RegionAtlas:
    def __init__(
        self,
        placements: dict[int, Placement],
        records: dict[int, list[RegionRecord]],
        terrain: Terrain | None = None,
        passages: tuple[DeepEdge, ...] = (),
        rules: Rules | None = None,
    ) -> None:
        shared = terrain or Terrain.of(records)
        self._placements = placements
        self._graphs = shared.graphs
        self._records = shared.records
        self._top: dict[int, int | None] = {}
        self._communities: dict[int, list[int]] | None = None
        table = (rules or Rules()).underground
        self._layers = LayeredGraph(self.neighbours, passages, narrow_width=table.narrow_width, vertical_cost=table.vertical_hop_cost)

    @classmethod
    async def load(cls, session: AsyncSession) -> "RegionAtlas":
        memo = memo_of(session, "atlas", ATLAS_TABLES)
        if memo is not None and "atlas" in memo:
            found: RegionAtlas = memo["atlas"]
            return found
        atlas = cls(await placements_of(session), {}, await terrain_of(session), await deep_edges(session))
        after = memo_of(session, "atlas", ATLAS_TABLES)
        if after is not None:
            after["atlas"] = atlas
        return atlas

    def remember(self, entity: EntityRow) -> None:
        self._placements[entity.id] = Placement(entity.id, entity.entity_type, entity.world_id, entity.location_id, entity.status == EntityStatus.CANON)
        self._top.clear()
        self._communities = None

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

    def holds(self, place_id: int, entity_id: int) -> bool:
        current = self._placements.get(entity_id)
        hops = 0
        while current is not None and hops <= LOCATION_CHAIN_MAX_HOPS:
            if current.entity_id == place_id:
                return True
            current = self._placements.get(current.location_id) if current.location_id is not None else None
            hops += 1
        return False

    def communities_in(self, region_id: int) -> list[int]:
        if self._communities is None:
            grouped: dict[int, list[int]] = {}
            for placement in self._placements.values():
                if placement.entity_type in COMMUNITY_TYPES and placement.living:
                    region = self.top_region(placement.entity_id)
                    if region is not None:
                        grouped.setdefault(region, []).append(placement.entity_id)
            self._communities = {region: sorted(found) for region, found in grouped.items()}
        return list(self._communities.get(region_id, []))

    def settlements_in(self, region_id: int) -> list[int]:
        return [
            node
            for node in self.communities_in(region_id)
            if (placement := self._placements.get(node)) is not None and placement.entity_type is EntityType.SETTLEMENT
        ]

    def world_of(self, entity_id: int) -> int | None:
        placement = self._placements.get(entity_id)
        return placement.world_id if placement is not None else None

    def neighbours(self, region_id: int) -> list[int]:
        world = self.world_of(region_id)
        graph = self._graphs.get(world) if world is not None else None
        return graph.neighbours(region_id) if graph is not None and region_id in graph else []

    def level_of(self, entity_id: int | None) -> Level:
        current = self._placements.get(entity_id) if entity_id is not None else None
        hops = 0
        while current is not None and hops <= LOCATION_CHAIN_MAX_HOPS:
            above = self._placements.get(current.location_id) if current.location_id is not None else None
            if above is not None and above.entity_type is EntityType.REGION:
                return current.stratum
            current = above
            hops += 1
        return None

    def cell_of(self, entity_id: int | None) -> Cell | None:
        region = self.top_region(entity_id)
        if region is None:
            return None
        return (region, None) if entity_id == region else (region, self.level_of(entity_id))

    def same_cell(self, first: int, second: int) -> bool:
        cell = self.cell_of(first)
        return cell is not None and cell == self.cell_of(second)

    def cell_hops(self, first: Cell | None, second: Cell | None, modes: frozenset[MovementMode] | None = None) -> int | None:
        if first is None or second is None:
            return None
        if first[1] is None and second[1] is None and (modes is None or self._layers.empty):
            return self.region_hops(first[0], second[0])
        if self.world_of(first[0]) != self.world_of(second[0]):
            return None
        return self._layers.hops(first, second, modes)

    def cell_path(
        self, first: Cell | None, second: Cell | None, modes: frozenset[MovementMode] | None = None, avoid: frozenset[Cell] = frozenset()
    ) -> list[Cell] | None:
        if first is None or second is None or self.world_of(first[0]) != self.world_of(second[0]):
            return None
        return self._layers.path(first, second, modes, avoid)

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
        return self.cell_hops(self.cell_of(first), self.cell_of(second))

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


async def deep_edges(session: AsyncSession) -> tuple[DeepEdge, ...]:
    rows = await session.execute(
        select(
            DeepPassageRow.first_region_entity_id,
            DeepPassageRow.first_stratum,
            DeepPassageRow.second_region_entity_id,
            DeepPassageRow.second_stratum,
            DeepPassageRow.state,
            DeepPassageRow.width,
        ).order_by(DeepPassageRow.id)
    )
    return tuple(
        DeepEdge((first, upper), (second, lower), state, width, passage_kind((first, upper), (second, lower)))
        for first, upper, second, lower, state, width in rows.all()
    )


def seafaring_reach(rules: Rules, seafaring: bool, sea_ban: bool) -> int | None:
    return rules.world_engine.seafaring_reach_hops if seafaring and not sea_ban else None
