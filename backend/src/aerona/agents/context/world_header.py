from sqlalchemy import select

from aerona.agents.context.naming import naming_item, world_naming
from aerona.agents.context.scope import Scope
from aerona.catalog.climate import CLIMATES
from aerona.catalog.domains import DOMAIN_LABELS
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.prompts import PromptId, render
from aerona.prompts.contexts.blocks import AgeStar, ClimateLine, CreatorMood, EpicSummary, LawLine, WorldHeaderContext


def target_world(scope: Scope, world_id: int | None) -> WorldRow | None:
    if world_id is not None and world_id in scope.worlds:
        return scope.worlds[world_id]
    return scope.primary_world


def climate_line(world: WorldRow | None) -> ClimateLine | None:
    if world is None or world.climate_era is None:
        return None
    spec = CLIMATES[world.climate_era]
    return ClimateLine(name=spec.label, since_age=world.climate_since_epoch or world.created_epoch, description=spec.description)


async def age_star(scope: Scope, world: WorldRow | None, world_id: int | None) -> AgeStar | None:
    star_id = world.epoch_star_entity_id if world is not None else None
    if star_id is None and scope.primary_world is not None:
        star_id = scope.primary_world.epoch_star_entity_id
    if star_id is None:
        return None
    star = await scope.session.get(EntityRow, star_id)
    if star is None:
        return None
    sky_world = world.name if world is not None and world_id is not None and world.id != scope.primary_world_id else None
    return AgeStar(id=star.id, name=star.name, domain=DOMAIN_LABELS[star.domain] if star.domain else None, sky_world=sky_world)


async def laws(scope: Scope, world: WorldRow | None) -> list[LawLine]:
    if world is None:
        return []
    statement = (
        select(EntityRow)
        .where(EntityRow.entity_type == EntityType.NATURAL_LAW, EntityRow.status == EntityStatus.CANON, EntityRow.world_id == world.id)
        .order_by(EntityRow.id)
    )
    return [LawLine(id=law.id, name=law.name, description=law.description) for law in await scope.session.scalars(statement)]


async def world_header_context(scope: Scope, world_id: int | None = None, short: bool = False) -> WorldHeaderContext:
    creator = scope.creator
    cosmos = scope.cosmos
    world = target_world(scope, world_id)
    primary = scope.primary_world
    fallback = primary.phonology if primary is not None else None
    dialect = None
    if world_id is not None and world is not None and world.id != scope.primary_world_id and world.phonology is not None:
        dialect = world_naming(world, fallback)
    dialects = [world_naming(item, fallback) for item in scope.living_worlds] if world_id is None and scope.multi_world else []
    depth = creator.depth
    return WorldHeaderContext(
        rules=scope.rules,
        world_name=cosmos.name,
        age=cosmos.epoch,
        world_year=cosmos.epoch_start_year,
        god_name=creator.name,
        god_title=creator.title,
        short=short,
        god_temperament=creator.temperament,
        god_note=creator.note,
        mood=CreatorMood(contentment=creator.mood_contentment, anger=creator.mood_anger, attention=creator.mood_interest, loneliness=creator.mood_loneliness),
        epic=EpicSummary(title=creator.epic.title, line=creator.epic.verse) if creator.epic is not None else None,
        prohibitions=list(depth.taboos) if depth is not None else [],
        desire=depth.desire or None if depth is not None else None,
        cosmology=cosmos.cosmology,
        tone=cosmos.tone,
        naming_rule=naming_item(fallback),
        dialect_world=dialect,
        dialects=dialects,
        doom=cosmos.doom_clock,
        doom_threshold=scope.rules.balance.apocalypse_threshold,
        climate=climate_line(world),
        age_star=await age_star(scope, world, world_id),
        laws=await laws(scope, world),
    )


async def world_header(scope: Scope, world_id: int | None = None, short: bool = False) -> str:
    return render(PromptId.WORLD_HEADER, await world_header_context(scope, world_id, short))
