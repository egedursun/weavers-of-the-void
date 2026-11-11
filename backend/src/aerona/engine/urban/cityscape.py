import math
from collections import defaultdict
from dataclasses import dataclass

from aerona.core.random import SeededRandom
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.settlement import DistrictRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.environment import RiverClass
from aerona.domain.enums.structure import StructureKind
from aerona.domain.enums.urban import LandCover, LandGround, Morphology
from aerona.engine.urban.coverage import home_of
from aerona.engine.urban.layout import CENTRE, CityLayout, Hex, distance, layout_of, ring
from aerona.engine.urban.planning import settle
from aerona.rules.registry import Rules


@dataclass(frozen=True)
class Tile:
    q: int
    r: int
    ground: LandGround
    cover: LandCover
    river: bool


SLOTS = 7
HOUSE_SLOTS = 6
LAND_RADIUS = 4
GROUND_ORDER = (LandGround.WATER, LandGround.SHORE, LandGround.WETLAND, LandGround.LOWLAND, LandGround.HILLS, LandGround.MOUNTAINS, LandGround.PEAKS)
BIOME_GROUND = (
    LandGround.WATER,
    LandGround.WATER,
    LandGround.SHORE,
    LandGround.LOWLAND,
    LandGround.LOWLAND,
    LandGround.WETLAND,
    LandGround.HILLS,
    LandGround.HILLS,
    LandGround.MOUNTAINS,
    LandGround.PEAKS,
)
DIGGINGS = frozenset({StructureKind.MINE, StructureKind.QUARRY})
DEEP = frozenset({CommodityKind.ORE, CommodityKind.STONE, CommodityKind.COAL})
WOODS = frozenset({CommodityKind.TIMBER, CommodityKind.FUEL})
WATERS = frozenset({CommodityKind.FISH})


def provisional(rules: Rules, districts: list[DistrictRow], morphology: Morphology, walls: int, town_id: int) -> CityLayout:
    stand_ins = [
        DistrictRow(
            id=district.id,
            settlement_entity_id=town_id,
            kind=district.kind,
            level=district.level,
            hex_q=district.hex_q,
            hex_r=district.hex_r,
            locked=list(district.locked),
        )
        for district in sorted(districts, key=lambda item: item.id)
    ]
    settle(rules, stand_ins, morphology, walls)
    return layout_of(rules, stand_ins, walls)


def slots_of(layout: CityLayout, buildings: list[StructureProfileRow], districts: list[DistrictRow]) -> dict[int, tuple[Hex, int]]:
    used: dict[Hex, int] = defaultdict(int)
    found: dict[int, tuple[Hex, int]] = {}
    for profile in sorted(buildings, key=lambda item: item.structure_entity_id):
        chosen = home_of(profile, districts)
        home = profile.district_id if profile.district_id in layout.footprints else chosen.id if chosen is not None else None
        cells = layout.footprints.get(home, []) if home is not None else []
        if not cells:
            cells = [cell for radius in range(3) for cell in ring(radius)]
        cell = min(cells, key=lambda item: (used[item], distance(item, CENTRE), item))
        found[profile.structure_entity_id] = (cell, used[cell] % SLOTS)
        used[cell] += 1
    return found


def ground_counts(biome_mix: list[int], total: int) -> list[LandGround]:
    weights: dict[LandGround, float] = defaultdict(float)
    for index, share in enumerate(biome_mix[: len(BIOME_GROUND)]):
        weights[BIOME_GROUND[index]] += max(0, share)
    whole = sum(weights.values()) or 1.0
    found: list[LandGround] = []
    for ground in GROUND_ORDER:
        found.extend([ground] * round(total * weights.get(ground, 0.0) / whole))
    return (found + [LandGround.LOWLAND] * total)[:total]


def land_tiles(land: RegionEnvironmentRow, region_id: int) -> list[Tile]:
    rng = SeededRandom.for_epoch(region_id, 0, f"land.scene.{region_id}")
    cells = [cell for radius in range(LAND_RADIUS + 1) for cell in ring(radius)]
    heights = {cell: rng.random() + distance(cell, CENTRE) * (0.3 if land.coast_kind.value != "none" else 0.0) * (1 if cell[0] >= 0 else -1) for cell in cells}
    by_height = sorted(cells, key=lambda cell: (heights[cell], cell))
    grounds = dict(zip(by_height, ground_counts(land.biome_mix, len(cells)), strict=True))
    flowing = land.river_class is not RiverClass.NONE
    river = {cell for cell in cells if flowing and cell[1] == 0 and grounds[cell] is not LandGround.WATER}
    dry = [cell for cell in by_height if grounds[cell] not in (LandGround.WATER, LandGround.SHORE) and cell not in river]
    covers: dict[Hex, LandCover] = {}
    plan = (
        (LandCover.BUILT, land.built, (LandGround.LOWLAND, LandGround.HILLS)),
        (LandCover.MARSH, land.wetland, (LandGround.WETLAND, LandGround.LOWLAND)),
        (LandCover.FIELDS, land.farmed, (LandGround.LOWLAND, LandGround.WETLAND)),
        (LandCover.PASTURE, land.grazed, (LandGround.LOWLAND, LandGround.HILLS)),
        (LandCover.MINED, land.mined, (LandGround.MOUNTAINS, LandGround.HILLS, LandGround.PEAKS)),
        (LandCover.FOREST, land.forest_cover, (LandGround.LOWLAND, LandGround.HILLS, LandGround.MOUNTAINS, LandGround.WETLAND)),
        (LandCover.CLEARED, land.cleared, (LandGround.LOWLAND, LandGround.HILLS)),
    )
    for cover, share, fits in plan:
        wanted = round(len(dry) * max(0, share) / 100)
        free = [cell for cell in dry if cell not in covers]
        chosen = sorted(free, key=lambda cell: (grounds[cell] not in fits, distance(cell, CENTRE) if cover is LandCover.BUILT else heights[cell], cell))[
            :wanted
        ]
        covers.update(dict.fromkeys(chosen, cover))
    return [
        Tile(
            q=cell[0],
            r=cell[1],
            ground=grounds[cell],
            cover=covers.get(cell, LandCover.OPEN),
            river=cell in river,
        )
        for cell in cells
    ]


def pick_tile(tiles: list[Tile], taken: set[Hex], prefer: tuple[LandCover, ...], grounds: tuple[LandGround, ...] = ()) -> Hex:
    wet = LandGround.WATER in grounds
    ranked = sorted(
        tiles,
        key=lambda tile: (
            (tile.q, tile.r) in taken,
            (tile.river or tile.ground is LandGround.WATER) is not wet,
            tile.cover not in prefer,
            bool(grounds) and tile.ground not in grounds,
            distance((tile.q, tile.r), CENTRE),
        ),
    )
    cell = (ranked[0].q, ranked[0].r) if ranked else CENTRE
    taken.add(cell)
    return cell


def resource_prefer(commodity: CommodityKind) -> tuple[tuple[LandCover, ...], tuple[LandGround, ...]]:
    if commodity in DEEP:
        return (LandCover.MINED,), (LandGround.MOUNTAINS, LandGround.HILLS, LandGround.PEAKS)
    if commodity in WOODS:
        return (LandCover.FOREST,), ()
    if commodity in WATERS:
        return (), (LandGround.WATER, LandGround.SHORE)
    return (LandCover.FIELDS, LandCover.PASTURE, LandCover.OPEN), (LandGround.LOWLAND,)


def homes_of(people: float, household: int) -> int:
    return math.ceil(people / household)
