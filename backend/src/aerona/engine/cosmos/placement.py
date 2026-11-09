import math
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.cosmography import BARRED_GALAXIES, DIMENSION_MINERALS, SCOPE_ORDER, SPIRAL_GALAXIES, STRUCTURE_MINERALS
from aerona.constants.units import PERCENT
from aerona.db.read_memo import memo_of, table_names
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.cosmography import ClusterRow, DimensionalEventRow, DimensionRow, GalacticStructureRow, GalaxyRow
from aerona.db.tables.cosmos import CosmosRow
from aerona.domain.enums.cosmography import ClusterKind, DimensionalEventKind, DimensionKind, GalacticZone, RouteScope
from aerona.domain.enums.material import MaterialKind
from aerona.engine.cosmos.kinds import CLUSTER_KIND_MECHANICS, DIMENSION_KIND_MECHANICS, GALAXY_TYPE_MECHANICS, STRUCTURE_MECHANICS, ZONE_MECHANICS
from aerona.rules.registry import Rules

GROUP_KINDS = frozenset({ClusterKind.GALAXY_GROUP, ClusterKind.LOCAL_GROUP})
NEUTRAL = 1.0


@dataclass(frozen=True)
class Placement:
    dimension: DimensionRow | None = None
    cluster: ClusterRow | None = None
    top_cluster: ClusterRow | None = None
    galaxy: GalaxyRow | None = None
    structure: GalacticStructureRow | None = None
    star: StarRow | None = None
    zone: GalacticZone = GalacticZone.INTERGALACTIC

    @property
    def dimension_id(self) -> int | None:
        return self.dimension.id if self.dimension is not None else None

    @property
    def galaxy_id(self) -> int | None:
        return self.galaxy.id if self.galaxy is not None else None


@dataclass(frozen=True)
class CosmicPull:
    time: float = NEUTRAL
    capacity: float = NEUTRAL
    ore: float = NEUTRAL
    density: float = NEUTRAL
    magic: int = 0
    leak: int = 0
    sanity: int = 0
    danger: int = 0
    hostility: int = 0
    minerals: tuple[MaterialKind, ...] = ()
    hidden: float = 0.0
    delay: int = 0


@dataclass
class Cosmography:
    dimensions: dict[int, DimensionRow] = field(default_factory=dict)
    clusters: dict[int, ClusterRow] = field(default_factory=dict)
    galaxies: dict[int, GalaxyRow] = field(default_factory=dict)
    structures: dict[int, GalacticStructureRow] = field(default_factory=dict)
    stars: dict[int, StarRow] = field(default_factory=dict)
    worlds: dict[int, WorldRow] = field(default_factory=dict)
    convergences: dict[int, int] = field(default_factory=dict)

    @classmethod
    async def load(cls, session: AsyncSession) -> "Cosmography":
        epoch = int(await session.scalar(select(CosmosRow.epoch)) or 0)
        pairs: dict[int, int] = {}
        statement = select(DimensionalEventRow).where(
            DimensionalEventRow.kind == DimensionalEventKind.CONVERGENCE,
            DimensionalEventRow.other_dimension_id.is_not(None),
            (DimensionalEventRow.until_epoch.is_(None)) | (DimensionalEventRow.until_epoch >= epoch),
        )
        for event in await session.scalars(statement):
            if event.other_dimension_id is not None:
                pairs[event.dimension_id] = event.other_dimension_id
                pairs[event.other_dimension_id] = event.dimension_id
        return cls(
            {row.id: row for row in await session.scalars(select(DimensionRow).order_by(DimensionRow.id))},
            {row.id: row for row in await session.scalars(select(ClusterRow).order_by(ClusterRow.id))},
            {row.id: row for row in await session.scalars(select(GalaxyRow).order_by(GalaxyRow.id))},
            {row.id: row for row in await session.scalars(select(GalacticStructureRow).order_by(GalacticStructureRow.id))},
            {row.id: row for row in await session.scalars(select(StarRow).order_by(StarRow.id))},
            {row.id: row for row in await session.scalars(select(WorldRow).order_by(WorldRow.id))},
            pairs,
        )

    @property
    def prime(self) -> DimensionRow | None:
        primes = [row for row in self.dimensions.values() if row.dimension_kind is DimensionKind.PRIME]
        return primes[0] if primes else next(iter(self.dimensions.values()), None)

    def cluster_chain(self, cluster: ClusterRow | None) -> list[ClusterRow]:
        chain: list[ClusterRow] = []
        seen: set[int] = set()
        while cluster is not None and cluster.id not in seen:
            chain.append(cluster)
            seen.add(cluster.id)
            cluster = self.clusters.get(cluster.parent_cluster_id) if cluster.parent_cluster_id is not None else None
        return chain

    def dimension_of_cluster(self, cluster: ClusterRow | None) -> DimensionRow | None:
        chain = self.cluster_chain(cluster)
        top = chain[-1] if chain else None
        if top is not None and top.dimension_id is not None:
            return self.dimensions.get(top.dimension_id)
        return self.prime

    def dimension_of_galaxy(self, galaxy: GalaxyRow | None) -> DimensionRow | None:
        if galaxy is None:
            return self.prime
        if galaxy.cluster_id is not None:
            return self.dimension_of_cluster(self.clusters.get(galaxy.cluster_id))
        if galaxy.dimension_id is not None:
            return self.dimensions.get(galaxy.dimension_id)
        return self.prime

    def root_world(self, world: WorldRow) -> WorldRow:
        seen: set[int] = set()
        while world.parent_world_id is not None and world.id not in seen:
            seen.add(world.id)
            parent = self.worlds.get(world.parent_world_id)
            if parent is None:
                break
            world = parent
        return world

    def place_star(self, star: StarRow) -> Placement:
        galaxy = self.galaxies.get(star.galaxy_id) if star.galaxy_id is not None else None
        cluster = self.clusters.get(galaxy.cluster_id) if galaxy is not None and galaxy.cluster_id is not None else None
        chain = self.cluster_chain(cluster)
        structure = self.structures.get(star.structure_id) if star.structure_id is not None else None
        zone = star.galactic_zone if galaxy is not None else GalacticZone.INTERGALACTIC
        return Placement(self.dimension_of_galaxy(galaxy), cluster, chain[-1] if chain else None, galaxy, structure, star, zone)

    def place_world(self, world: WorldRow) -> Placement:
        root = self.root_world(world)
        star = self.stars.get(root.star_id) if root.star_id is not None else None
        if star is not None:
            return self.place_star(star)
        if root.galaxy_id is not None and root.galaxy_id in self.galaxies:
            galaxy = self.galaxies[root.galaxy_id]
            cluster = self.clusters.get(galaxy.cluster_id) if galaxy.cluster_id is not None else None
            chain = self.cluster_chain(cluster)
            return Placement(self.dimension_of_galaxy(galaxy), cluster, chain[-1] if chain else None, galaxy, None, None, GalacticZone.OUTER_DISC)
        dimension = self.dimensions.get(root.dimension_id) if root.dimension_id is not None else self.prime
        return Placement(dimension)

    def partner_of(self, placement: Placement) -> DimensionRow | None:
        other = self.convergences.get(placement.dimension_id or 0)
        return self.dimensions.get(other) if other is not None else None

    def pull(self, rules: Rules, placement: Placement) -> CosmicPull:
        return pull_of(rules, placement, self.partner_of(placement))

    def place_world_id(self, world_id: int | None) -> Placement:
        world = self.worlds.get(world_id) if world_id is not None else None
        return self.place_world(world) if world is not None else Placement(self.prime)

    def worlds_in_dimension(self, dimension_id: int) -> list[WorldRow]:
        return [world for world in self.worlds.values() if self.place_world(world).dimension_id == dimension_id]

    def worlds_in_galaxy(self, galaxy_id: int) -> list[WorldRow]:
        return [world for world in self.worlds.values() if self.place_world(world).galaxy_id == galaxy_id]

    def stars_in_galaxy(self, galaxy_id: int) -> list[StarRow]:
        return [star for star in self.stars.values() if star.galaxy_id == galaxy_id]

    def central_galaxy(self, cluster_id: int | None) -> GalaxyRow | None:
        members = [row for row in self.galaxies.values() if cluster_id is not None and row.cluster_id == cluster_id]
        return max(members, key=lambda row: (len(self.stars_in_galaxy(row.id)), row.radius, -row.id), default=None)

    def scope(self, first: WorldRow, second: WorldRow) -> RouteScope:
        a, b = self.place_world(first), self.place_world(second)
        same_cluster = a.cluster is not None and b.cluster is not None and a.cluster.id == b.cluster.id
        same_top = (a.top_cluster is None and b.top_cluster is None) or (
            a.top_cluster is not None and b.top_cluster is not None and a.top_cluster.id == b.top_cluster.id
        )
        steps = (
            (a.dimension_id != b.dimension_id, RouteScope.INTERDIMENSIONAL),
            (a.star is not None and b.star is not None and a.star.id == b.star.id, RouteScope.SYSTEM),
            (a.galaxy_id == b.galaxy_id, RouteScope.STELLAR),
            (same_cluster and a.cluster is not None and a.cluster.cluster_kind in GROUP_KINDS, RouteScope.GALACTIC),
            (same_cluster or same_top, RouteScope.INTERGALACTIC),
        )
        return next((scope for matched, scope in steps if matched), RouteScope.INTERCLUSTER)

    def scope_by_id(self, first_id: int, second_id: int) -> RouteScope:
        first, second = self.worlds.get(first_id), self.worlds.get(second_id)
        if first is None or second is None:
            return RouteScope.STELLAR
        return self.scope(first, second)


LADDER_TABLES = table_names((DimensionRow, ClusterRow, GalaxyRow, GalacticStructureRow, StarRow, WorldRow, DimensionalEventRow, CosmosRow))


async def cosmography_of(session: AsyncSession) -> Cosmography:
    memo = memo_of(session, "cosmography", LADDER_TABLES)
    if memo is not None and "ladder" in memo:
        found: Cosmography = memo["ladder"]
        return found
    loaded = await Cosmography.load(session)
    if memo is not None:
        memo["ladder"] = loaded
    return loaded


async def world_pull(session: AsyncSession, rules: Rules, world: WorldRow) -> CosmicPull:
    cosmography = await cosmography_of(session)
    return cosmography.pull(rules, cosmography.place_world(world))


async def hidden_sky(session: AsyncSession, rules: Rules, world_id: int | None) -> float:
    cosmography = await cosmography_of(session)
    return min(1.0, cosmography.pull(rules, cosmography.place_world_id(world_id)).hidden)


def within_reach(scope: RouteScope, reach: RouteScope) -> bool:
    return SCOPE_ORDER.index(scope) <= SCOPE_ORDER.index(reach)


@dataclass
class PullTally:
    capacity: float = NEUTRAL
    ore: float = NEUTRAL
    density: float = NEUTRAL
    time: float = NEUTRAL
    magic: int = 0
    leak: int = 0
    sanity: int = 0
    danger: int = 0
    hostility: int = 0
    delay: int = 0
    hidden: float = 0.0
    minerals: list[MaterialKind] = field(default_factory=list)

    def zone(self, rules: Rules, zone: GalacticZone, metallicity: float) -> None:
        effect = ZONE_MECHANICS[zone]
        self.capacity *= effect.capacity(rules) / PERCENT
        self.density *= effect.density(rules) / PERCENT
        self.ore *= effect.metallicity(rules) / PERCENT * metallicity
        self.leak += effect.leak(rules)
        self.danger += effect.danger(rules)
        self.delay += effect.delay(rules)

    def galaxy(self, rules: Rules, galaxy: GalaxyRow, zone: GalacticZone) -> None:
        kind = GALAXY_TYPE_MECHANICS[galaxy.galaxy_type]
        self.capacity *= kind.capacity(rules) / PERCENT
        self.density *= kind.density(rules) / PERCENT
        self.leak += kind.leak(rules) + galaxy.leak // rules.dimensions.leak_world_per
        self.sanity += kind.sanity(rules)
        self.danger += kind.danger(rules)
        self.zone(rules, zone, (PERCENT / 2 + galaxy.metallicity) / PERCENT)

    def cluster(self, rules: Rules, cluster: ClusterRow) -> None:
        kind = CLUSTER_KIND_MECHANICS[cluster.cluster_kind]
        self.leak += kind.leak(rules)
        self.danger += kind.danger(rules) + cluster.medium_heat // rules.clusters.heat_danger_per

    def structure(self, rules: Rules, structure: GalacticStructureRow) -> None:
        effect = STRUCTURE_MECHANICS[structure.kind]
        share = structure.intensity / PERCENT
        self.magic += round(effect.magic(rules) * share)
        self.leak += round(effect.leak(rules) * share)
        self.danger += round(effect.danger(rules) * share)
        self.delay += effect.delay(rules)
        self.hidden = effect.hide(rules) * share / PERCENT
        if structure.kind in STRUCTURE_MINERALS:
            self.minerals.append(STRUCTURE_MINERALS[structure.kind])

    def dimension(self, rules: Rules, dimension: DimensionRow, partner: DimensionRow | None) -> None:
        nature = DIMENSION_KIND_MECHANICS[dimension.dimension_kind]
        self.time = (dimension.time_factor + partner.time_factor) / 2 if partner is not None else dimension.time_factor
        self.capacity *= nature.capacity(rules) / PERCENT
        self.magic += dimension.magic
        self.leak += dimension.leak // rules.dimensions.leak_world_per
        self.sanity += dimension.sanity_drain
        self.hostility = dimension.hostility
        self.danger += dimension.hostility // rules.dimensions.hostility_danger_per
        if dimension.dimension_kind in DIMENSION_MINERALS:
            self.minerals.append(DIMENSION_MINERALS[dimension.dimension_kind])


def pull_of(rules: Rules, placement: Placement, partner: DimensionRow | None = None) -> CosmicPull:
    tally = PullTally()
    if placement.galaxy is not None:
        tally.galaxy(rules, placement.galaxy, placement.zone)
    else:
        tally.zone(rules, GalacticZone.INTERGALACTIC, NEUTRAL)
    if placement.cluster is not None:
        tally.cluster(rules, placement.cluster)
    if placement.structure is not None and placement.structure.ended_epoch is None:
        tally.structure(rules, placement.structure)
    if placement.dimension is not None:
        tally.dimension(rules, placement.dimension, partner)
    return CosmicPull(
        tally.time,
        tally.capacity,
        tally.ore,
        tally.density,
        tally.magic,
        tally.leak,
        tally.sanity,
        tally.danger,
        tally.hostility,
        tuple(tally.minerals),
        tally.hidden,
        tally.delay,
    )


def zone_at(rules: Rules, galaxy: GalaxyRow, x: float, y: float) -> GalacticZone:
    table = rules.galaxies
    reach = math.hypot(x, y) / galaxy.radius * PERCENT if galaxy.radius > 0 else PERCENT
    angle = math.degrees(math.atan2(y, x)) % 360
    barred = galaxy.galaxy_type in BARRED_GALAXIES and min(angle % 180, 180 - angle % 180) <= table.arm_width_deg / 2
    spiral = galaxy.galaxy_type in SPIRAL_GALAXIES and galaxy.arm_count > 0
    disc = GalacticZone.ARM if spiral and on_arm(rules, galaxy, angle, reach) else GalacticZone.INTERARM if spiral else GalacticZone.OUTER_DISC
    if not spiral and reach <= (table.inner_reach_pct + table.disc_reach_pct) / 2:
        disc = GalacticZone.INNER_DISC
    bands = (
        (reach <= table.core_reach_pct, GalacticZone.CORE),
        (reach <= table.bulge_reach_pct, GalacticZone.BULGE),
        (barred and reach <= table.bar_reach_pct, GalacticZone.BAR),
        (reach <= table.inner_reach_pct, GalacticZone.INNER_DISC),
        (reach <= table.disc_reach_pct, disc),
        (reach <= table.halo_reach_pct, GalacticZone.HALO),
    )
    return next((zone for matched, zone in bands if matched), GalacticZone.RIM)


def on_arm(rules: Rules, galaxy: GalaxyRow, angle: float, reach: float) -> bool:
    table = rules.galaxies
    spacing = 360 / galaxy.arm_count
    wound = (angle - reach / PERCENT * table.arm_wind_deg) % spacing
    return min(wound, spacing - wound) <= table.arm_width_deg / 2
