from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.ask import ask
from aerona.agents.context.recent_chronicle import recent_chronicle
from aerona.agents.context.scope import Scope, load_scope
from aerona.agents.context.world_header import world_header
from aerona.agents.deepener import normalize_depth
from aerona.agents.roles import AgentRole
from aerona.agents.runtime import AgentRuntime
from aerona.catalog.cosmography import (
    CAUSALITY_LABELS,
    CLUSTER_KINDS,
    DIMENSION_KINDS,
    GALAXY_AGE_LABELS,
    GALAXY_TYPES,
    NUCLEUS_LABELS,
    STRUCTURE_KINDS,
)
from aerona.catalog.stars import STAR_TYPE_LABELS, STAR_TYPES
from aerona.catalog.worlds import ATMOSPHERE_LABELS, DISCOVERY_LABELS, GRAVITY_LABELS, WORLD_TYPES
from aerona.core.errors import NotFoundError
from aerona.core.grammar import spoken
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.cosmography import ClusterRow, DimensionRow, GalaxyRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.node import NodeKind
from aerona.domain.models.profiles import EntityDepth
from aerona.engine.cosmos.placement import Cosmography
from aerona.engine.primitives.stats import stat
from aerona.prompts import PromptId
from aerona.prompts.contexts.narrative import CelestialKind, DeepenCelestialContext
from aerona.prompts.schemas.narrative import DeepenOutput

PEOPLE_LINES = 8


DepthRow = WorldRow | StarRow | GalaxyRow | ClusterRow | DimensionRow
SCALE_DEPTH_KINDS: dict[NodeKind, CelestialKind] = {
    NodeKind.GALAXY: CelestialKind.GALAXY,
    NodeKind.CLUSTER: CelestialKind.CLUSTER,
    NodeKind.DIMENSION: CelestialKind.DIMENSION,
}


async def scale_row(session: AsyncSession, kind: CelestialKind, node_id: int) -> GalaxyRow | ClusterRow | DimensionRow | None:
    if kind is CelestialKind.GALAXY:
        return await session.get(GalaxyRow, node_id)
    if kind is CelestialKind.CLUSTER:
        return await session.get(ClusterRow, node_id)
    if kind is CelestialKind.DIMENSION:
        return await session.get(DimensionRow, node_id)
    return None


async def depth_row(session: AsyncSession, kind: CelestialKind, node_id: int) -> DepthRow | None:
    if kind is CelestialKind.WORLD:
        return await session.get(WorldRow, node_id)
    if kind is CelestialKind.STAR:
        return await session.get(StarRow, node_id)
    return await scale_row(session, kind, node_id)


async def scale_lines(session: AsyncSession, row: GalaxyRow | ClusterRow | DimensionRow) -> tuple[list[str], list[str]]:
    ladder = await Cosmography.load(session)
    if isinstance(row, GalaxyRow):
        details = [
            f"Kind: {GALAXY_TYPES[row.galaxy_type].label} ({GALAXY_TYPES[row.galaxy_type].description})",
            f"Nucleus: {NUCLEUS_LABELS[row.nucleus]}",
            f"Age: {GALAXY_AGE_LABELS[row.age_stage]}",
            f"Arms: {row.arm_count}",
        ]
        holder = ladder.clusters.get(row.cluster_id or 0)
        neighbours = [f"In the cluster {holder.name}"] if holder else []
        neighbours += [f"Star {star.name}" for star in sorted(ladder.stars_in_galaxy(row.id), key=lambda star: star.id)]
        neighbours += [f"Structure {item.name} ({STRUCTURE_KINDS[item.kind].label})" for item in ladder.structures.values() if item.galaxy_id == row.id]
    elif isinstance(row, ClusterRow):
        details = [f"Kind: {CLUSTER_KINDS[row.cluster_kind].label} ({CLUSTER_KINDS[row.cluster_kind].description})"]
        neighbours = [f"Galaxy {galaxy.name}" for galaxy in ladder.galaxies.values() if galaxy.cluster_id == row.id]
        neighbours += [f"Cluster {child.name}" for child in ladder.clusters.values() if child.parent_cluster_id == row.id]
    else:
        details = [
            f"Kind: {DIMENSION_KINDS[row.dimension_kind].label} ({DIMENSION_KINDS[row.dimension_kind].description})",
            f"Causality: {CAUSALITY_LABELS[row.causality]}",
            f"Time runs {row.time_factor:g} times as it does in the prime",
        ]
        neighbours = [f"Cluster {cluster.name}" for cluster in ladder.clusters.values() if cluster.dimension_id == row.id]
        neighbours += [f"World {world.name}" for world in ladder.worlds_in_dimension(row.id)]
    details.append(f"Came to be in age {row.created_epoch}")
    return details, neighbours


async def _world_lines(scope: Scope, world: WorldRow) -> tuple[list[str], list[str]]:
    session = scope.session
    star = await session.get(StarRow, world.star_id) if world.star_id is not None else None
    details = [
        f"Kind: {WORLD_TYPES[world.world_type].label} ({WORLD_TYPES[world.world_type].description})",
        f"Gravity: {GRAVITY_LABELS[world.gravity]}",
        f"Atmosphere: {ATMOSPHERE_LABELS[world.atmosphere]}",
        f"Known to the gods: {DISCOVERY_LABELS[world.discovery]}",
    ]
    if world.climate_era is not None:
        details.append(f"Climate: {world.climate_era.value.replace('_', ' ')}")
    if world.description:
        details.append(f"Description: {world.description}")
    neighbours: list[str] = []
    if star is not None:
        neighbours.append(f"Its star: {star.name} ({STAR_TYPE_LABELS[star.star_type]}: {STAR_TYPES[star.star_type].description})")
    if world.patron_son_id is not None and (patron := await session.get(SonRow, world.patron_son_id)) is not None:
        neighbours.append(f"Its guardian son: {patron.name}")
    peoples = list(
        await session.scalars(
            select(EntityRow).where(EntityRow.world_id == world.id, EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON)
        )
    )
    peoples.sort(key=lambda people: stat(people, "population") or 0, reverse=True)
    neighbours += [f"A people of the world: {people.name}" for people in peoples[:PEOPLE_LINES]]
    return details, neighbours


async def _star_lines(scope: Scope, star: StarRow) -> tuple[list[str], list[str]]:
    details = [
        f"Kind: {STAR_TYPE_LABELS[star.star_type]} ({STAR_TYPES[star.star_type].description})",
        f"Brightness: {star.brightness}/100",
        f"Came to be in age {star.created_epoch}",
    ]
    if star.description:
        details.append(f"Description: {star.description}")
    worlds = list(
        await scope.session.scalars(
            select(WorldRow).where(WorldRow.star_id == star.id).order_by(WorldRow.parent_world_id.is_not(None), WorldRow.orbit, WorldRow.id)
        )
    )
    neighbours = [f"{world.name} ({WORLD_TYPES[world.world_type].label})" for world in worlds]
    return details, neighbours


async def deepen_celestial(runtime: AgentRuntime, kind: CelestialKind, node_id: int) -> EntityDepth:
    runtime.require_llm("deepening")
    async with runtime.database.read() as session:
        rules = await runtime.rules(session)
        scope = await load_scope(session, rules)
        if kind is CelestialKind.WORLD:
            world = await session.get(WorldRow, node_id)
            if world is None:
                raise NotFoundError("No such world.")
            name, lore, world_id = world.name, world.cosmology or "", world.id
            details, neighbours = await _world_lines(scope, world)
        elif kind is CelestialKind.STAR:
            star = await session.get(StarRow, node_id)
            if star is None:
                raise NotFoundError("No such star.")
            name, lore, world_id = star.name, "", None
            details, neighbours = await _star_lines(scope, star)
        else:
            scale = await scale_row(session, kind, node_id)
            if scale is None:
                raise NotFoundError(f"No such {spoken(kind)}.")
            name, lore, world_id = scale.name, scale.description or "", None
            details, neighbours = await scale_lines(session, scale)
        context = DeepenCelestialContext(
            lore_language=scope.cosmos.lore_language,
            rules=rules,
            world_name=scope.cosmos.name,
            world_header=await world_header(scope, world_id if scope.multi_world else None),
            kind=kind,
            name=name,
            detail_lines=details,
            lore=lore,
            neighbour_lines=neighbours,
            recent_events=await recent_chronicle(scope, rules.context.chronicle_default, world_id),
        )
    output = await ask(
        runtime.model,
        rules,
        label=AgentRole.DEEPENING,
        system=(PromptId.DEEPEN_CELESTIAL_SYSTEM, context),
        user=(PromptId.DEEPEN_CELESTIAL_USER, context),
        output=DeepenOutput,
    )
    async with runtime.database.write() as session:
        row = await depth_row(session, kind, node_id)
        if row is None:
            raise NotFoundError(f"No such {spoken(kind)}.")
        depth = normalize_depth(output, (await load_scope(session, rules)).epoch, None, None)
        row.depth = depth
    return depth
