import math
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.cosmography import BARRED_GALAXIES, NUCLEUS_OF, SPIRAL_GALAXIES
from aerona.constants.units import PERCENT
from aerona.core.random import SeededRandom
from aerona.db.repositories.base import Repository
from aerona.db.repositories.names import NameRepository
from aerona.db.tables.celestial import StarRow
from aerona.db.tables.cosmography import ClusterRow, DimensionRow, GalacticStructureRow, GalaxyRow
from aerona.db.tables.cosmos import AppliedFixupRow, CosmosRow
from aerona.domain.enums.cosmography import ClusterKind, DimensionElement, DimensionKind, GalacticNucleus, GalacticStructureKind, GalacticZone, GalaxyType
from aerona.domain.enums.world import Discovery
from aerona.engine.cosmos.kinds import CLUSTER_KIND_MECHANICS, DIMENSION_KIND_MECHANICS, GALAXY_TYPE_MECHANICS
from aerona.engine.cosmos.placement import Cosmography, zone_at
from aerona.rules.registry import Rules

LADDER_FIXUP = "cosmography.scale_ladder"
HOME_NAME_FIXUP = "cosmography.home_galaxy_name"
LOCAL_STRUCTURES = frozenset(
    kind
    for kind in GalacticStructureKind
    if kind
    not in {GalacticStructureKind.SPIRAL_ARM, GalacticStructureKind.BAR, GalacticStructureKind.BULGE, GalacticStructureKind.CORE, GalacticStructureKind.HALO}
)
ZONE_STRUCTURES: dict[GalacticZone, GalacticStructureKind] = {
    GalacticZone.CORE: GalacticStructureKind.CORE,
    GalacticZone.BULGE: GalacticStructureKind.BULGE,
    GalacticZone.BAR: GalacticStructureKind.BAR,
    GalacticZone.ARM: GalacticStructureKind.SPIRAL_ARM,
    GalacticZone.HALO: GalacticStructureKind.HALO,
}


@dataclass(frozen=True)
class DimensionDraft:
    name: str
    kind: DimensionKind
    epoch: int
    parent_dimension_id: int | None = None
    element: DimensionElement | None = None
    description: str | None = None


@dataclass(frozen=True)
class ClusterDraft:
    name: str
    kind: ClusterKind
    epoch: int
    dimension_id: int | None = None
    parent_cluster_id: int | None = None
    x: float = 0.0
    y: float = 0.0
    radius: float = 100.0
    description: str | None = None


@dataclass(frozen=True)
class GalaxyDraft:
    name: str
    galaxy_type: GalaxyType
    epoch: int
    cluster_id: int | None = None
    dimension_id: int | None = None
    x: float = 0.0
    y: float = 0.0
    radius: float = 900.0
    description: str | None = None


async def create_dimension(session: AsyncSession, rules: Rules, draft: DimensionDraft) -> DimensionRow:
    nature = DIMENSION_KIND_MECHANICS[draft.kind]
    names = NameRepository(session)
    name = await names.unique_name(draft.name)
    row = DimensionRow(
        name=name,
        dimension_kind=draft.kind,
        element=draft.element if draft.kind is DimensionKind.ELEMENTAL else None,
        parent_dimension_id=draft.parent_dimension_id,
        veil=nature.veil(rules),
        stability=nature.stability(rules),
        time_factor=nature.time(rules) / PERCENT,
        magic=nature.magic(rules),
        hostility=nature.hostility(rules),
        sanity_drain=nature.sanity(rules),
        leak=nature.leak(rules),
        discovery=Discovery.KNOWN,
        description=draft.description,
        created_epoch=draft.epoch,
        locked=[],
    )
    await Repository(session).insert(row)
    row.name = await names.claim(row.id, name)
    return row


async def create_cluster(session: AsyncSession, rules: Rules, draft: ClusterDraft) -> ClusterRow:
    names = NameRepository(session)
    name = await names.unique_name(draft.name)
    row = ClusterRow(
        name=name,
        cluster_kind=draft.kind,
        dimension_id=draft.dimension_id if draft.parent_cluster_id is None else None,
        parent_cluster_id=draft.parent_cluster_id,
        x=draft.x,
        y=draft.y,
        radius=draft.radius,
        medium_heat=CLUSTER_KIND_MECHANICS[draft.kind].heat(rules),
        expansion=0,
        discovery=Discovery.KNOWN,
        description=draft.description,
        created_epoch=draft.epoch,
        locked=[],
    )
    await Repository(session).insert(row)
    row.name = await names.claim(row.id, name)
    return row


async def create_galaxy(session: AsyncSession, rules: Rules, draft: GalaxyDraft) -> GalaxyRow:
    kind = GALAXY_TYPE_MECHANICS[draft.galaxy_type]
    names = NameRepository(session)
    name = await names.unique_name(draft.name)
    row = GalaxyRow(
        name=name,
        galaxy_type=draft.galaxy_type,
        cluster_id=draft.cluster_id,
        dimension_id=draft.dimension_id if draft.cluster_id is None else None,
        x=draft.x,
        y=draft.y,
        radius=draft.radius,
        arm_count=kind.arms(rules),
        nucleus=NUCLEUS_OF.get(draft.galaxy_type, GalacticNucleus.DORMANT),
        star_formation=kind.formation(rules),
        metallicity=kind.metallicity(rules),
        leak=0,
        discovery=Discovery.KNOWN,
        merge_progress=0,
        description=draft.description,
        created_epoch=draft.epoch,
        locked=[],
    )
    await Repository(session).insert(row)
    row.name = await names.claim(row.id, name)
    await lay_out(session, rules, row, draft.epoch)
    return row


async def lay_out(session: AsyncSession, rules: Rules, galaxy: GalaxyRow, epoch: int) -> list[GalacticStructureRow]:
    table = rules.galaxies
    made: list[GalacticStructureRow] = []
    radius = galaxy.radius
    intensity = table.layout_intensity

    def add(kind: GalacticStructureKind, name: str, x: float, y: float, reach_pct: int) -> None:
        reach = max(radius * reach_pct / PERCENT, 1.0)
        made.append(
            GalacticStructureRow(galaxy_id=galaxy.id, kind=kind, name=name, x=x, y=y, radius=reach, intensity=intensity, created_epoch=epoch, locked=[])
        )

    if galaxy.nucleus is not GalacticNucleus.NONE:
        add(GalacticStructureKind.CORE, f"Core of {galaxy.name}", 0.0, 0.0, table.core_reach_pct)
    add(GalacticStructureKind.BULGE, f"Bulge of {galaxy.name}", 0.0, 0.0, table.bulge_reach_pct)
    if galaxy.galaxy_type in BARRED_GALAXIES:
        add(GalacticStructureKind.BAR, f"Bar of {galaxy.name}", 0.0, 0.0, table.bar_reach_pct)
    if galaxy.galaxy_type in SPIRAL_GALAXIES:
        middle = (table.inner_reach_pct + table.disc_reach_pct) / 2 / PERCENT * radius
        for arm in range(galaxy.arm_count):
            angle = math.tau * arm / galaxy.arm_count
            add(
                GalacticStructureKind.SPIRAL_ARM,
                f"Arm {arm + 1} of {galaxy.name}",
                math.cos(angle) * middle,
                math.sin(angle) * middle,
                table.disc_reach_pct - table.inner_reach_pct,
            )
    add(GalacticStructureKind.HALO, f"Halo of {galaxy.name}", 0.0, 0.0, table.halo_reach_pct)
    session.add_all(made)
    await session.flush()
    return made


def structure_for(cosmography: Cosmography, star: StarRow, galaxy: GalaxyRow) -> int | None:
    local = [
        structure
        for structure in cosmography.structures.values()
        if structure.galaxy_id == galaxy.id
        and structure.ended_epoch is None
        and structure.kind in LOCAL_STRUCTURES
        and math.hypot(star.x - structure.x, star.y - structure.y) <= structure.radius
    ]
    if local:
        return min(local, key=lambda row: (math.hypot(star.x - row.x, star.y - row.y), row.id)).id
    wanted = ZONE_STRUCTURES.get(star.galactic_zone)
    if wanted is None:
        return None
    matches = [row for row in cosmography.structures.values() if row.galaxy_id == galaxy.id and row.ended_epoch is None and row.kind is wanted]
    if not matches:
        return None
    return min(matches, key=lambda row: (math.hypot(star.x - row.x, star.y - row.y), row.id)).id


def settle_star(rules: Rules, cosmography: Cosmography, star: StarRow) -> None:
    galaxy = cosmography.galaxies.get(star.galaxy_id) if star.galaxy_id is not None else None
    if galaxy is None:
        if "galactic_zone" not in star.locked:
            star.galactic_zone = GalacticZone.INTERGALACTIC
        if "structure_id" not in star.locked:
            star.structure_id = None
        return
    if "galactic_zone" not in star.locked:
        star.galactic_zone = zone_at(rules, galaxy, star.x, star.y)
    if "structure_id" not in star.locked:
        star.structure_id = structure_for(cosmography, star, galaxy)


async def home_galaxy(session: AsyncSession) -> GalaxyRow | None:
    cosmography = await Cosmography.load(session)
    prime = cosmography.prime
    for galaxy in cosmography.galaxies.values():
        if prime is None or cosmography.dimension_of_galaxy(galaxy) is prime:
            return galaxy
    return next(iter(cosmography.galaxies.values()), None)


def home_galaxy_name(cosmos_name: str) -> str:
    return f"{cosmos_name} Galaxy"


async def name_home_galaxy(session: AsyncSession) -> int:
    if await session.get(AppliedFixupRow, HOME_NAME_FIXUP) is not None:
        return 0
    ladder = await session.get(AppliedFixupRow, LADDER_FIXUP)
    cosmos = await session.scalar(select(CosmosRow))
    if ladder is None or cosmos is None:
        return 0
    galaxy = await session.get(GalaxyRow, int((ladder.result or {}).get("galaxy", 0)))
    names = NameRepository(session)
    renamed = 0
    wanted = home_galaxy_name(cosmos.name)
    if (
        galaxy is not None
        and galaxy.name.startswith(f"{cosmos.name} ")
        and galaxy.name != wanted
        and not await names.is_taken(wanted, ignore_node_id=galaxy.id)
    ):
        await names.rename(galaxy.id, wanted)
        renamed = 1
    session.add(AppliedFixupRow(key=HOME_NAME_FIXUP, result={"renamed": renamed}))
    await session.flush()
    return renamed


async def ensure_ladder(session: AsyncSession, rules: Rules) -> int:
    if await session.get(AppliedFixupRow, LADDER_FIXUP) is not None:
        return 0
    cosmos = await session.scalar(select(CosmosRow))
    if cosmos is None:
        return 0
    epoch = cosmos.epoch
    stars = list(await session.scalars(select(StarRow).order_by(StarRow.id)))
    farthest = max((math.hypot(star.x, star.y) for star in stars), default=0.0)
    table = rules.galaxies
    radius = max(float(table.home_radius), farthest * table.home_radius_margin_pct / PERCENT)
    prime = await session.scalar(select(DimensionRow).where(DimensionRow.dimension_kind == DimensionKind.PRIME).order_by(DimensionRow.id).limit(1))
    if prime is None:
        prime = await create_dimension(session, rules, DimensionDraft(f"{cosmos.name} Prime", DimensionKind.PRIME, epoch))
    group = await session.scalar(select(ClusterRow).order_by(ClusterRow.id).limit(1))
    if group is None:
        group = await create_cluster(
            session,
            rules,
            ClusterDraft(f"{cosmos.name} Group", ClusterKind.LOCAL_GROUP, epoch, dimension_id=prime.id, radius=float(rules.clusters.home_radius)),
        )
    galaxy = await session.scalar(select(GalaxyRow).order_by(GalaxyRow.id).limit(1))
    if galaxy is None:
        galaxy = await create_galaxy(session, rules, GalaxyDraft(home_galaxy_name(cosmos.name), GalaxyType.SPIRAL, epoch, cluster_id=group.id, radius=radius))
    placed = 0
    for star in stars:
        if star.galaxy_id is None:
            star.galaxy_id = galaxy.id
            placed += 1
    await session.flush()
    cosmography = await Cosmography.load(session)
    for star in stars:
        settle_star(rules, cosmography, star)
    session.add(AppliedFixupRow(key=LADDER_FIXUP, result={"stars": placed, "galaxy": galaxy.id, "dimension": prime.id}))
    await session.flush()
    return placed


def birth_position(rng: SeededRandom, structure: GalacticStructureRow) -> tuple[float, float]:
    angle = rng.random() * math.tau
    distance = math.sqrt(rng.random()) * structure.radius
    return structure.x + math.cos(angle) * distance, structure.y + math.sin(angle) * distance
