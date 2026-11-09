import math
import random
from dataclasses import dataclass

from markupsafe import Markup

from aerona.catalog.cosmography import BARRED_GALAXIES, SPIRAL_GALAXIES
from aerona.constants.units import PERCENT
from aerona.db.tables.cosmography import ClusterRow, DimensionRow, GalacticStructureRow, GalaxyRow
from aerona.domain.enums.cosmography import (
    ClusterKind,
    DimensionKind,
    GalacticNucleus,
    GalacticStructureKind,
    GalaxyAge,
    GalaxyType,
)
from aerona.rules.registry.cosmography import GalaxyRules

VOID = "#0d0620"
VOID_EDGE = "#1a0d38"
CORE = "#ffe9c2"
BULGE = "#ffd49a"
YOUNG = "#a8c8ff"
OLD = "#ffbf86"
DISC = "#d9d4ff"
NURSERY = "#ff7ab8"
HALO = "#6f7fb8"
STAR = "#fdca26"

FAMILY: dict[GalaxyType, str] = {
    GalaxyType.SPIRAL: "spiral",
    GalaxyType.BARRED_SPIRAL: "spiral",
    GalaxyType.GRAND_DESIGN_SPIRAL: "spiral",
    GalaxyType.FLOCCULENT_SPIRAL: "spiral",
    GalaxyType.LENTICULAR: "lenticular",
    GalaxyType.ELLIPTICAL: "elliptical",
    GalaxyType.GIANT_ELLIPTICAL: "elliptical",
    GalaxyType.DWARF_ELLIPTICAL: "elliptical",
    GalaxyType.DWARF_SPHEROIDAL: "elliptical",
    GalaxyType.IRREGULAR: "irregular",
    GalaxyType.DWARF_IRREGULAR: "irregular",
    GalaxyType.RING: "ring",
    GalaxyType.PECULIAR: "irregular",
    GalaxyType.STARBURST: "irregular",
    GalaxyType.ACTIVE: "spiral",
    GalaxyType.QUASAR_HOST: "elliptical",
    GalaxyType.LOW_SURFACE_BRIGHTNESS: "spiral",
    GalaxyType.ULTRA_DIFFUSE: "elliptical",
    GalaxyType.LIVING: "spiral",
    GalaxyType.DEAD: "elliptical",
    GalaxyType.SHATTERED: "irregular",
    GalaxyType.FORGED: "spiral",
    GalaxyType.DREAMING: "spiral",
    GalaxyType.MIRROR: "spiral",
    GalaxyType.CROWNED: "spiral",
    GalaxyType.HOLLOW: "ring",
    GalaxyType.EMBER: "spiral",
    GalaxyType.VEILED: "spiral",
}

ARM_INK: dict[GalaxyType, str] = {
    GalaxyType.LIVING: "#8ff0a8",
    GalaxyType.DEAD: "#8f8580",
    GalaxyType.EMBER: "#ff7a3a",
    GalaxyType.FORGED: "#ffcc55",
    GalaxyType.DREAMING: "#c8a0ff",
    GalaxyType.MIRROR: "#e4ecf8",
    GalaxyType.CROWNED: "#ffe680",
    GalaxyType.VEILED: "#7a68a8",
    GalaxyType.HOLLOW: "#8fd8ff",
    GalaxyType.SHATTERED: "#ff9c7a",
    GalaxyType.STARBURST: NURSERY,
}

AGE_LIGHT: dict[GalaxyAge, float] = {
    GalaxyAge.FORMING: 0.95,
    GalaxyAge.YOUNG: 1.05,
    GalaxyAge.MATURE: 1.0,
    GalaxyAge.OLD: 0.85,
    GalaxyAge.DYING: 0.65,
    GalaxyAge.DEAD: 0.4,
}

CORE_LIGHT: dict[GalacticNucleus, float] = {
    GalacticNucleus.NONE: 0.5,
    GalacticNucleus.DORMANT: 1.0,
    GalacticNucleus.ACTIVE: 1.4,
    GalacticNucleus.QUASAR: 1.8,
    GalacticNucleus.DEVOURED: 0.2,
}

STRUCTURE_INK: dict[GalacticStructureKind, str] = {
    GalacticStructureKind.SPIRAL_ARM: YOUNG,
    GalacticStructureKind.BAR: BULGE,
    GalacticStructureKind.BULGE: BULGE,
    GalacticStructureKind.CORE: CORE,
    GalacticStructureKind.HALO: HALO,
    GalacticStructureKind.EMISSION_NEBULA: "#ff6a8a",
    GalacticStructureKind.REFLECTION_NEBULA: "#7aa8ff",
    GalacticStructureKind.DARK_NEBULA: "#140b1e",
    GalacticStructureKind.PLANETARY_NEBULA: "#6ae0d0",
    GalacticStructureKind.SUPERNOVA_REMNANT: "#ff9a5a",
    GalacticStructureKind.STELLAR_NURSERY: NURSERY,
    GalacticStructureKind.OPEN_CLUSTER: "#d4e2ff",
    GalacticStructureKind.GLOBULAR_CLUSTER: "#ffe2b0",
    GalacticStructureKind.STELLAR_STREAM: "#b4ccff",
    GalacticStructureKind.DUST_LANE: "#140b1e",
    GalacticStructureKind.SUPERBUBBLE: "#ffb4dc",
    GalacticStructureKind.STAR_GRAVEYARD: "#9e94a2",
    GalacticStructureKind.LEY_SPIRAL: "#8af0d0",
    GalacticStructureKind.SEALED_VAULT: "#d8b060",
    GalacticStructureKind.GODS_FORGE: "#ffb040",
    GalacticStructureKind.DEAD_LIGHT_DRIFT: "#8a80a6",
    GalacticStructureKind.SINGING_NEBULA: "#c4a4ff",
    GalacticStructureKind.RIFT_SCAR: "#e46aa0",
}

LAYOUT_KINDS = frozenset(
    {
        GalacticStructureKind.SPIRAL_ARM,
        GalacticStructureKind.BAR,
        GalacticStructureKind.BULGE,
        GalacticStructureKind.CORE,
        GalacticStructureKind.HALO,
    }
)

DIMENSION_INK: dict[DimensionKind, str] = {
    DimensionKind.PRIME: "#9cc4ff",
    DimensionKind.PARALLEL: "#7ab0ff",
    DimensionKind.MIRROR: "#e4ecf8",
    DimensionKind.POCKET: "#7ab0ff",
    DimensionKind.BUBBLE_UNIVERSE: "#7ab0ff",
    DimensionKind.BRANE: "#7ab0ff",
    DimensionKind.HIGHER_DIMENSIONAL: "#b88cff",
    DimensionKind.ANTIMATTER: "#ff6ad0",
    DimensionKind.QUANTUM_BRANCH: "#7ab0ff",
    DimensionKind.TIME_REVERSED: "#e4ecf8",
    DimensionKind.COMPACTIFIED: "#9aa2b4",
    DimensionKind.ASTRAL: "#b88cff",
    DimensionKind.ETHEREAL: "#8ff0d0",
    DimensionKind.DREAM: "#d0a8ff",
    DimensionKind.SHADOW: "#6a5a8e",
    DimensionKind.SPIRIT: "#8ff0d0",
    DimensionKind.FEY: "#8ff0a8",
    DimensionKind.ELEMENTAL: "#ff9a5a",
    DimensionKind.CELESTIAL: "#ffe680",
    DimensionKind.INFERNAL: "#ff5a3a",
    DimensionKind.ABYSSAL: "#b0306a",
    DimensionKind.LIMBO: "#9aa2b4",
    DimensionKind.FAR_REALM: "#e46aa0",
    DimensionKind.CLOCKWORK: "#d8b060",
    DimensionKind.CHAOS: "#ff6ad0",
    DimensionKind.UNDERWORLD: "#7a6aa0",
    DimensionKind.DIVINE_DOMAIN: "#ffd870",
    DimensionKind.VOID_BETWEEN: "#4a4068",
}

CLUSTER_SPREAD: dict[ClusterKind, str] = {
    ClusterKind.FILAMENT: "line",
    ClusterKind.MIRROR_CLUSTER: "line",
    ClusterKind.SUPERCLUSTER: "band",
    ClusterKind.WALL: "band",
    ClusterKind.VOID: "ring",
    ClusterKind.CROWN_CLUSTER: "ring",
}

SIZE = 320
POINTS = 1500
TILT = 0.55
DIGITS = 1


@dataclass(frozen=True)
class Point:
    x: float
    y: float
    radius: float
    ink: str
    alpha: float


def _number(value: float) -> str:
    return f"{round(value, DIGITS):g}"


def _frame(defs: str, body: str, label: str) -> Markup:
    half = SIZE / 2
    return Markup(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{-half} {-half} {SIZE} {SIZE}" role="img" aria-label="{label}">'
        f'<defs><radialGradient id="void"><stop offset="0" stop-color="{VOID_EDGE}"/><stop offset="1" stop-color="{VOID}"/></radialGradient>{defs}</defs>'
        f'<rect x="{-half}" y="{-half}" width="{SIZE}" height="{SIZE}" fill="url(#void)"/>{body}</svg>'
    )


def _glow(key: str, ink: str, centre: tuple[float, float], *, radius: float, strength: float) -> tuple[str, str]:
    x, y = centre
    gradient = (
        f'<radialGradient id="{key}"><stop offset="0" stop-color="{ink}" stop-opacity="{min(strength, 1):.2f}"/>'
        f'<stop offset="0.45" stop-color="{ink}" stop-opacity="{min(strength * 0.35, 1):.2f}"/>'
        f'<stop offset="1" stop-color="{ink}" stop-opacity="0"/></radialGradient>'
    )
    return gradient, f'<circle cx="{_number(x)}" cy="{_number(y)}" r="{_number(radius)}" fill="url(#{key})"/>'


def _galaxy_points(galaxy: GalaxyRow, rules: GalaxyRules) -> list[tuple[float, float, float, str, float]]:
    rng = random.Random(galaxy.id * 7919 + 17)
    family = FAMILY[galaxy.galaxy_type]
    arms_ink = ARM_INK.get(galaxy.galaxy_type, YOUNG)
    radius = max(galaxy.radius, 1.0)
    bulge = rules.bulge_reach_pct / PERCENT * radius
    disc = rules.disc_reach_pct / PERCENT * radius
    bar = rules.bar_reach_pct / PERCENT * radius
    wind = math.radians(rules.arm_wind_deg)
    width = math.radians(rules.arm_width_deg)
    arms = max(galaxy.arm_count, 2 if galaxy.galaxy_type is GalaxyType.GRAND_DESIGN_SPIRAL else 0)
    nursery = 0.06 * (0.4 + galaxy.star_formation / PERCENT * 1.6)
    found: list[tuple[float, float, float, str, float]] = []
    for _ in range(POINTS // 6):
        spread = radius * (0.36 if family == "elliptical" else 0.09)
        found.append((rng.gauss(0, spread), rng.gauss(0, spread * 0.6), 1.2, BULGE, 0.9))
    clumps = [(rng.uniform(-0.6, 0.6) * radius, rng.uniform(-0.6, 0.6) * radius) for _ in range(5)]
    while len(found) < POINTS:
        if family == "elliptical":
            x, z = rng.gauss(0, radius * 0.4), rng.gauss(0, radius * 0.3)
            found.append((x, z, 0.8, OLD, 0.5))
            continue
        if family == "irregular":
            cx, cz = rng.choice(clumps)
            found.append((cx + rng.gauss(0, radius * 0.12), cz + rng.gauss(0, radius * 0.12), 1.0, NURSERY if rng.random() < nursery * 2 else YOUNG, 0.7))
            continue
        if family == "ring":
            angle = rng.uniform(0, math.tau)
            distance = radius * (0.82 if galaxy.galaxy_type is GalaxyType.HOLLOW else 0.68) + rng.gauss(0, radius * 0.06)
            found.append((math.cos(angle) * distance, math.sin(angle) * distance, 1.0, arms_ink, 0.8))
            continue
        root = bar if galaxy.galaxy_type in BARRED_GALAXIES else bulge * 0.6
        distance = root + rng.random() ** 1.25 * (disc - root)
        angle = rng.uniform(0, math.tau)
        on_arm = galaxy.galaxy_type in SPIRAL_GALAXIES and arms > 0 and rng.random() < 0.72
        if on_arm:
            arm = rng.randrange(arms)
            angle = arm * math.tau / arms + distance / radius * wind + rng.gauss(0, width * 0.3)
        knot = on_arm and rng.random() < nursery
        found.append(
            (
                math.cos(angle) * distance,
                math.sin(angle) * distance,
                1.6 if knot else 0.9,
                NURSERY if knot else arms_ink if on_arm else DISC,
                0.85 if on_arm else 0.35,
            )
        )
    if galaxy.galaxy_type in BARRED_GALAXIES:
        found += [(rng.uniform(-bar, bar), rng.gauss(0, bar * 0.1), 1.0, BULGE, 0.8) for _ in range(POINTS // 12)]
    return found


def galaxy_figure(galaxy: GalaxyRow, structures: list[GalacticStructureRow], stars: list[tuple[float, float]], rules: GalaxyRules) -> Markup:
    radius = max(galaxy.radius, 1.0)
    scale = SIZE / 2 / (radius * rules.disc_reach_pct / PERCENT * 1.12)
    light = AGE_LIGHT[galaxy.age_stage]
    squash = math.cos(TILT)
    disc, haze = _glow(f"disc-{galaxy.id}", DISC, (0, 0), radius=SIZE / 2 * 0.95, strength=0.22 * light)
    defs: list[str] = [disc]
    body: list[str] = [haze]
    for index, structure in enumerate(row for row in structures if row.kind not in LAYOUT_KINDS and row.ended_epoch is None):
        gradient, circle = _glow(
            f"structure-{galaxy.id}-{index}",
            STRUCTURE_INK[structure.kind],
            (structure.x * scale, structure.y * scale * squash),
            radius=max(structure.radius * scale, 4),
            strength=0.25 + structure.intensity / 160,
        )
        defs.append(gradient)
        body.append(circle)
    for x, z, size, ink, alpha in _galaxy_points(galaxy, rules):
        body.append(
            f'<circle cx="{_number(x * scale)}" cy="{_number(z * scale * squash)}" r="{size * 0.7:.1f}" fill="{ink}" fill-opacity="{alpha * light:.2f}"/>'
        )
    gradient, circle = _glow(
        f"core-{galaxy.id}", CORE, (0, 0), radius=rules.bulge_reach_pct / PERCENT * radius * scale * 1.2, strength=CORE_LIGHT[galaxy.nucleus] * light
    )
    defs.append(gradient)
    body.append(circle)
    for x, y in stars:
        body.append(f'<circle cx="{_number(x * scale)}" cy="{_number(y * scale * squash)}" r="2.6" fill="{STAR}" stroke="{VOID}" stroke-width="0.8"/>')
    return _frame("".join(defs), "".join(body), galaxy.name)


def dimension_figure(dimension: DimensionRow) -> Markup:
    rng = random.Random(dimension.id * 131 + 7)
    ink = DIMENSION_INK[dimension.dimension_kind]
    half = SIZE / 2 * 0.84
    rings = 3 + dimension.magic // 25
    gradient, glow = _glow(f"dimension-{dimension.id}", ink, (0, 0), radius=half * 1.1, strength=0.6)
    body = [glow]
    dash = ' stroke-dasharray="4 5"' if dimension.stability < 40 else ""
    for ring in range(1, rings + 1):
        distance = half * ring / rings
        opacity = 0.15 + dimension.veil / PERCENT * 0.5 * ring / rings
        shape = f'cx="0" cy="0" rx="{_number(distance)}" ry="{_number(distance * 0.42)}" fill="none"'
        body.append(f'<ellipse {shape} stroke="{ink}" stroke-opacity="{opacity:.2f}" stroke-width="1.2"{dash}/>')
    for _ in range(140):
        angle = rng.uniform(0, math.tau)
        distance = math.sqrt(rng.random()) * half
        place = f'cx="{_number(math.cos(angle) * distance)}" cy="{_number(math.sin(angle) * distance * 0.42)}"'
        body.append(f'<circle {place} r="0.9" fill="{ink}" fill-opacity="{rng.uniform(0.3, 0.9):.2f}"/>')
    core, centre = _glow(f"dimension-core-{dimension.id}", CORE, (0, 0), radius=half * 0.22, strength=0.95)
    body.append(centre)
    return _frame(gradient + core, "".join(body), dimension.name)


def cluster_figure(cluster: ClusterRow, galaxies: int) -> Markup:
    rng = random.Random(cluster.id * 977 + 3)
    spread = CLUSTER_SPREAD.get(cluster.cluster_kind, "ball")
    half = SIZE / 2
    defs: list[str] = []
    body: list[str] = []
    medium, glow = _glow(f"medium-{cluster.id}", "#ff6a8a", (0, 0), radius=half * 0.95, strength=cluster.medium_heat / PERCENT * 0.3)
    defs.append(medium)
    body.append(glow)
    for index in range(max(galaxies, 3) + 6):
        t = rng.random()
        angle = rng.uniform(0, math.tau)
        if spread == "line":
            x, y = (t - 0.5) * SIZE * 0.8, math.sin(t * math.tau) * SIZE * 0.12
        elif spread == "band":
            x, y = (t - 0.5) * SIZE * 0.85, rng.uniform(-0.15, 0.15) * SIZE
        elif spread == "ring":
            distance = SIZE * 0.34 + rng.uniform(-0.03, 0.03) * SIZE
            x, y = math.cos(angle) * distance, math.sin(angle) * distance
        else:
            distance = rng.random() ** 0.7 * SIZE * 0.36
            x, y = math.cos(angle) * distance, math.sin(angle) * distance
        major = index < galaxies
        gradient, circle = _glow(
            f"blob-{cluster.id}-{index}", YOUNG if major else DISC, (x, y), radius=(0.07 if major else 0.03) * SIZE, strength=0.95 if major else 0.5
        )
        defs.append(gradient)
        body.append(circle)
    return _frame("".join(defs), "".join(body), cluster.name)
