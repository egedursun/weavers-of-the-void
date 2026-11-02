from aerona.agents.context.scope import Scope
from aerona.catalog.stars import STAR_TYPE_LABELS
from aerona.catalog.worlds import ATMOSPHERE_LABELS, GRAVITY_LABELS, WORLD_TYPES
from aerona.db.tables.celestial import StarRow
from aerona.prompts import PromptId, render
from aerona.prompts.contexts.blocks import WorldLineContext


async def world_line_context(scope: Scope, world_id: int) -> WorldLineContext | None:
    world = scope.worlds.get(world_id)
    if world is None:
        return None
    star = await scope.session.get(StarRow, world.star_id) if world.star_id is not None else None
    return WorldLineContext(
        id=world.id,
        name=world.name,
        type_label=WORLD_TYPES[world.world_type].label,
        star_name=star.name if star else None,
        star_type=STAR_TYPE_LABELS[star.star_type] if star else None,
        gravity=GRAVITY_LABELS[world.gravity],
        atmosphere=ATMOSPHERE_LABELS[world.atmosphere],
        time_factor=world.time_factor,
        leak=world.leakage,
        cosmology=world.cosmology if world.id != scope.primary_world_id else None,
    )


async def world_line(scope: Scope, world_id: int | None) -> str:
    context = await world_line_context(scope, world_id) if world_id is not None else None
    return render(PromptId.WORLD_LINE, context) if context is not None else ""
