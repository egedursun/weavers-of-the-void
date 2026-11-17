from collections.abc import Mapping

from aerona.catalog.techniques import INSTITUTIONS
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.grammar import spoken
from aerona.db.tables.culture import InstitutionRow, ResearchBoostRow, ResearchFocusRow
from aerona.domain.enums.culture import BoostTrigger, ResearchChooser, Technique
from aerona.engine.context import TickContext
from aerona.engine.lore.learning_control import holder
from aerona.engine.lore.research_depth import add_progress
from aerona.engine.polity.control import lock

INSTITUTION_FLAGS = frozenset({"origin", "embraced"})
INSTITUTION_COUNTS = frozenset({"refused_epochs", "since_epoch"})


async def set_focus(ctx: TickContext, holder_id: int, technique: Technique | None, options: list[Technique] | None, *, hold: bool) -> ResearchFocusRow | None:
    await holder(ctx, holder_id)
    row = await ctx.session.get(ResearchFocusRow, holder_id)
    if technique is None:
        if row is not None:
            await ctx.session.delete(row)
            await ctx.session.flush()
        return None
    if row is None:
        row = ResearchFocusRow(holder_entity_id=holder_id, technique=technique, chooser=ResearchChooser.GOD, options=[], epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    row.technique, row.chooser, row.epoch = technique, ResearchChooser.GOD, ctx.epoch
    if options is not None:
        row.options = [item.value for item in dict.fromkeys([technique, *options])]
    elif technique.value not in row.options:
        row.options = [technique.value, *row.options]
    row.locked = lock(row.locked, "technique") if hold else [key for key in row.locked if key != "technique"]
    await ctx.session.flush()
    return row


async def set_institution(
    ctx: TickContext, community_id: int, technique: Technique, values: Mapping[str, int | bool], release: list[str], *, present: bool
) -> InstitutionRow | None:
    await holder(ctx, community_id)
    if technique not in INSTITUTIONS:
        raise ValidationFailedError(f"{spoken(technique).capitalize()} is a technique, not an institution.")
    row = await ctx.session.get(InstitutionRow, (technique, community_id))
    if not present:
        if row is not None:
            await ctx.session.delete(row)
            await ctx.session.flush()
        return None
    if row is None:
        row = InstitutionRow(
            technique=technique, community_entity_id=community_id, origin=False, embraced=True, since_epoch=ctx.epoch, refused_epochs=0, locked=[]
        )
        ctx.session.add(row)
    for key, value in values.items():
        if key in INSTITUTION_FLAGS:
            if not isinstance(value, bool):
                raise ValidationFailedError(f"{key.capitalize()} is yes or no.")
        elif key in INSTITUTION_COUNTS:
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValidationFailedError(f"{key.replace('_', ' ').capitalize()} is a whole number of epochs, 0 or more.")
        else:
            raise ValidationFailedError(f"{key.replace('_', ' ').capitalize()} cannot be set here.")
        setattr(row, key, value)
        row.locked = lock(row.locked, key)
    row.locked = [key for key in row.locked if key not in release]
    await ctx.session.flush()
    return row


async def grant_boost(ctx: TickContext, holder_id: int, technique: Technique, trigger: BoostTrigger, progress: int) -> ResearchBoostRow:
    await holder(ctx, holder_id)
    if not 0 < progress < PERCENT:
        raise ValidationFailedError(f"A boost pushes research between 1 and {PERCENT - 1}%.")
    await add_progress(ctx, holder_id, technique, progress)
    row = ResearchBoostRow(holder_entity_id=holder_id, technique=technique, trigger=trigger, progress=progress, epoch=ctx.epoch)
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def edit_boost(ctx: TickContext, boost_id: int, values: Mapping[str, int | str]) -> ResearchBoostRow:
    row = await ctx.session.get(ResearchBoostRow, boost_id)
    if row is None:
        raise NotFoundError("No such boost.")
    for key, value in values.items():
        if key == "progress" and isinstance(value, int) and not isinstance(value, bool) and 0 < value < PERCENT:
            row.progress = value
        elif key == "technique" and isinstance(value, str) and value in Technique._value2member_map_:
            row.technique = Technique(value)
        elif key == "trigger" and isinstance(value, str) and value in BoostTrigger._value2member_map_:
            row.trigger = BoostTrigger(value)
        elif key == "epoch" and isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            row.epoch = value
        else:
            raise ValidationFailedError(f"{key.capitalize()} cannot take that value.")
    await ctx.session.flush()
    return row


async def remove_boost(ctx: TickContext, boost_id: int) -> None:
    row = await ctx.session.get(ResearchBoostRow, boost_id)
    if row is None:
        raise NotFoundError("No such boost.")
    await ctx.session.delete(row)
    await ctx.session.flush()
