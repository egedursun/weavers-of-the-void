from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field

from aerona.catalog.zones import OUTSIDE_WALLS, RING_OF_ZONE, WATERSIDE, ZONE_OF_DISTRICT
from aerona.core.random import SeededRandom
from aerona.db.tables.settlement import DistrictRow
from aerona.domain.enums.settlement import DistrictKind
from aerona.domain.enums.urban import Morphology
from aerona.rules.registry import Rules

Hex = tuple[int, int]
CENTRE: Hex = (0, 0)
DIRECTIONS: tuple[Hex, ...] = ((1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1))
SEARCH = 12
HEX_KEY = "hex"


def distance(first: Hex, second: Hex) -> int:
    dq, dr = first[0] - second[0], first[1] - second[1]
    return (abs(dq) + abs(dr) + abs(dq + dr)) // 2


def neighbours(cell: Hex) -> list[Hex]:
    return [(cell[0] + dq, cell[1] + dr) for dq, dr in DIRECTIONS]


def ring(radius: int) -> list[Hex]:
    if radius == 0:
        return [CENTRE]
    found: list[Hex] = []
    q, r = DIRECTIONS[4][0] * radius, DIRECTIONS[4][1] * radius
    for side in range(6):
        for _ in range(radius):
            found.append((q, r))
            q, r = q + DIRECTIONS[side][0], r + DIRECTIONS[side][1]
    return found


def seed_of(district: DistrictRow) -> Hex | None:
    return (district.hex_q, district.hex_r) if district.hex_q is not None and district.hex_r is not None else None


def size_of(rules: Rules, district: DistrictRow) -> int:
    return max(1, district.level * rules.city_plan.cells_per_level)


def spread(seed: Hex, size: int, taken: dict[Hex, int], fits: Callable[[Hex], bool], *, through: bool) -> list[Hex]:
    found: list[Hex] = []
    frontier = [seed]
    seen = {seed}
    while frontier and len(found) < size:
        frontier.sort(key=lambda cell: (distance(cell, seed), distance(cell, CENTRE), cell))
        cell = frontier.pop(0)
        free = cell not in taken and (cell == seed or fits(cell))
        if free:
            found.append(cell)
        if not free and not through:
            continue
        for near in neighbours(cell):
            if near not in seen:
                seen.add(near)
                frontier.append(near)
    return found


def claim(seed: Hex, size: int, taken: dict[Hex, int], fits: Callable[[Hex], bool] = lambda cell: True) -> list[Hex]:
    near = spread(seed, size, taken, fits, through=False)
    if len(near) >= size:
        return near
    far = spread(seed, size, {**taken, **dict.fromkeys(near, -1)}, fits, through=True)
    return near + far[: size - len(near)]


@dataclass
class CityLayout:
    cells: dict[Hex, int] = field(default_factory=dict)
    footprints: dict[int, list[Hex]] = field(default_factory=dict)
    seeds: dict[int, Hex] = field(default_factory=dict)
    walls_radius: int | None = None

    def apart(self, first: int, second: int) -> int:
        if first == second:
            return 0
        one, other = self.seeds.get(first), self.seeds.get(second)
        return distance(one, other) if one is not None and other is not None else 0


def layout_of(rules: Rules, districts: Sequence[DistrictRow], walls_level: int = 0) -> CityLayout:
    found = CityLayout()
    placed = sorted(
        (district for district in districts if seed_of(district) is not None),
        key=lambda item: (item.kind in OUTSIDE_WALLS, RING_OF_ZONE[ZONE_OF_DISTRICT[item.kind]], item.id),
    )
    reserved: dict[Hex, int] = {}
    for district in placed:
        seed = seed_of(district)
        if seed is not None:
            reserved.setdefault(seed, district.id)
    walls: int | None = None
    for district in placed:
        seed = seed_of(district)
        if seed is None:
            continue
        outer = district.kind in OUTSIDE_WALLS
        if outer and walls is None and walls_level > 0 and found.cells:
            walls = max(distance(cell, CENTRE) for cell in found.cells) + 1
        found.seeds[district.id] = seed
        others = {cell: owner for cell, owner in reserved.items() if owner != district.id}
        beyond = walls
        fits = (lambda cell, edge=beyond: distance(cell, CENTRE) > edge) if outer and beyond is not None else (lambda cell: True)
        cells = claim(seed, size_of(rules, district), {**others, **found.cells}, fits)
        found.footprints[district.id] = cells
        for cell in cells:
            found.cells[cell] = district.id
    inner = [cell for district in placed if district.kind not in OUTSIDE_WALLS for cell in found.footprints.get(district.id, [])]
    if walls_level > 0 and inner:
        found.walls_radius = max(distance(cell, CENTRE) for cell in inner) + 1
    return found


def band_of(rules: Rules, kind: DistrictKind) -> int:
    return RING_OF_ZONE[ZONE_OF_DISTRICT[kind]] * rules.city_plan.ring_spacing


def ordered(cells: Iterable[Hex], morphology: Morphology, rng: SeededRandom) -> list[Hex]:
    items = list(cells)
    if morphology is Morphology.PLANNED:
        return sorted(items, key=lambda cell: (cell[1], cell[0]))
    if morphology is Morphology.CONCENTRIC:
        return items
    weights = {cell: rng.random() for cell in sorted(items)}
    return sorted(items, key=lambda cell: (weights[cell], cell))


def toward(cell: Hex, water: int) -> int:
    dq, dr = DIRECTIONS[water]
    return -(cell[0] * dq + cell[1] * dr)


def plan_seed(rules: Rules, layout: CityLayout, kind: DistrictKind, morphology: Morphology, *, rng: SeededRandom, waterside: int | None) -> Hex:
    start = band_of(rules, kind)
    if kind in OUTSIDE_WALLS and layout.walls_radius is not None:
        start = max(start, layout.walls_radius + 1)
    taken_seeds = set(layout.seeds.values())
    for radius in range(start, start + SEARCH):
        candidates = [cell for cell in ring(radius) if cell not in layout.cells and cell not in taken_seeds]
        if kind in WATERSIDE and waterside is not None:
            candidates.sort(key=lambda cell: (toward(cell, waterside), cell))
        else:
            candidates = ordered(candidates, morphology, rng)
        if candidates:
            return candidates[0]
    return ring(start + SEARCH)[0]


def water_side(seed: int, coastal: bool) -> int | None:
    return seed % len(DIRECTIONS) if coastal else None


def falloff(reach: float, apart: int) -> float:
    return 1.0 if apart <= 0 else reach**apart
