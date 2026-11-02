import math
from dataclasses import dataclass, field

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.cartography.model import BorderKind, Coordinates, MapWindow, WorldMap
from aerona.constants.books import (
    COAST_STROKE,
    COMPASS_MARGIN,
    COMPASS_SIZE,
    COORDINATE_DECIMALS,
    FIGURE_REFERENCE,
    HALO_STROKE,
    LABEL_CHARACTER_WIDTH,
    LABEL_GAP,
    LABEL_LETTER_SPACING,
    REGION_DASH,
    REGION_LABEL_BASE,
    REGION_LABEL_GAIN,
    REGION_LABEL_MAX,
    REGION_LABEL_MIN,
    REGION_STROKE,
    ROAD_DASH,
    ROAD_STROKE,
    SETTLEMENT_LABEL_OFFSET,
    SETTLEMENT_STYLE,
    SUB_REGION_DASH,
    SUB_REGION_STROKE,
)
from aerona.db.tables.celestial import WorldMapRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EntityStatus
from aerona.rules.registry import Rules
from aerona.services.books.terrain import book_frame
from aerona.services.map_lines import routed_roads
from aerona.services.wiki import SettlementTier, road_network, settlement_tiers


@dataclass(frozen=True)
class MapStroke:
    d: str
    colour: str
    width: float
    opacity: float
    dash: str


@dataclass(frozen=True)
class MapSettlement:
    x: float
    y: float
    radius: float
    tier: str


@dataclass(frozen=True)
class MapLabel:
    x: float
    y: float
    text: str
    size: float
    anchor: str
    water: bool = False
    region: bool = False


@dataclass(frozen=True)
class MapPicture:
    world_id: int
    signature: str
    view_box: str
    x: float
    y: float
    width: float
    height: float
    unit: float
    ink: str
    water_ink: str
    halo: str
    halo_width: float
    strokes: list[MapStroke] = field(default_factory=list)
    settlements: list[MapSettlement] = field(default_factory=list)
    labels: list[MapLabel] = field(default_factory=list)
    compass: tuple[float, float, float] | None = None
    legend: list[str] = field(default_factory=list)


Box = tuple[float, float, float, float]


def _number(value: float) -> str:
    return f"{round(value, COORDINATE_DECIMALS):g}"


def _segments_path(world_map: WorldMap, kind: BorderKind, frame: MapWindow) -> str:
    coordinates = world_map.borders.coordinates
    parts: list[str] = []
    right, bottom = frame.x + frame.width, frame.y + frame.height
    for index, border in enumerate(world_map.borders.kinds):
        if border is not kind:
            continue
        offset = index * 4
        x1, y1, x2, y2 = coordinates[offset : offset + 4]
        if max(x1, x2) < frame.x or min(x1, x2) > right or max(y1, y2) < frame.y or min(y1, y2) > bottom:
            continue
        parts.append(f"M{_number(x1)} {_number(y1)}L{_number(x2)} {_number(y2)}")
    return "".join(parts)


def _polyline(path: list[float]) -> str:
    points = [f"{_number(path[index])} {_number(path[index + 1])}" for index in range(0, len(path) - 1, 2)]
    return ("M" + "L".join(points)) if len(points) >= 2 else ""


def _dash(pattern: tuple[float, float], unit: float) -> str:
    return " ".join(_number(value * unit) for value in pattern)


def _box(x: float, y: float, text: str, size: float, *, anchor: str, spacing: float, gap: float) -> Box:
    width = len(text) * size * (LABEL_CHARACTER_WIDTH + spacing)
    left = x - width / 2 if anchor == "middle" else x
    return left - gap, y - size - gap, left + width + gap, y + size * 0.3 + gap


def _overlaps(box: Box, taken: list[Box]) -> bool:
    return any(not (box[2] < other[0] or box[0] > other[2] or box[3] < other[1] or box[1] > other[3]) for other in taken)


def _inside(point: Coordinates, frame: MapWindow) -> bool:
    return frame.x <= point[0] <= frame.x + frame.width and frame.y <= point[1] <= frame.y + frame.height


def build_picture(
    world_map: WorldMap,
    *,
    world_id: int,
    signature: str,
    names: dict[int, str],
    tiers: dict[int, str],
    roads: list[list[float]],
) -> MapPicture | None:
    if not world_map.regions:
        return None
    frame = book_frame(world_map)
    unit = frame.width / FIGURE_REFERENCE
    gap = LABEL_GAP * unit
    palette = world_map.palette
    strokes = [
        MapStroke(_segments_path(world_map, BorderKind.SUB_REGION, frame), palette.land_label, SUB_REGION_STROKE * unit, 0.45, _dash(SUB_REGION_DASH, unit)),
        MapStroke(_segments_path(world_map, BorderKind.REGION, frame), palette.land_label, REGION_STROKE * unit, 0.7, _dash(REGION_DASH, unit)),
        MapStroke(_segments_path(world_map, BorderKind.COAST, frame), palette.coastline, COAST_STROKE * unit, 0.85, ""),
    ]
    strokes += [MapStroke(d, palette.coastline, ROAD_STROKE * unit, 0.75, _dash(ROAD_DASH, unit)) for road in roads if (d := _polyline(road))]
    ranked = sorted(
        (marker for marker in world_map.markers if marker.id in tiers and _inside((marker.x, marker.y), frame)),
        key=lambda marker: (SETTLEMENT_STYLE[tiers[marker.id]][2], marker.id),
    )
    taken: list[Box] = []
    settlements: list[MapSettlement] = []
    for marker in ranked:
        radius = SETTLEMENT_STYLE[tiers[marker.id]][0] * unit
        settlements.append(MapSettlement(marker.x, marker.y, radius, tiers[marker.id]))
        if tiers[marker.id] != SettlementTier.VILLAGE:
            taken.append((marker.x - radius, marker.y - radius, marker.x + radius, marker.y + radius))
    labels: list[MapLabel] = []
    for region in sorted(world_map.regions, key=lambda item: -item.size):
        centroid = region.centroid
        if region.depth != 0 or centroid is None or region.id not in names or not _inside(centroid, frame):
            continue
        size = min(REGION_LABEL_MAX, max(REGION_LABEL_MIN, REGION_LABEL_BASE + math.sqrt(region.size) * REGION_LABEL_GAIN)) * unit
        text = names[region.id].upper()
        box = _box(centroid[0], centroid[1], text, size, anchor="middle", spacing=LABEL_LETTER_SPACING, gap=gap)
        if _overlaps(box, taken):
            continue
        taken.append(box)
        labels.append(MapLabel(centroid[0], centroid[1], text, size, "middle", water=region.is_water, region=True))
    for marker in ranked:
        radius, size, _rank = SETTLEMENT_STYLE[tiers[marker.id]]
        name = names.get(marker.id)
        if not name or size <= 0:
            continue
        x = marker.x + (radius + SETTLEMENT_LABEL_OFFSET) * unit
        y = marker.y + size * unit * 0.35
        box = _box(x, y, name, size * unit, anchor="start", spacing=0.0, gap=gap)
        if _overlaps(box, taken):
            continue
        taken.append(box)
        labels.append(MapLabel(x, y, name, size * unit, "start"))
    compass_size = COMPASS_SIZE * unit
    margin = COMPASS_MARGIN * unit
    present = {settlement.tier for settlement in settlements}
    return MapPicture(
        world_id=world_id,
        signature=signature,
        view_box=f"{_number(frame.x)} {_number(frame.y)} {_number(frame.width)} {_number(frame.height)}",
        x=frame.x,
        y=frame.y,
        width=frame.width,
        height=frame.height,
        unit=unit,
        ink=palette.land_label,
        water_ink=palette.water_label,
        halo=palette.background,
        halo_width=HALO_STROKE * unit,
        strokes=[stroke for stroke in strokes if stroke.d],
        settlements=list(reversed(settlements)),
        labels=labels,
        compass=(frame.x + frame.width - margin - compass_size / 2, frame.y + margin + compass_size / 2, compass_size),
        legend=sorted(present, key=lambda tier: SETTLEMENT_STYLE[tier][2]),
    )


async def load_map(session: AsyncSession, world_id: int) -> tuple[WorldMap, str] | None:
    row = await session.get(WorldMapRow, world_id)
    if row is None:
        return None
    try:
        return WorldMap.model_validate(row.geometry), row.signature or str(row.epoch)
    except ValidationError:
        return None


async def map_picture(session: AsyncSession, rules: Rules, world_id: int, epoch: int) -> MapPicture | None:
    loaded = await load_map(session, world_id)
    if loaded is None:
        return None
    world_map, signature = loaded
    names = {
        entity_id: name
        for entity_id, name in await session.execute(
            select(EntityRow.id, EntityRow.name).where(EntityRow.world_id == world_id, EntityRow.status == EntityStatus.CANON)
        )
    }
    tiers = {entity_id: info.tier.value for entity_id, info in (await settlement_tiers(session, rules, world_id, epoch)).items()}
    positions = {marker.id: (marker.x, marker.y) for marker in world_map.markers}
    roads = [routed.path for routed in routed_roads(world_map, await road_network(session, world_id), positions)]
    return build_picture(world_map, world_id=world_id, signature=signature, names=names, tiers=tiers, roads=roads)
