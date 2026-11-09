from sqlalchemy import select

from aerona.agents.ask import ask
from aerona.agents.context.recent_chronicle import recent_chronicle
from aerona.agents.context.scope import Scope, load_scope
from aerona.agents.context.world_header import world_header
from aerona.agents.deepener import normalize_depth
from aerona.agents.roles import AgentRole
from aerona.agents.runtime import AgentRuntime
from aerona.catalog.stars import STAR_TYPE_LABELS, STAR_TYPES
from aerona.catalog.worlds import ATMOSPHERE_LABELS, DISCOVERY_LABELS, GRAVITY_LABELS, WORLD_TYPES
from aerona.core.errors import NotFoundError
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.models.profiles import EntityDepth
from aerona.engine.primitives.stats import stat
from aerona.prompts import PromptId
from aerona.prompts.contexts.narrative import CelestialKind, DeepenCelestialContext
from aerona.prompts.schemas.narrative import DeepenOutput

PEOPLE_LINES = 8


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
        f"Kindled in age {star.created_epoch}",
    ]
    if star.description:
        details.append(f"Description: {star.description}")
    worlds = list(await scope.session.scalars(select(WorldRow).where(WorldRow.star_id == star.id).order_by(WorldRow.orbit)))
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
        else:
            star = await session.get(StarRow, node_id)
            if star is None:
                raise NotFoundError("No such star.")
            name, lore, world_id = star.name, "", None
            details, neighbours = await _star_lines(scope, star)
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
        row: WorldRow | StarRow | None = await session.get(WorldRow, node_id) if kind is CelestialKind.WORLD else await session.get(StarRow, node_id)
        if row is None:
            raise NotFoundError(f"No such {kind.value}.")
        depth = normalize_depth(output, (await load_scope(session, rules)).epoch, None, None)
        row.depth = depth
    return depth
