from collections.abc import Mapping
from typing import Any

from aerona.core.errors import NotFoundError
from aerona.db.tables.anatomy import CreatureAnatomyRow
from aerona.db.tables.ecology import BeastProfileRow, SpeciesProfileRow
from aerona.domain.enums.entity import EntityType
from aerona.engine.context import TickContext
from aerona.engine.ecology.anatomy import beast_anatomy, species_anatomy
from aerona.engine.polity.control import lock
from aerona.engine.primitives.edits import bounds, coerce
from aerona.engine.primitives.queries import living_entity


async def make_anatomy(ctx: TickContext, node_id: int) -> CreatureAnatomyRow:
    creature = await living_entity(ctx.session, node_id)
    if creature is not None and creature.entity_type is EntityType.SPECIES:
        profile = await ctx.session.get(SpeciesProfileRow, node_id)
        if profile is not None:
            return await species_anatomy(ctx, creature, profile)
    if creature is not None and creature.entity_type is EntityType.BEAST:
        beast = await ctx.session.get(BeastProfileRow, node_id)
        if beast is not None:
            return await beast_anatomy(ctx, creature, beast)
    raise NotFoundError("Only a described kind or a named beast has a body to shape.")


async def edit_anatomy(ctx: TickContext, node_id: int, values: Mapping[str, Any], *, release: list[str]) -> CreatureAnatomyRow:
    row = await ctx.session.get(CreatureAnatomyRow, node_id) or await make_anatomy(ctx, node_id)
    limits = bounds(row)
    for key, value in values.items():
        setattr(row, key, coerce(row, key, value, limits))
        row.locked = lock(row.locked, key)
    row.locked = [item for item in row.locked if item not in release]
    await ctx.session.flush()
    return row


async def reroll_anatomy(ctx: TickContext, node_id: int) -> CreatureAnatomyRow:
    row = await ctx.session.get(CreatureAnatomyRow, node_id)
    if row is not None:
        await ctx.session.delete(row)
        await ctx.session.flush()
    fresh = await make_anatomy(ctx, node_id)
    await ctx.session.flush()
    return fresh
