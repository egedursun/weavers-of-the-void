from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.cartography.model import Coordinates, WorldMap
from aerona.cartography.routing import CellRouter
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.city_rules import ConurbationRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.warfare import WarRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.war import WarStatus
from aerona.services.wiki import Road, RoadKind

CONURBATION = "conurbation"
RELATION_KINDS: dict[BondKind, str] = {
    BondKind.TRADES_WITH: "trade",
    BondKind.ENEMY: "hostility",
    BondKind.RULES: "rule",
    BondKind.HUNTS: "hunt",
}
ROUTED_RELATIONS = frozenset({BondKind.TRADES_WITH})


@dataclass(frozen=True)
class RoutedRoad:
    road: Road
    path: list[float]


@dataclass(frozen=True)
class RelationLine:
    source: int
    target: int
    kind: str
    description: str | None
    path: list[float]


@dataclass(frozen=True)
class WarSite:
    id: int
    war_id: int
    name: str
    location_id: int | None
    started_epoch: int
    ended_epoch: int | None
    ongoing: bool


def straight(start: Coordinates, end: Coordinates) -> list[float]:
    return [start[0], start[1], end[0], end[1]]


def routed_roads(world_map: WorldMap, roads: Sequence[Road], positions: Mapping[int, Coordinates]) -> list[RoutedRoad]:
    router = CellRouter.of(world_map.cells) if roads else None
    routed: list[RoutedRoad] = []
    for road in roads:
        start, end = positions.get(road.first), positions.get(road.second)
        if start is None or end is None or router is None:
            continue
        routed.append(RoutedRoad(road, router.route(start, end)))
    return routed


async def relation_lines(session: AsyncSession, world_map: WorldMap, positions: Mapping[int, Coordinates], roads: Sequence[Road]) -> list[RelationLine]:
    if not positions:
        return []
    drawn = {frozenset((road.first, road.second)) for road in roads if road.kind is RoadKind.TRADE}
    ids = list(positions)
    bonds = await session.scalars(
        select(BondRow)
        .where(
            BondRow.kind.in_(list(RELATION_KINDS)),
            BondRow.state == BondState.ACTIVE,
            or_(BondRow.source_node_id.in_(ids), BondRow.target_node_id.in_(ids)),
        )
        .order_by(BondRow.id)
    )
    router: CellRouter | None = None
    lines: list[RelationLine] = []
    seen: set[tuple[frozenset[int], BondKind]] = set()
    for bond in bonds:
        start, end = positions.get(bond.source_node_id), positions.get(bond.target_node_id)
        pair = frozenset((bond.source_node_id, bond.target_node_id))
        if start is None or end is None or len(pair) < 2 or (pair, bond.kind) in seen:
            continue
        if bond.kind is BondKind.TRADES_WITH and pair in drawn:
            continue
        seen.add((pair, bond.kind))
        if bond.kind in ROUTED_RELATIONS:
            router = router or CellRouter.of(world_map.cells)
            path = router.route(start, end)
        else:
            path = straight(start, end)
        lines.append(RelationLine(bond.source_node_id, bond.target_node_id, RELATION_KINDS[bond.kind], bond.description, path))
    return lines


async def conurbation_lines(session: AsyncSession, positions: Mapping[int, Coordinates]) -> list[RelationLine]:
    lines: list[RelationLine] = []
    for city in await session.scalars(select(ConurbationRow).where(ConurbationRow.split_epoch.is_(None)).order_by(ConurbationRow.id)):
        start = positions.get(city.core_entity_id)
        for member in city.members or []:
            end = positions.get(member)
            if start is not None and end is not None:
                lines.append(RelationLine(city.core_entity_id, member, CONURBATION, "grown together into one city", straight(start, end)))
    return lines


async def war_sites(session: AsyncSession, world_id: int, shown: int, current: int) -> list[WarSite]:
    past = shown < current
    statement = select(WarRow, EntityRow).join(EntityRow, EntityRow.id == WarRow.event_entity_id).where(WarRow.world_id == world_id).order_by(WarRow.id)
    sites: list[WarSite] = []
    for war, event in await session.execute(statement):
        if past and war.started_epoch > shown:
            continue
        ongoing = not past and war.status is not WarStatus.ENDED
        sites.append(WarSite(event.id, war.id, event.name, event.location_id, war.started_epoch, war.ended_epoch, ongoing))
    return sites


def region_creators(entities: Sequence[EntityRow]) -> dict[int, int | None]:
    return {entity.id: entity.creator_son_id for entity in entities if entity.entity_type is EntityType.REGION}
