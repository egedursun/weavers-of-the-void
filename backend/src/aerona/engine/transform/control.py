from collections.abc import Mapping
from typing import Any

from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.celestial import StarRow
from aerona.db.tables.transform import (
    LUMINOSITY_SHIFT_MAX,
    PROSPECT_FIELDS,
    STAR_MODIFIER_FIELDS,
    TRANSFORMATION_FIELDS,
    StarModifierRow,
    TransformationRow,
    TransformProspectRow,
)
from aerona.domain.enums.transform import StarModifierSource
from aerona.engine.context import TickContext
from aerona.engine.divine.control import apply
from aerona.engine.gatherings.control import allowed


async def require_transformation(ctx: TickContext, transformation_id: int) -> TransformationRow:
    row = await ctx.session.get(TransformationRow, transformation_id)
    if row is None:
        raise NotFoundError("No such transformation.")
    return row


async def edit_transformation(ctx: TickContext, transformation_id: int, values: Mapping[str, Any], release: list[str]) -> TransformationRow:
    row = await require_transformation(ctx, transformation_id)
    allowed(values, TRANSFORMATION_FIELDS, "transformation")
    apply(row, values, release)
    await ctx.session.flush()
    return row


async def remove_transformation(ctx: TickContext, transformation_id: int) -> None:
    await ctx.session.delete(await require_transformation(ctx, transformation_id))
    await ctx.session.flush()


async def require_prospect(ctx: TickContext, prospect_id: int) -> TransformProspectRow:
    row = await ctx.session.get(TransformProspectRow, prospect_id)
    if row is None:
        raise NotFoundError("No such prospect of a transformation.")
    return row


async def edit_prospect(ctx: TickContext, prospect_id: int, values: Mapping[str, Any], release: list[str]) -> TransformProspectRow:
    row = await require_prospect(ctx, prospect_id)
    allowed(values, PROSPECT_FIELDS, "prospect of a transformation")
    apply(row, values, release)
    await ctx.session.flush()
    return row


async def remove_prospect(ctx: TickContext, prospect_id: int) -> None:
    await ctx.session.delete(await require_prospect(ctx, prospect_id))
    await ctx.session.flush()


async def add_star_modifier(ctx: TickContext, star_id: int, luminosity_pct: int, age_epochs: int, decay: int) -> StarModifierRow:
    if await ctx.session.get(StarRow, star_id) is None:
        raise NotFoundError("No such star.")
    if abs(luminosity_pct) > LUMINOSITY_SHIFT_MAX:
        raise ValidationFailedError(f"A star's light can be shifted by at most {LUMINOSITY_SHIFT_MAX} in a hundred.")
    row = StarModifierRow(
        star_id=star_id,
        source=StarModifierSource.DIVINE_ACT,
        luminosity_pct=luminosity_pct,
        age_epochs=age_epochs,
        aged=False,
        decay=decay,
        epoch=ctx.epoch,
        cause_node_id=None,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def require_star_modifier(ctx: TickContext, modifier_id: int) -> StarModifierRow:
    row = await ctx.session.get(StarModifierRow, modifier_id)
    if row is None:
        raise NotFoundError("No such change to a star's light.")
    return row


async def edit_star_modifier(ctx: TickContext, modifier_id: int, values: Mapping[str, Any], release: list[str]) -> StarModifierRow:
    row = await require_star_modifier(ctx, modifier_id)
    allowed(values, STAR_MODIFIER_FIELDS, "change to a star's light")
    apply(row, values, release)
    await ctx.session.flush()
    return row


async def remove_star_modifier(ctx: TickContext, modifier_id: int) -> None:
    await ctx.session.delete(await require_star_modifier(ctx, modifier_id))
    await ctx.session.flush()
