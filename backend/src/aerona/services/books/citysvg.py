import math
from collections import defaultdict
from dataclasses import dataclass

from markupsafe import Markup, escape
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.structures import STRUCTURES
from aerona.catalog.urban import SERVICE_OF
from aerona.catalog.zones import CIVIC_SERVICE_OF, ZONE_OF_DISTRICT, ZONE_OF_STRUCTURE
from aerona.core.grammar import several
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.economy import ResourceProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.settlement import DistrictRow, SettlementInfrastructureRow, SettlementProfileRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.structure import ConstructionState, StructureKind
from aerona.domain.enums.urban import HousingLevel, LandCover, LandGround, Morphology, ZoneKind
from aerona.engine.primitives.stats import stat_or
from aerona.engine.urban.cityscape import Tile, homes_of, land_tiles, perimeter_of, pick_tile, provisional, resource_prefer, slots_of
from aerona.engine.urban.coverage import people_of_districts
from aerona.engine.urban.layout import Hex, ring
from aerona.rules.registry import Rules
from aerona.services.books.typed import RecordTable

UNIT = 10.0
CORNER = 1.15
PAD = 2.5
PAPER = "#f6f1e4"
INK = "#3a3326"
WATER = "#7fb4d8"
WALL = "#6b5b45"
ZONE_INK: dict[ZoneKind, str] = {
    ZoneKind.GOVERNANCE: "#c9a240",
    ZoneKind.RESIDENTIAL: "#c9744f",
    ZoneKind.COMMERCIAL: "#5d8fc4",
    ZoneKind.INDUSTRIAL: "#8a74a8",
    ZoneKind.AGRICULTURAL: "#b5b85a",
    ZoneKind.CIVIC: "#4f9fa6",
    ZoneKind.GREEN: "#4f9a5a",
}
GROUND_INK: dict[LandGround, str] = {
    LandGround.WATER: WATER,
    LandGround.SHORE: "#e6d6a5",
    LandGround.LOWLAND: "#a9c98a",
    LandGround.WETLAND: "#88b3a0",
    LandGround.HILLS: "#b9a979",
    LandGround.MOUNTAINS: "#8f8778",
    LandGround.PEAKS: "#e8e6e2",
}
COVER_INK: dict[LandCover, str | None] = {
    LandCover.OPEN: None,
    LandCover.FOREST: "#3f7a3f",
    LandCover.FIELDS: "#e2c95a",
    LandCover.PASTURE: "#c4d68a",
    LandCover.MARSH: "#5f9a86",
    LandCover.CLEARED: "#c9a77a",
    LandCover.BUILT: "#a08c78",
    LandCover.MINED: "#7a5a4a",
}
STATE_OPACITY: dict[ConstructionState, float] = {
    ConstructionState.PLANNED: 0.35,
    ConstructionState.BUILDING: 0.6,
    ConstructionState.COMPLETE: 1.0,
    ConstructionState.DAMAGED: 0.7,
    ConstructionState.RUINED: 0.3,
}

BUILDING_STATES = (
    frozenset({ConstructionState.COMPLETE}),
    frozenset({ConstructionState.PLANNED, ConstructionState.BUILDING}),
    frozenset({ConstructionState.DAMAGED}),
    frozenset({ConstructionState.RUINED}),
)


@dataclass
class Plan:
    figure: Markup
    caption: str
    facts: list[tuple[str, str]]


def _world(cell: Hex) -> tuple[float, float]:
    q, r = cell
    return 2 * (q + r / 2) * UNIT, math.sqrt(3) * r * UNIT


def _hex(cell: Hex, fill: str, *, stroke: str = PAPER, width: float = 0.8, opacity: float = 1.0) -> str:
    x, y = _world(cell)
    points = " ".join(
        f"{x + math.cos(math.pi / 3 * index + math.pi / 6) * CORNER * UNIT:.1f},{y + math.sin(math.pi / 3 * index + math.pi / 6) * CORNER * UNIT:.1f}"
        for index in range(6)
    )
    return f'<polygon points="{points}" fill="{fill}" fill-opacity="{opacity:.2f}" stroke="{stroke}" stroke-width="{width}"/>'


def _frame(cells: list[Hex], body: list[str], label: str) -> Markup:
    places = [_world(cell) for cell in cells] or [(0.0, 0.0)]
    left = min(x for x, _ in places) - PAD * UNIT
    top = min(y for _, y in places) - PAD * UNIT
    width = max(x for x, _ in places) - min(x for x, _ in places) + 2 * PAD * UNIT
    height = max(y for _, y in places) - min(y for _, y in places) + 2 * PAD * UNIT
    return Markup(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{left:.1f} {top:.1f} {width:.1f} {height:.1f}" role="img" aria-label="{escape(label)}">'
        f'<rect x="{left:.1f}" y="{top:.1f}" width="{width:.1f}" height="{height:.1f}" fill="{PAPER}"/>{"".join(body)}</svg>'
    )


def _slot(cell: Hex, slot: int) -> tuple[float, float]:
    x, y = _world(cell)
    if slot == 0:
        return x, y
    angle = math.tau * (slot - 1) / 6
    return x + math.cos(angle) * UNIT * 0.55, y + math.sin(angle) * UNIT * 0.55


async def city_plan(session: AsyncSession, rules: Rules, town: EntityRow) -> Plan | None:
    districts = list(await session.scalars(select(DistrictRow).where(DistrictRow.settlement_entity_id == town.id).order_by(DistrictRow.id)))
    buildings = list(
        await session.scalars(
            select(StructureProfileRow).where(StructureProfileRow.host_entity_id == town.id).order_by(StructureProfileRow.structure_entity_id)
        )
    )
    if not districts and not buildings:
        return None
    profile = await session.get(SettlementProfileRow, town.id)
    infrastructure = await session.get(SettlementInfrastructureRow, town.id)
    walls = infrastructure.walls_level if infrastructure is not None else 0
    morphology = profile.morphology if profile is not None else Morphology.ORGANIC
    layout = provisional(rules, districts, morphology, walls, town.id)
    slots = slots_of(layout, buildings, districts, await perimeter_of(session, buildings))
    people = people_of_districts(rules, round(stat_or(town, "population", 0)), districts)
    body: list[str] = []
    cells: list[Hex] = []
    for district in districts:
        for cell in layout.footprints.get(district.id, []):
            cells.append(cell)
            body.append(_hex(cell, ZONE_INK[ZONE_OF_DISTRICT[district.kind]], opacity=0.55 + district.condition / 250))
    wall_cells = ring(layout.walls_radius) if layout.walls_radius else []
    cells.extend(wall_cells)
    body.extend(_hex(cell, "none", stroke=WALL, width=2.2) for cell in wall_cells)
    for row in buildings:
        cell, slot = slots[row.structure_entity_id]
        x, y = _slot(cell, slot)
        size = UNIT * (0.22 + row.level * 0.05)
        ink = ZONE_INK[ZONE_OF_STRUCTURE[row.kind]]
        opacity = STATE_OPACITY[row.construction_state]
        body.append(
            f'<rect x="{x - size / 2:.1f}" y="{y - size / 2:.1f}" width="{size:.1f}" height="{size:.1f}" rx="1" '
            f'fill="{ink}" fill-opacity="{opacity:.2f}" stroke="{INK}" stroke-width="0.6"/>'
        )
    counts: dict[ZoneKind, list[int]] = {zone: [0, 0, 0] for zone in ZoneKind}
    for district in districts:
        share = counts[ZONE_OF_DISTRICT[district.kind]]
        share[0] += 1
        share[1] += len(layout.footprints.get(district.id, []))
    for row in buildings:
        counts[ZONE_OF_STRUCTURE[row.kind]][2] += 1
    homes = sum(homes_of(people.get(district.id, 0), rules.city_plan.household) for district in districts)
    facts = [
        (f"{zone.value.capitalize()} zone", f"{districts_n} districts on {cells_n} hexes, {built} buildings")
        for zone, (districts_n, cells_n, built) in counts.items()
        if districts_n or built
    ]
    facts.append(("Homes", f"{homes} homes for {round(stat_or(town, 'population', 0))} people"))
    facts.append(("Walls", f"level {walls}, {layout.walls_radius} hexes out" if layout.walls_radius else "none"))
    facts.append(("Growth", morphology.value))
    caption = f"{town.name}: its districts by zone on their hexes, each building in its place, shaded by its state"
    return Plan(_frame(cells, body, f"Plan of {town.name}"), caption, facts)


def _mark(cell: Hex, shape: str, size: float, fill: str) -> str:
    x, y = _world(cell)
    if shape == "circle":
        return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{size:.1f}" fill="{fill}" stroke="{INK}" stroke-width="0.8"/>'
    outline = f'fill="{fill}" stroke="{INK}" stroke-width="0.8"'
    if shape == "diamond":
        return f'<polygon points="{x:.1f},{y - size:.1f} {x + size:.1f},{y:.1f} {x:.1f},{y + size:.1f} {x - size:.1f},{y:.1f}" {outline}/>'
    if shape == "triangle":
        return f'<polygon points="{x:.1f},{y - size:.1f} {x + size:.1f},{y + size * 0.8:.1f} {x - size:.1f},{y + size * 0.8:.1f}" {outline}/>'
    return f'<rect x="{x - size:.1f}" y="{y - size:.1f}" width="{size * 2:.1f}" height="{size * 2:.1f}" fill="{fill}" stroke="{INK}" stroke-width="0.8"/>'


def _tile(tile: Tile) -> str:
    cell = (tile.q, tile.r)
    cover = COVER_INK[tile.cover]
    parts = [_hex(cell, GROUND_INK[tile.ground])]
    if cover is not None:
        parts.append(_hex(cell, cover, opacity=0.7))
    if tile.river:
        x, y = _world(cell)
        parts.append(f'<line x1="{x - UNIT:.1f}" y1="{y:.1f}" x2="{x + UNIT:.1f}" y2="{y:.1f}" stroke="{WATER}" stroke-width="3" stroke-linecap="round"/>')
    return "".join(parts)


async def land_plan(session: AsyncSession, region: EntityRow) -> Plan | None:
    land = await session.get(RegionEnvironmentRow, region.id)
    if land is None:
        return None
    tiles = land_tiles(land, region.id)
    local = list(
        await session.scalars(select(EntityRow).where(EntityRow.location_id == region.id, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id))
    )
    taken: set[Hex] = set()
    body = [_tile(tile) for tile in tiles]
    towns = [row for row in local if row.entity_type is EntityType.SETTLEMENT]
    for row in towns:
        cell = pick_tile(tiles, taken, (LandCover.BUILT,), (LandGround.LOWLAND, LandGround.SHORE))
        body.append(_mark(cell, "circle", UNIT * (0.25 + min(0.4, math.log10(max(1.0, stat_or(row, "population", 0))) / 12)), ZONE_INK[ZoneKind.GOVERNANCE]))
    places = [row for row in local if row.entity_type is EntityType.PLACE]
    for _ in places:
        body.append(_mark(pick_tile(tiles, taken, (LandCover.OPEN, LandCover.FOREST)), "triangle", UNIT * 0.35, ZONE_INK[ZoneKind.CIVIC]))
    works = list(await session.scalars(select(StructureProfileRow).where(StructureProfileRow.host_entity_id == region.id)))
    for _ in works:
        body.append(_mark(pick_tile(tiles, taken, (LandCover.MINED, LandCover.OPEN)), "square", UNIT * 0.3, ZONE_INK[ZoneKind.INDUSTRIAL]))
    profiles = {
        row.resource_entity_id: row
        for row in await session.scalars(select(ResourceProfileRow).where(ResourceProfileRow.resource_entity_id.in_([row.id for row in local])))
    }
    deposits = [profiles[row.id] for row in local if row.entity_type is EntityType.RESOURCE and row.id in profiles]
    for deposit in deposits:
        prefer, grounds = resource_prefer(deposit.commodity)
        body.append(_mark(pick_tile(tiles, taken, prefer, grounds), "diamond", UNIT * (0.2 + deposit.richness / 250), ZONE_INK[ZoneKind.AGRICULTURAL]))
    covers: dict[LandCover, int] = {}
    for tile in tiles:
        covers[tile.cover] = covers.get(tile.cover, 0) + 1
    facts = [
        (cover.value.capitalize(), f"{count} of {several(len(tiles), 'tile', 'tiles')}") for cover, count in sorted(covers.items(), key=lambda item: -item[1])
    ]
    on_land = [
        several(len(towns), "settlement", "settlements"),
        several(len(places), "place", "places"),
        several(len(works), "work", "works"),
        several(len(deposits), "deposit", "deposits"),
    ]
    facts.append(("On the land", ", ".join(on_land)))
    caption = f"{region.name}: its ground and cover tile by tile, its river, settlements (circles), places (triangles), works (squares) and deposits (diamonds)"
    return Plan(_frame([(tile.q, tile.r) for tile in tiles], body, f"Land of {region.name}"), caption, facts)


def _words(value: str) -> str:
    return value.replace("_", " ")


async def type_tables(session: AsyncSession, rules: Rules) -> list[RecordTable]:
    worlds = {row.id: row.name for row in await session.scalars(select(WorldRow).order_by(WorldRow.id))}
    rows = list(
        await session.execute(
            select(StructureProfileRow, EntityRow)
            .join(EntityRow, EntityRow.id == StructureProfileRow.structure_entity_id)
            .where(EntityRow.status == EntityStatus.CANON)
            .order_by(EntityRow.world_id, StructureProfileRow.kind, EntityRow.id)
        )
    )
    towns = {row.id: row for row in await session.scalars(select(EntityRow).where(EntityRow.entity_type == EntityType.SETTLEMENT).order_by(EntityRow.id))}
    grouped: dict[tuple[int, StructureKind], list[StructureProfileRow]] = defaultdict(list)
    for profile, entity in rows:
        grouped[(entity.world_id, profile.kind)].append(profile)
    buildings = RecordTable(
        "Building types",
        ["World", "Type", "Zone", "Serves", "Standing", "Being built", "Damaged", "In ruins", "Towns"],
    )
    for (world_id, kind), items in sorted(grouped.items(), key=lambda item: (item[0][0], item[0][1].value)):
        spec = STRUCTURES.get(kind)
        states = [sum(1 for item in items if item.construction_state in wanted) for wanted in BUILDING_STATES]
        hosts = sorted({towns[item.host_entity_id].name for item in items if item.host_entity_id in towns})
        service = SERVICE_OF.get(kind)
        civic = CIVIC_SERVICE_OF.get(kind)
        buildings.rows.append(
            [
                worlds.get(world_id, f"World {world_id}"),
                spec.label if spec is not None else _words(kind.value).capitalize(),
                ZONE_OF_STRUCTURE[kind].value,
                ", ".join(_words(part.value) for part in (civic, service) if part is not None) or "nothing",
                *(str(count) for count in states),
                ", ".join(hosts) or "the open land",
            ]
        )
    homes = RecordTable("Home types", ["World", "Home", "Districts", "Homes", "Towns"])
    by_town: dict[int, list[DistrictRow]] = defaultdict(list)
    for district in await session.scalars(select(DistrictRow).order_by(DistrictRow.settlement_entity_id, DistrictRow.id)):
        by_town[district.settlement_entity_id].append(district)
    tally: dict[tuple[int, HousingLevel], list[int]] = defaultdict(lambda: [0, 0])
    places: dict[tuple[int, HousingLevel], set[str]] = defaultdict(set)
    for town_id, quarters in by_town.items():
        town = towns.get(town_id)
        if town is None:
            continue
        people = people_of_districts(rules, round(stat_or(town, "population", 0)), quarters)
        for district in quarters:
            key = (town.world_id, district.housing)
            tally[key][0] += 1
            tally[key][1] += homes_of(people.get(district.id, 0), rules.city_plan.household)
            places[key].add(town.name)
    for (world_id, level), (count, dwellings) in sorted(tally.items(), key=lambda item: (item[0][0], item[0][1].value)):
        homes.rows.append(
            [worlds.get(world_id, f"World {world_id}"), _words(level.value), str(count), str(dwellings), ", ".join(sorted(places[(world_id, level)]))]
        )
    return [table for table in (buildings, homes) if table.rows]
