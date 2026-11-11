import re
from bisect import bisect_right
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from functools import cache
from itertools import pairwise
from math import atan2, cos, hypot, pi, radians, sin, sqrt

from aerona.catalog.heraldry import (
    CONTRAST,
    DIVISION_ZONES,
    FUR_PARTNERS,
    FUR_SOLIDS,
    FURS,
    GLYPHS,
    LIGHTNESS,
    SHAPE_ZONES,
    SHAPES,
    SOLID_TINCTURES,
    TILTS,
)
from aerona.core.total import partial, total
from aerona.domain.enums.collective import (
    ArmsInk,
    ArmsRim,
    ChargeArrangement,
    HeraldicCharge,
    HeraldicDivision,
    PartitionLine,
    ShieldShape,
    SupporterPose,
    Tincture,
)

Point = tuple[float, float]
Loop = tuple[tuple[Point, ...], bool]
Box = tuple[float, float, float, float]
Placement = tuple[float, float, float, float, bool]
D = HeraldicDivision
A = ChargeArrangement
L = PartitionLine
CENTRE = (60.0, 62.0)
FAR = 260.0
NUMBER = re.compile(r"-?(?:\d+\.?\d*|\.\d+)(?:e-?\d+)?")
STEPS = 18
BOLDEST = 6.0


@dataclass(frozen=True)
class Design:
    shape: ShieldShape
    field: Tincture
    division: HeraldicDivision
    line: PartitionLine
    second: Tincture | None
    charges: tuple[tuple[HeraldicCharge, Tincture | None], ...]
    arrangement: ChargeArrangement
    rim: ArmsRim
    rim_line: PartitionLine
    rim_tincture: Tincture | None
    supporter: HeraldicCharge
    pose: SupporterPose
    supporter_tincture: Tincture | None
    crest: HeraldicCharge
    crest_tincture: Tincture | None


@dataclass(frozen=True)
class Layer:
    d: str
    ink: ArmsInk
    filled: bool
    width: float = 0.0
    opacity: float = 1.0
    evenodd: bool = False
    clip: str | None = None
    transform: str | None = None
    clipped: bool = True


@dataclass(frozen=True)
class Drawing:
    view_box: str
    outline: str
    layers: tuple[Layer, ...]


def num(value: float) -> str:
    text = f"{value:.2f}".rstrip("0").rstrip(".")
    return "0" if text in {"-0", ""} else text


def path(points: list[Point] | tuple[Point, ...], closed: bool = True) -> str:
    body = "L".join(f"{num(x)} {num(y)}" for x, y in points)
    return f"M{body}{'Z' if closed else ''}"


def unit(x: float, y: float) -> Point:
    length = hypot(x, y)
    return (x / length, y / length)


def add(point: Point, vector: Point, scale: float = 1.0) -> Point:
    return (point[0] + vector[0] * scale, point[1] + vector[1] * scale)


def rect(x0: float, y0: float, x1: float, y1: float) -> Loop:
    return (((x0, y0), (x1, y0), (x1, y1), (x0, y1)), False)


def quad(start: Point, control: Point, end: Point) -> list[Point]:
    return [
        (
            (1 - t) ** 2 * start[0] + 2 * (1 - t) * t * control[0] + t**2 * end[0],
            (1 - t) ** 2 * start[1] + 2 * (1 - t) * t * control[1] + t**2 * end[1],
        )
        for t in (step / STEPS for step in range(1, STEPS + 1))
    ]


def cubic(start: Point, first: Point, second: Point, end: Point) -> list[Point]:
    return [
        (
            (1 - t) ** 3 * start[0] + 3 * (1 - t) ** 2 * t * first[0] + 3 * (1 - t) * t**2 * second[0] + t**3 * end[0],
            (1 - t) ** 3 * start[1] + 3 * (1 - t) ** 2 * t * first[1] + 3 * (1 - t) * t**2 * second[1] + t**3 * end[1],
        )
        for t in (step / STEPS for step in range(1, STEPS + 1))
    ]


def ellipse(cx: float, cy: float, rx: float, ry: float, count: int = 72) -> tuple[Point, ...]:
    return tuple((cx + rx * cos(2 * pi * k / count - pi / 2), cy + ry * sin(2 * pi * k / count - pi / 2)) for k in range(count))


@cache
def outline_of(shape: ShieldShape) -> tuple[Point, ...]:
    segments = SHAPES[shape]
    if segments[0][0] == "E":
        cx, cy, rx, ry = (float(value) for value in segments[0][1:])
        return ellipse(cx, cy, rx, ry)
    points: list[Point] = []
    for kind, *values in segments:
        here = points[-1] if points else (0.0, 0.0)
        if kind in {"M", "L"}:
            points.append((float(values[0]), float(values[1])))
        elif kind == "Q":
            points.extend(quad(here, (values[0], values[1]), (values[2], values[3])))
        else:
            points.extend(cubic(here, (values[0], values[1]), (values[2], values[3]), (values[4], values[5])))
    if hypot(points[0][0] - points[-1][0], points[0][1] - points[-1][1]) < 0.01:
        points.pop()
    return tuple(points)


def signed_area(points: tuple[Point, ...]) -> float:
    return sum(points[i][0] * points[(i + 1) % len(points)][1] - points[(i + 1) % len(points)][0] * points[i][1] for i in range(len(points))) / 2


def inward(start: Point, end: Point, sign: float) -> Point:
    dx, dy = end[0] - start[0], end[1] - start[1]
    length = hypot(dx, dy) or 1.0
    return (-dy / length * sign, dx / length * sign)


@cache
def inset(shape: ShieldShape, distance: float) -> tuple[Point, ...]:
    points = outline_of(shape)
    sign = 1.0 if signed_area(points) > 0 else -1.0
    moved: list[Point] = []
    for index, point in enumerate(points):
        before, after = points[index - 1], points[(index + 1) % len(points)]
        first, second = inward(before, point, sign), inward(point, after, sign)
        mx, my = first[0] + second[0], first[1] + second[1]
        length = hypot(mx, my)
        mx, my = (mx / length, my / length) if length > 1e-6 else first
        reach = distance / max(0.35, mx * first[0] + my * first[1])
        moved.append((point[0] + mx * reach, point[1] + my * reach))
    return tuple(moved)


def scaled(points: tuple[Point, ...], factor: float, centre: Point) -> tuple[Point, ...]:
    return tuple((centre[0] + (x - centre[0]) * factor, centre[1] + (y - centre[1]) * factor) for x, y in points)


def sine(count: int = 12) -> tuple[Point, ...]:
    return tuple((k / count, sin(2 * pi * k / count)) for k in range(count + 1))


def bump(sign: float, count: int = 10) -> tuple[Point, ...]:
    return tuple((k / count, sign * sqrt(max(0.0, 1 - (2 * k / count - 1) ** 2))) for k in range(count + 1))


def cloud(count: int = 24) -> tuple[Point, ...]:
    return tuple((t - 0.12 * sin(4 * pi * t), sin(2 * pi * t)) for t in (k / count for k in range(count + 1)))


ZIGZAG = ((0.0, 0.0), (0.25, 1.0), (0.75, -1.0), (1.0, 0.0))
PROFILES: Mapping[PartitionLine, tuple[float, float, tuple[Point, ...]]] = partial(
    PartitionLine,
    {
        L.WAVY: (16.0, 3.0, sine()),
        L.INDENTED: (7.0, 2.4, ZIGZAG),
        L.DANCETTY: (26.0, 6.0, ZIGZAG),
        L.ENGRAILED: (11.0, 3.0, bump(-1.0)),
        L.INVECTED: (11.0, 3.0, bump(1.0)),
        L.EMBATTLED: (13.0, 3.2, ((0.0, 0.0), (0.0, -1.0), (0.5, -1.0), (0.5, 1.0), (1.0, 1.0), (1.0, 0.0))),
        L.NEBULY: (15.0, 3.4, cloud()),
        L.RAGULY: (13.0, 3.2, ((0.0, 0.0), (0.0, -1.0), (0.3, -1.0), (0.45, 1.0), (0.8, 1.0), (0.65, -1.0), (1.0, -1.0), (1.0, 0.0))),
        L.DOVETAILED: (14.0, 3.0, ((0.0, 0.0), (0.0, -1.0), (0.3, -1.0), (0.2, 1.0), (0.8, 1.0), (0.7, -1.0), (1.0, -1.0), (1.0, 0.0))),
    },
    without=(L.STRAIGHT,),
)


class Track:
    def __init__(self, points: list[Point]) -> None:
        self.points = points
        self.marks = [0.0]
        for start, end in pairwise(points):
            self.marks.append(self.marks[-1] + hypot(end[0] - start[0], end[1] - start[1]))
        self.length = self.marks[-1]

    def at(self, distance: float) -> tuple[Point, Point]:
        distance = min(max(distance, 0.0), self.length)
        index = min(max(bisect_right(self.marks, distance) - 1, 0), len(self.points) - 2)
        start, end = self.points[index], self.points[index + 1]
        span = (self.marks[index + 1] - self.marks[index]) or 1.0
        t = (distance - self.marks[index]) / span
        dx, dy = end[0] - start[0], end[1] - start[1]
        length = hypot(dx, dy) or 1.0
        return (start[0] + dx * t, start[1] + dy * t), (-dy / length, dx / length)


def along(points: list[Point], line: PartitionLine, scale: float = 1.0) -> list[Point]:
    period, amplitude, profile = PROFILES[line]
    track = Track(points)
    count = max(1, round(track.length / (period * scale)))
    step = track.length / count
    found: list[Point] = [points[0]]
    for k in range(count):
        for u, h in profile[1:]:
            spot, normal = track.at((k + u) * step)
            found.append(add(spot, normal, h * amplitude * scale))
    return found


def hidden(start: Point, end: Point) -> bool:
    return (start[0] < 4 and end[0] < 4) or (start[0] > 116 and end[0] > 116) or (start[1] < 2 and end[1] < 2) or (start[1] > 130 and end[1] > 130)


def styled(loop: Loop, line: PartitionLine, scale: float = 1.0) -> list[Point]:
    points, curved = loop
    if line is L.STRAIGHT:
        return list(points)
    if curved:
        return along([*points, points[0]], line, scale)[:-1]
    found: list[Point] = []
    for index, start in enumerate(points):
        end = points[(index + 1) % len(points)]
        found.extend([end] if hidden(start, end) else along([start, end], line, scale)[1:])
    return found


def meet(first: Point, towards: Point, second: Point, along_second: Point) -> Point:
    cross = towards[0] * along_second[1] - towards[1] * along_second[0]
    if abs(cross) < 1e-9:
        return first
    gap = (second[0] - first[0], second[1] - first[1])
    t = (gap[0] * along_second[1] - gap[1] * along_second[0]) / cross
    return add(first, towards, t)


def half_plane(origin: Point, direction: Point, side: Point) -> Loop:
    start, end = add(origin, direction, -FAR), add(origin, direction, FAR)
    return ((start, end, add(end, side, FAR), add(start, side, FAR)), False)


def band(origin: Point, direction: Point, half: float) -> Loop:
    normal = (-direction[1], direction[0])
    left, right = add(origin, normal, half), add(origin, normal, -half)
    return ((add(left, direction, -FAR), add(left, direction, FAR), add(right, direction, FAR), add(right, direction, -FAR)), False)


def crossing(centre: Point, directions: list[Point], half: float) -> Loop:
    ordered = sorted(directions, key=lambda vector: atan2(vector[1], vector[0]))
    points: list[Point] = []
    for index, direction in enumerate(ordered):
        following = ordered[(index + 1) % len(ordered)]
        normal, next_normal = (-direction[1], direction[0]), (-following[1], following[0])
        points.append(add(add(centre, normal, -half), direction, FAR))
        points.append(add(add(centre, normal, half), direction, FAR))
        points.append(meet(add(centre, normal, half), direction, add(centre, next_normal, -half), following))
    return (tuple(points), False)


def chevron_band(top: Point, bottom: Point, left: Point, right: Point) -> Loop:
    return ((add(top, left, FAR), top, add(top, right, FAR), add(bottom, right, FAR), bottom, add(bottom, left, FAR)), False)


def mirrored(loops: list[Loop]) -> list[Loop]:
    return [(tuple((120 - x, y) for x, y in points), curved) for points, curved in loops]


BEND = unit(100, 116)
SINISTER = (-BEND[0], BEND[1])
TOP_LEFT, TOP_RIGHT = unit(-50, -54), unit(50, -54)
DOWN_LEFT, DOWN_RIGHT = unit(-1, 1.1), unit(1, 1.1)


def stripes() -> list[Loop]:
    normal = (BEND[1], -BEND[0])
    width = 15.0
    found: list[Loop] = []
    for k in range(-9, 9, 2):
        near, far = add(CENTRE, normal, k * width), add(CENTRE, normal, (k + 1) * width)
        found.append(((add(near, BEND, -FAR), add(near, BEND, FAR), add(far, BEND, FAR), add(far, BEND, -FAR)), False))
    return found


def per_chevron(_: ShieldShape) -> tuple[Loop, ...]:
    apex = (60.0, 46.0)
    right, left = add(apex, DOWN_RIGHT, FAR), add(apex, DOWN_LEFT, FAR)
    return (((apex, right, add(right, (0, 1), FAR), add(left, (0, 1), FAR), left), False),)


def per_chevron_inverted(_: ShieldShape) -> tuple[Loop, ...]:
    apex = (60.0, 84.0)
    return (((apex, add(apex, (DOWN_RIGHT[0], -DOWN_RIGHT[1]), FAR), add(apex, (DOWN_LEFT[0], -DOWN_LEFT[1]), FAR)), False),)


def per_saltire(_: ShieldShape) -> tuple[Loop, ...]:
    top = (CENTRE, add(CENTRE, TOP_LEFT, FAR), add(CENTRE, TOP_RIGHT, FAR))
    bottom = (CENTRE, add(CENTRE, TOP_LEFT, -FAR), add(CENTRE, TOP_RIGHT, -FAR))
    return ((top, False), (bottom, False))


def gyronny(_: ShieldShape) -> tuple[Loop, ...]:
    angles = [radians(-90 + 45 * k) for k in range(0, 8, 2)]
    return tuple(
        ((CENTRE, add(CENTRE, (cos(angle), sin(angle)), FAR), add(CENTRE, (cos(angle + pi / 4), sin(angle + pi / 4)), FAR)), False) for angle in angles
    )


def paly(_: ShieldShape) -> tuple[Loop, ...]:
    width = 100 / 6
    return tuple(rect(10 + i * width, -20, 10 + (i + 1) * width, 150) for i in (1, 3, 5))


def barry(_: ShieldShape) -> tuple[Loop, ...]:
    height = 116 / 6
    return tuple(rect(-20, 8 + i * height, 140, 8 + (i + 1) * height) for i in (1, 3, 5))


def chequy(_: ShieldShape) -> tuple[Loop, ...]:
    side = 100 / 6
    return tuple(rect(10 + i * side, 8 + j * side, 10 + (i + 1) * side, 8 + (j + 1) * side) for i in range(6) for j in range(7) if (i + j) % 2)


def lozengy(_: ShieldShape) -> tuple[Loop, ...]:
    return tuple((((cx, cy - 13), (cx + 10, cy), (cx, cy + 13), (cx - 10, cy)), False) for cx in range(10, 120, 20) for cy in range(8, 140, 26))


def pily(_: ShieldShape) -> tuple[Loop, ...]:
    width = 100 / 3
    return tuple((((10 + i * width, -20), (10 + (i + 1) * width, -20), (10 + (i + 0.5) * width, 112)), False) for i in range(3))


def chevronny(_: ShieldShape) -> tuple[Loop, ...]:
    return tuple(chevron_band((60, top), (60, top + 13), unit(-1, 1), unit(1, 1)) for top in range(-80, 130, 26))


SALTIRE_ARMS = [TOP_LEFT, TOP_RIGHT, (-TOP_LEFT[0], -TOP_LEFT[1]), (-TOP_RIGHT[0], -TOP_RIGHT[1])]
REGIONS: Mapping[HeraldicDivision, Callable[[ShieldShape], tuple[Loop, ...]]] = total(
    HeraldicDivision,
    {
        D.PLAIN: lambda _: (),
        D.PER_PALE: lambda _: (rect(60, -20, 140, 150),),
        D.PER_FESS: lambda _: (rect(-20, 62, 140, 150),),
        D.PER_BEND: lambda _: (half_plane(CENTRE, BEND, (-BEND[1], BEND[0])),),
        D.PER_BEND_SINISTER: lambda _: (half_plane(CENTRE, SINISTER, (SINISTER[1], -SINISTER[0])),),
        D.PER_CHEVRON: per_chevron,
        D.PER_CHEVRON_INVERTED: per_chevron_inverted,
        D.PER_SALTIRE: per_saltire,
        D.QUARTERLY: lambda _: (rect(60, -20, 140, 62), rect(-20, 62, 60, 150)),
        D.GYRONNY: gyronny,
        D.PALY: paly,
        D.BARRY: barry,
        D.BENDY: lambda _: tuple(stripes()),
        D.BENDY_SINISTER: lambda _: tuple(mirrored(stripes())),
        D.CHEQUY: chequy,
        D.LOZENGY: lozengy,
        D.PILY: pily,
        D.CHEVRONNY: chevronny,
        D.CHIEF: lambda _: (rect(-20, -20, 140, 38),),
        D.BASE: lambda _: (rect(-20, 98, 140, 150),),
        D.PALE: lambda _: (rect(44, -20, 76, 150),),
        D.FESS: lambda _: (rect(-20, 48, 140, 78),),
        D.BARS: lambda _: (rect(-20, 40, 140, 53), rect(-20, 71, 140, 84)),
        D.BEND: lambda _: (band(CENTRE, BEND, 14),),
        D.BEND_SINISTER: lambda _: (band(CENTRE, SINISTER, 14),),
        D.CROSS: lambda _: (crossing((60, 58), [(0, -1), (1, 0), (0, 1), (-1, 0)], 13),),
        D.SALTIRE: lambda _: (crossing(CENTRE, SALTIRE_ARMS, 11),),
        D.PALL: lambda _: (crossing((60, 56), [unit(-50, -48), unit(50, -48), (0, 1)], 11),),
        D.CHEVRON: lambda _: (chevron_band((60, 34), (60, 58), unit(-1, 1), unit(1, 1)),),
        D.PILE: lambda _: ((((32, -20), (88, -20), (60, 112)), False),),
        D.CANTON: lambda _: (rect(-20, -20, 50, 46),),
        D.FLAUNCHES: lambda _: ((ellipse(-34, 66, 60, 60), True), (ellipse(154, 66, 60, 60), True)),
        D.BORDURE: lambda shape: (rect(-20, -20, 140, 150), (inset(shape, 11), True)),
        D.ORLE: lambda shape: ((inset(shape, 13), True), (inset(shape, 21), True)),
        D.INESCUTCHEON: lambda shape: ((scaled(outline_of(shape), 0.42, (60, 64)), True),),
    },
)
RINGED = frozenset({D.BORDURE, D.ORLE})
UNSTYLED = frozenset({D.PLAIN, D.CHEQUY, D.LOZENGY, D.GYRONNY})


@cache
def regions(division: HeraldicDivision, shape: ShieldShape) -> tuple[tuple[Loop, ...], bool]:
    return (REGIONS[division](shape), division in RINGED)


def region_path(design: Design) -> str:
    loops, _ = regions(design.division, design.shape)
    line = L.STRAIGHT if design.division in UNSTYLED else design.line
    return "".join(path(styled(loop, line)) for loop in loops)


def inside(points: tuple[Point, ...], spot: Point) -> bool:
    found = False
    x, y = spot
    for index, (x1, y1) in enumerate(points):
        x2, y2 = points[index - 1]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / ((y2 - y1) or 1e-9) + x1:
            found = not found
    return found


def in_second(design: Design, spot: Point) -> bool:
    loops, _ = regions(design.division, design.shape)
    return sum(inside(points, spot) for points, _ in loops) % 2 == 1


def zone(design: Design) -> Box:
    base = SHAPE_ZONES[design.shape]
    override = DIVISION_ZONES.get(design.division)
    if override is None:
        return base
    chosen = tuple(base[k] if value is None else value for k, value in enumerate(override))
    return (max(chosen[0], base[0]), max(chosen[1], base[1]), min(chosen[2], base[2]), min(chosen[3], base[3]))


def effective(arrangement: ChargeArrangement, count: int) -> ChargeArrangement:
    if count == 2 and arrangement is A.TWO_AND_ONE:
        return A.IN_FESS
    if count == 2 and arrangement is A.ONE_AND_TWO:
        return A.IN_PALE
    return arrangement


Slot = tuple[float, float, float]


def in_pale(box: Box, count: int) -> list[Slot]:
    x0, y0, x1, y1 = box
    size = min((x1 - x0) * 0.62, (y1 - y0) / count * 0.84)
    return [((x0 + x1) / 2, y0 + (y1 - y0) * (k + 0.5) / count, size) for k in range(count)]


def in_fess(box: Box, count: int) -> list[Slot]:
    x0, y0, x1, y1 = box
    size = min((y1 - y0) * 0.62, (x1 - x0) / count * 0.84)
    return [(x0 + (x1 - x0) * (k + 0.5) / count, (y0 + y1) / 2, size) for k in range(count)]


def triangle_of(box: Box, top: tuple[float, ...], bottom: tuple[float, ...]) -> list[Slot]:
    x0, y0, x1, y1 = box
    width, height = x1 - x0, y1 - y0
    size = min(width, height) * 0.38
    return [(x0 + width * u, y0 + height * 0.27, size) for u in top] + [(x0 + width * u, y0 + height * 0.73, size) for u in bottom]


def diagonal(box: Box, count: int, sinister: bool) -> list[Slot]:
    x0, y0, x1, y1 = box
    width, height = x1 - x0, y1 - y0
    first, last = (0.78, 0.22) if sinister else (0.22, 0.78)
    size = min(width, height) * (0.42 if count == 2 else 0.32)
    return [(x0 + width * (first + (last - first) * (k + 0.5) / count), y0 + height * (0.2 + 0.6 * (k + 0.5) / count), size) for k in range(count)]


def in_chief(shape: ShieldShape, count: int) -> list[Slot]:
    x0, y0, x1, _ = SHAPE_ZONES[shape]
    span = x1 - x0
    size = min(22.0, span / count * 0.8)
    return [(x0 + span * (k + 0.5) / count, y0 + 6, size) for k in range(count)]


ARRANGERS: Mapping[ChargeArrangement, Callable[[Box, int], list[Slot]]] = partial(
    ChargeArrangement,
    {
        A.IN_PALE: in_pale,
        A.IN_FESS: in_fess,
        A.TWO_AND_ONE: lambda box, _: triangle_of(box, (0.27, 0.73), (0.5,)),
        A.ONE_AND_TWO: lambda box, _: triangle_of(box, (0.5,), (0.27, 0.73)),
        A.IN_BEND: lambda box, count: diagonal(box, count, sinister=False),
        A.IN_BEND_SINISTER: lambda box, count: diagonal(box, count, sinister=True),
    },
    without=(A.IN_CHIEF,),
)


def slots(design: Design, count: int) -> list[Slot]:
    if count == 0:
        return []
    arrangement = effective(design.arrangement, count)
    if arrangement is A.IN_CHIEF:
        return in_chief(design.shape, count)
    x0, y0, x1, y1 = zone(design)
    if count == 1:
        return [((x0 + x1) / 2, (y0 + y1) / 2, min(56.0, min(x1 - x0, y1 - y0) * 0.66))]
    return ARRANGERS[arrangement]((x0, y0, x1, y1), count)


def beneath(design: Design, x: float, y: float, size: float) -> set[Tincture]:
    reach = size * 0.3
    spots = [(x, y), (x - reach, y), (x + reach, y), (x, y - reach), (x, y + reach)]
    second = design.second if design.second is not None else design.field
    return {second if in_second(design, spot) else design.field for spot in spots}


def partners(tincture: Tincture) -> list[Tincture]:
    if tincture in FUR_PARTNERS:
        return list(FUR_PARTNERS[tincture])
    return [other for other in SOLID_TINCTURES if abs(LIGHTNESS[other] - LIGHTNESS[tincture]) >= CONTRAST]


def against(under: set[Tincture]) -> list[Tincture]:
    common = [tincture for tincture in SOLID_TINCTURES if all(tincture in partners(below) for below in under)]
    return common


def contrasting(under: set[Tincture]) -> Tincture:
    common = against(under)
    if common:
        return max(common, key=lambda tincture: (min(abs(LIGHTNESS[tincture] - LIGHTNESS[below]) for below in under), tincture.value))
    darkest = min(LIGHTNESS[below] for below in under)
    return Tincture.SILVER if darkest < 0.5 else Tincture.BLACK


def ink(tincture: Tincture) -> ArmsInk:
    return ArmsInk(FUR_SOLIDS.get(tincture, tincture).value)


def circle(x: float, y: float, r: float) -> str:
    return f"M{num(x - r)} {num(y)}a{num(r)} {num(r)} 0 1 0 {num(2 * r)} 0a{num(r)} {num(r)} 0 1 0 {num(-2 * r)} 0Z"


def ermine_spot(x: float, y: float) -> str:
    tail = (
        f"M{num(x)} {num(y - 3.5)}C{num(x + 1.6)} {num(y - 0.5)} {num(x + 2.2)} {num(y + 2.2)} {num(x)} {num(y + 4.5)}"
        f"C{num(x - 2.2)} {num(y + 2.2)} {num(x - 1.6)} {num(y - 0.5)} {num(x)} {num(y - 3.5)}Z"
    )
    return tail + circle(x, y - 5.6, 1.1) + circle(x - 2.4, y - 4.2, 1.1) + circle(x + 2.4, y - 4.2, 1.1)


@cache
def fur_pattern(fur: Tincture) -> str:
    if fur is Tincture.VAIR:
        bells: list[str] = []
        for row in range(10):
            top = 4 + row * 14
            for column in range(-1, 11):
                x = column * 12 + (6 if row % 2 else 0)
                bells.append(path([(x, top + 14), (x + 3, top + 10), (x + 3, top + 4), (x + 6, top), (x + 9, top + 4), (x + 9, top + 10), (x + 12, top + 14)]))
        return "".join(bells)
    return "".join(ermine_spot(x + (7 if row % 2 else 0), 10 + row * 15) for row in range(9) for x in range(4, 124, 14))


def filling(d: str, tincture: Tincture, evenodd: bool) -> list[Layer]:
    if tincture not in FURS:
        return [Layer(d, ink(tincture), True, evenodd=evenodd)]
    base, spots = FURS[tincture]
    return [Layer(d, ink(base), True, evenodd=evenodd), Layer(fur_pattern(tincture), ink(spots), True, evenodd=evenodd, clip=d)]


@cache
def absolute(part: str) -> str:
    numbers = list(NUMBER.finditer(part[1:]))
    if part[0] != "m" or len(numbers) < 2:
        return part
    tail = part[1:][numbers[1].end() :].lstrip(" ,")
    return f"M{numbers[0].group()} {numbers[1].group()}" + ("l" + tail if tail and not tail[0].isalpha() else tail)


def glyph(charge: HeraldicCharge) -> str:
    return "".join(absolute(part) for part in GLYPHS[charge])


def placed(charge: HeraldicCharge, tincture: Tincture, spots: list[Placement], clipped: bool) -> list[Layer]:
    d = glyph(charge)
    if not d:
        return []
    layers: list[Layer] = []
    for x, y, size, turn, flip in spots:
        scale = size / 24
        transform = f"translate({num(x)} {num(y)}) rotate({num(turn)}) scale({num(-scale if flip else scale)} {num(scale)}) translate(-12 -12)"
        outer = min(3.6 * scale, BOLDEST) / scale
        layers.append(Layer(d, ArmsInk.LINE, False, round(outer, 3), transform=transform, clipped=clipped))
        layers.append(Layer(d, ink(tincture), False, round(outer * 0.56, 3), transform=transform, clipped=clipped))
    return layers


def charge_layers(design: Design) -> list[Layer]:
    shown = [(charge, tincture) for charge, tincture in design.charges if charge is not HeraldicCharge.NONE][:3]
    layers: list[Layer] = []
    for (charge, tincture), (x, y, size) in zip(shown, slots(design, len(shown)), strict=False):
        chosen = tincture if tincture is not None else contrasting(beneath(design, x, y, size))
        layers.extend(placed(charge, chosen, [(x, y, size, 0.0, False)], True))
    return layers


def poses(design: Design) -> list[Placement]:
    tilt = TILTS.get(design.supporter, 0.0)
    match design.pose:
        case SupporterPose.CROSSED:
            return [(60, 66, 166, 40 - tilt, False), (60, 66, 166, 40 - tilt, True)]
        case SupporterPose.BEHIND:
            return [(60, 66, 164, -tilt, False)]
        case SupporterPose.FLANKING:
            return [(-14, 72, 40, -tilt, False), (134, 72, 40, -tilt, True)]
        case SupporterPose.CORNERS:
            return [(1, 3, 20, 0, False), (119, 3, 20, 0, True), (5, 119, 20, 0, False), (115, 119, 20, 0, True)]


CREST: Placement = (60, -11, 30, 0, False)


def ornament_tincture(tincture: Tincture | None) -> Tincture:
    return tincture if tincture is not None else Tincture.GOLD


def beads(shape: ShieldShape, depth: float, gap: float, radius: float) -> str:
    track = Track([*inset(shape, depth), inset(shape, depth)[0]])
    count = max(1, round(track.length / gap))
    return "".join(circle(*track.at(track.length * k / count)[0], radius) for k in range(count))


def cords(shape: ShieldShape) -> str:
    near, far = Track([*inset(shape, 1.0), inset(shape, 1.0)[0]]), Track([*inset(shape, 6.0), inset(shape, 6.0)[0]])
    count = max(1, round(near.length / 3.2))
    return "".join(path([near.at(near.length * k / count)[0], far.at(far.length * (k + 0.8) / count)[0]], closed=False) for k in range(count))


def rim_layers(design: Design, outline: str) -> list[Layer]:
    shape = design.shape
    tincture = ink(ornament_tincture(design.rim_tincture))
    edge = Layer(outline, ArmsInk.LINE, False, 2.8, clipped=False)
    if design.rim is ArmsRim.LINE:
        return [Layer(outline, ArmsInk.LINE, False, 3.2, clipped=False)]
    depth = 6.0 if design.rim is ArmsRim.BAND else 7.0
    inner = path(inset(shape, depth))
    ring = outline + inner
    rim = [Layer(ring, ArmsInk.LINE if design.rim is ArmsRim.BEADED else tincture, True, evenodd=True)]
    if design.rim is ArmsRim.DOUBLE:
        rim.append(Layer(path(inset(shape, 3.5)), ArmsInk.LINE, False, 0.9))
    if design.rim is ArmsRim.BEADED:
        pearls = beads(shape, 3.5, 6.6, 1.9)
        rim += [Layer(pearls, tincture, True), Layer(pearls, ArmsInk.LINE, False, 0.5)]
    if design.rim is ArmsRim.STUDDED:
        rim.append(Layer(beads(shape, 3.5, 9.0, 1.25), ArmsInk.LINE, True))
    if design.rim is ArmsRim.ROPE:
        rim.append(Layer(cords(shape), ArmsInk.LINE, False, 0.9))
    return [*rim, Layer(inner, ArmsInk.LINE, False, 1.1), edge]


def bounds(design: Design, outline: tuple[Point, ...]) -> str:
    xs = [x for x, _ in outline]
    ys = [y for _, y in outline]
    boxes: list[Box] = [(min(xs) - 3, min(ys) - 3, max(xs) + 3, max(ys) + 3)]
    spots = (poses(design) if design.supporter is not HeraldicCharge.NONE else []) + ([CREST] if design.crest is not HeraldicCharge.NONE else [])
    for x, y, size, turn, _ in spots:
        half = size * 10.5 / 24
        reach = half * (abs(cos(radians(turn))) + abs(sin(radians(turn))))
        boxes.append((x - reach, y - reach, x + reach, y + reach))
    x0, y0 = min(box[0] for box in boxes), min(box[1] for box in boxes)
    x1, y1 = max(box[2] for box in boxes), max(box[3] for box in boxes)
    return f"{num(x0)} {num(y0)} {num(x1 - x0)} {num(y1 - y0)}"


def settled(design: Design) -> Design:
    shown = [(charge, tincture) for charge, tincture in design.charges if charge is not HeraldicCharge.NONE][:3]
    charges = tuple(
        (charge, tincture if tincture is not None else contrasting(beneath(design, x, y, size)))
        for (charge, tincture), (x, y, size) in zip(shown, slots(design, len(shown)), strict=False)
    )
    second = design.second if design.second is not None or design.division is D.PLAIN else contrasting({design.field})
    return replace(
        design,
        second=second,
        charges=charges,
        rim_tincture=ornament_tincture(design.rim_tincture),
        supporter_tincture=ornament_tincture(design.supporter_tincture),
        crest_tincture=ornament_tincture(design.crest_tincture),
    )


def draw(design: Design) -> Drawing:
    design = settled(design)
    shape = outline_of(design.shape)
    edge = styled((shape, True), design.rim_line, 0.6)
    outline = path(edge)
    behind: list[Layer] = []
    around: list[Layer] = []
    if design.supporter is not HeraldicCharge.NONE:
        spots = poses(design)
        layers = placed(design.supporter, ornament_tincture(design.supporter_tincture), spots, False)
        (behind if design.pose in {SupporterPose.CROSSED, SupporterPose.BEHIND} else around).extend(layers)
    field = filling(outline, design.field, False)
    parted: list[Layer] = []
    if design.division is not D.PLAIN:
        d = region_path(design)
        _, evenodd = regions(design.division, design.shape)
        second = design.second if design.second is not None else contrasting({design.field})
        parted = [*filling(d, second, evenodd), Layer(d, ArmsInk.LINE, False, 1.0, evenodd=evenodd)]
    depth = Layer(path(inset(design.shape, 1.6)), ArmsInk.BLACK, False, 2.2, opacity=0.14)
    crest = placed(design.crest, ornament_tincture(design.crest_tincture), [CREST], False) if design.crest is not HeraldicCharge.NONE else []
    layers = [*behind, *field, *parted, *charge_layers(design), depth, *rim_layers(design, outline), *around, *crest]
    return Drawing(view_box=bounds(design, tuple(edge)), outline=outline, layers=tuple(layers))
