import hashlib
import math
from collections.abc import Callable, Sequence

from aerona.domain.enums.cosmography import ClusterKind

GOLDEN_ANGLE = math.pi * (3 - math.sqrt(5))
LAYOUT_SCALE = 6.0
SATELLITE_SPREAD = 0.8
KNOT_SPREAD = 0.6
SHEET_SQUASH = 0.35
VOID_FIRST_RING = 2
VOID_RING_SIZE = 8
FILAMENT_WAVE = 0.35
FILAMENT_WAVE_STEP = 0.9
SUPERCLUSTER_REACH = 1.6
SUPERCLUSTER_CLUMP_SPREAD = 0.85
COMPACT_SPREAD = 0.75
WIDE_SPREAD = 1.4
WALL_SPREAD = 1.6
CROWN_ARC_SIZE = 7
CROWN_ARC_HALF = 1.1
CROWN_ARC_STEP = 1.0
FORGE_RING_SIZE = 6
FORGE_RING_STEP = 0.9
DREAM_START = 0.8
DREAM_ARM_GAP = 1.3
MIRROR_CENTRE = -0.22
MIRROR_SPREAD = 0.18
MIRROR_SEAM = -0.1
JITTER_RADIAL = 0.3
JITTER_ANGULAR = 0.35
DEFAULT_SCATTER = 0.2

GALAXY_GROUP_HOSTS = ((-0.18, -0.1), (0.2, 0.05), (-0.02, 0.24))
LOCAL_GROUP_HOSTS = ((-0.24, -0.06), (0.26, 0.1))
POOR_CLUSTER_HOSTS = ((0.0, 0.0), (-0.3, -0.25), (0.28, -0.3), (0.32, 0.22), (-0.25, 0.3))
SUPERCLUSTER_HOSTS = ((-0.3, -0.22), (0.28, -0.18), (-0.05, 0.28), (0.34, 0.3))

SCATTER: dict[ClusterKind, float] = {
    ClusterKind.FILAMENT: 0.12,
    ClusterKind.WALL: 0.2,
    ClusterKind.VOID: 0.1,
    ClusterKind.CROWN_CLUSTER: 0.0,
    ClusterKind.FORGE_CLUSTER: 0.0,
    ClusterKind.DREAM_CLUSTER: 0.1,
    ClusterKind.MIRROR_CLUSTER: 0.0,
}

MIN_GAP = 0.7
NUDGE_ROUNDS = 40
OUTWARD_ATTEMPTS = 12
OUTWARD_STEP = 0.3
CLEAR_TOLERANCE = 0.999

Point = tuple[float, float]
Arrangement = Callable[[ClusterKind, int, float], Point]

PLACED: dict[tuple[ClusterKind, float], list[Point]] = {}


def noise(kind: ClusterKind, index: int, salt: str) -> float:
    digest = hashlib.blake2b(f"{kind.value}|{index}|{salt}".encode(), digest_size=8).digest()
    return int.from_bytes(digest, "little") / 2**64 * 2 - 1


def scatter_of(kind: ClusterKind) -> float:
    return SCATTER.get(kind, DEFAULT_SCATTER)


def candidate(kind: ClusterKind, index: int, spacing: float) -> Point:
    x, y = arranged(kind, index, spacing)
    reach = scatter_of(kind) * spacing
    return x + noise(kind, index, "x") * reach, y + noise(kind, index, "y") * reach


def nudged(kind: ClusterKind, index: int, start: Point, gap: float, placed: Sequence[Point]) -> Point:
    x, y = start
    for _ in range(NUDGE_ROUNDS):
        moved = False
        for px, py in placed:
            dx, dy = x - px, y - py
            distance = math.hypot(dx, dy)
            if distance >= gap:
                continue
            if distance < gap * 1e-6:
                dx, dy, distance = (*polar(1.0, math.pi * (1 + noise(kind, index, "nudge"))), 1.0)
            x += dx * (gap - distance) / distance
            y += dy * (gap - distance) / distance
            moved = True
        if kind is ClusterKind.MIRROR_CLUSTER and x > -gap / 2:
            x = -gap / 2
            moved = True
        if not moved:
            break
    return x, y


def clear_of(point: Point, gap: float, placed: Sequence[Point]) -> bool:
    return all(math.hypot(point[0] - px, point[1] - py) >= gap * CLEAR_TOLERANCE for px, py in placed)


def kept_apart(kind: ClusterKind, index: int, spacing: float, placed: Sequence[Point]) -> Point:
    if kind is ClusterKind.MIRROR_CLUSTER and index % 2:
        x, y = placed[index - 1]
        return -x, y
    gap = MIN_GAP * spacing
    x, y = candidate(kind, index, spacing)
    point = (x, y)
    for attempt in range(OUTWARD_ATTEMPTS):
        reach = 1 + OUTWARD_STEP * attempt
        point = nudged(kind, index, (x * reach, y * reach), gap, placed)
        if clear_of(point, gap, placed):
            return point
    return point


def slot(kind: ClusterKind, index: int, spacing: float) -> Point:
    placed = PLACED.setdefault((kind, spacing), [])
    while len(placed) <= index:
        placed.append(kept_apart(kind, len(placed), spacing, placed))
    return placed[index]


def disc(kind: ClusterKind, index: int, spread: float, turn: float = 0.0) -> Point:
    radius = spread * math.sqrt(index + 0.5) * (1 + JITTER_RADIAL * noise(kind, index, "r"))
    angle = index * GOLDEN_ANGLE + turn + JITTER_ANGULAR * noise(kind, index, "a")
    return radius * math.cos(angle), radius * math.sin(angle)


def spread(index: int, spacing: float) -> Point:
    if index == 0:
        return 0.0, 0.0
    return polar(spacing * math.sqrt(index + 0.5), index * GOLDEN_ANGLE)


def polar(radius: float, angle: float) -> Point:
    return radius * math.cos(angle), radius * math.sin(angle)


def hosted(kind: ClusterKind, index: int, spacing: float, hosts: Sequence[Point], spread: float = SATELLITE_SPREAD) -> Point:
    scale = spacing * LAYOUT_SCALE
    if index < len(hosts):
        hx, hy = hosts[index]
        return hx * scale, hy * scale
    order, host = divmod(index - len(hosts), len(hosts))
    hx, hy = hosts[host]
    sx, sy = disc(kind, order, spacing * spread, host * GOLDEN_ANGLE)
    return hx * scale + sx, hy * scale + sy


def filament(_kind: ClusterKind, index: int, spacing: float) -> Point:
    step = (index + 1) // 2 * (1 if index % 2 else -1)
    return step * spacing, FILAMENT_WAVE * spacing * math.sin(step * FILAMENT_WAVE_STEP)


def wall(kind: ClusterKind, index: int, spacing: float) -> Point:
    x, y = disc(kind, index, spacing * WALL_SPREAD)
    return x, y * SHEET_SQUASH


def void(_kind: ClusterKind, index: int, spacing: float) -> Point:
    ring, place = divmod(index, VOID_RING_SIZE)
    return polar(spacing * (VOID_FIRST_RING + ring), place * math.tau / VOID_RING_SIZE + ring * math.pi / VOID_RING_SIZE)


def rich(kind: ClusterKind, index: int, spacing: float) -> Point:
    if index == 0:
        return 0.0, 0.0
    return disc(kind, index - 1, spacing * COMPACT_SPREAD)


def crown(_kind: ClusterKind, index: int, spacing: float) -> Point:
    if index == 0:
        return 0.0, 0.0
    arc, place = divmod(index - 1, CROWN_ARC_SIZE)
    middle = (CROWN_ARC_SIZE - 1) / 2
    angle = -math.pi / 2 + (place - middle) / middle * CROWN_ARC_HALF
    reach = spacing * middle / CROWN_ARC_HALF
    return polar(reach + arc * spacing * CROWN_ARC_STEP, angle)


def forge(_kind: ClusterKind, index: int, spacing: float) -> Point:
    if index == 0:
        return 0.0, 0.0
    ring, place = divmod(index - 1, FORGE_RING_SIZE)
    angle = place * math.tau / FORGE_RING_SIZE + ring * math.pi / FORGE_RING_SIZE
    return polar(spacing * (1 + ring * FORGE_RING_STEP), angle)


def dream(_kind: ClusterKind, index: int, spacing: float) -> Point:
    growth = spacing * DREAM_ARM_GAP / math.tau
    angle = 0.0
    radius = spacing * DREAM_START
    for _ in range(index):
        angle += spacing / radius
        radius = spacing * DREAM_START + growth * angle
    return polar(radius, angle)


def mirror(kind: ClusterKind, index: int, spacing: float) -> Point:
    pair, side = divmod(index, 2)
    scale = spacing * LAYOUT_SCALE
    dx, dy = disc(kind, pair, scale * MIRROR_SPREAD / 2)
    x = min(MIRROR_CENTRE * scale + dx, MIRROR_SEAM * scale)
    return (-x if side else x), dy


ARRANGEMENTS: dict[ClusterKind, Arrangement] = {
    ClusterKind.GALAXY_GROUP: lambda kind, index, spacing: hosted(kind, index, spacing, GALAXY_GROUP_HOSTS),
    ClusterKind.LOCAL_GROUP: lambda kind, index, spacing: hosted(kind, index, spacing, LOCAL_GROUP_HOSTS),
    ClusterKind.POOR_CLUSTER: lambda kind, index, spacing: hosted(kind, index, spacing, POOR_CLUSTER_HOSTS, KNOT_SPREAD),
    ClusterKind.RICH_CLUSTER: rich,
    ClusterKind.SUPERCLUSTER: lambda kind, index, spacing: hosted(
        kind, index, spacing * SUPERCLUSTER_REACH, SUPERCLUSTER_HOSTS, SUPERCLUSTER_CLUMP_SPREAD / SUPERCLUSTER_REACH
    ),
    ClusterKind.FILAMENT: filament,
    ClusterKind.WALL: wall,
    ClusterKind.VOID: void,
    ClusterKind.CROWN_CLUSTER: crown,
    ClusterKind.DROWNED_CLUSTER: lambda kind, index, spacing: disc(kind, index, spacing * WIDE_SPREAD),
    ClusterKind.FORGE_CLUSTER: forge,
    ClusterKind.DREAM_CLUSTER: dream,
    ClusterKind.MIRROR_CLUSTER: mirror,
}


def arranged(kind: ClusterKind, index: int, spacing: float) -> Point:
    return ARRANGEMENTS[kind](kind, index, spacing)
