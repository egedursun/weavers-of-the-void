from sqlalchemy import func, select

from aerona.agents.context.scope import Scope
from aerona.catalog.worlds import ATMOSPHERE_LABELS, DISCOVERY_LABELS, GRAVITY_LABELS, WORLD_TYPES
from aerona.db.tables.celestial import StarRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.world import Discovery
from aerona.prompts import PromptId, render
from aerona.prompts.contexts.blocks import CosmosLinesContext, CosmosWorld

COUNTED = (EntityType.REGION, EntityType.PEOPLE, EntityType.SETTLEMENT)


async def world_counts(scope: Scope) -> dict[tuple[int, EntityType], int]:
    statement = (
        select(EntityRow.world_id, EntityRow.entity_type, func.count())
        .where(EntityRow.status == EntityStatus.CANON, EntityRow.entity_type.in_(COUNTED))
        .group_by(EntityRow.world_id, EntityRow.entity_type)
    )
    return {(world_id, entity_type): int(count) for world_id, entity_type, count in await scope.session.execute(statement)}


async def cosmos_lines(scope: Scope, exclude_id: int | None = None) -> str:
    if not scope.multi_world:
        return ""
    counts = await world_counts(scope)
    stars = {star.id: star.name for star in await scope.session.scalars(select(StarRow))}
    worlds = [
        CosmosWorld(
            id=world.id,
            name=world.name,
            type_label=WORLD_TYPES[world.world_type].label,
            star_name=stars.get(world.star_id) if world.star_id is not None else None,
            regions=counts.get((world.id, EntityType.REGION), 0),
            peoples=counts.get((world.id, EntityType.PEOPLE), 0),
            settlements=counts.get((world.id, EntityType.SETTLEMENT), 0),
            gravity=GRAVITY_LABELS[world.gravity],
            atmosphere=ATMOSPHERE_LABELS[world.atmosphere],
            time_factor=world.time_factor,
            discovery_label=DISCOVERY_LABELS[world.discovery] if world.discovery is not Discovery.KNOWN else None,
        )
        for world in scope.living_worlds
        if world.id != exclude_id
    ]
    return render(PromptId.COSMOS_LINES, CosmosLinesContext(worlds=worlds)) if worlds else ""
