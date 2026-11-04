from collections.abc import Mapping

from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.culture import HolderCustomTechniqueRow, HolderLevelRow, IdeologyCustomTenetRow, IdeologyProfileRow, IdeologyTenetRow
from aerona.domain.enums.culture import CustomCatalog, IdeologyTenet
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityType
from aerona.domain.enums.society import KnowledgeBranch
from aerona.engine.context import TickContext
from aerona.engine.lore import ideology
from aerona.engine.lore.kinds import TenetParams, kind_of, params_of
from aerona.engine.polity.control import lock
from aerona.engine.primitives.queries import living_entity

HOLDER_FIELDS = {"level": (0, None), "practitioners": (0, None), "progress": (0, PERCENT)}
HOLDER_FLAGS = frozenset({"secret"})


async def holder(ctx: TickContext, holder_id: int) -> None:
    entity = await living_entity(ctx.session, holder_id)
    if entity is None or entity.entity_type not in {*COMMUNITY_TYPES, EntityType.POLITY}:
        raise NotFoundError("No such living community.")


async def edit_holder(ctx: TickContext, holder_id: int, branch: KnowledgeBranch, values: Mapping[str, int | bool], release: list[str]) -> HolderLevelRow:
    await holder(ctx, holder_id)
    row = await ctx.session.get(HolderLevelRow, (holder_id, branch))
    if row is None:
        row = HolderLevelRow(holder_entity_id=holder_id, branch=branch, level=0, practitioners=0, progress=0, secret=False, updated_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    for key, value in values.items():
        if key in HOLDER_FLAGS:
            if not isinstance(value, bool):
                raise ValidationFailedError(f"{key.capitalize()} is yes or no.")
        elif key in HOLDER_FIELDS:
            low, high = HOLDER_FIELDS[key]
            if isinstance(value, bool) or not isinstance(value, int) or value < low or (high is not None and value > high):
                raise ValidationFailedError(f"{key.capitalize()} runs from {low} to {high if high is not None else 'any height'}.")
        else:
            raise ValidationFailedError(f"{key.capitalize()} cannot be set here.")
        setattr(row, key, value)
        row.locked = lock(row.locked, key)
    row.locked = [key for key in row.locked if key not in release]
    await ctx.session.flush()
    return row


async def set_custom_technique(ctx: TickContext, holder_id: int, kind_id: int, *, held: bool, secret: bool) -> HolderCustomTechniqueRow | None:
    await holder(ctx, holder_id)
    if await kind_of(ctx.session, kind_id, CustomCatalog.TECHNIQUE) is None:
        raise NotFoundError("No such technique of your own making.")
    row = await ctx.session.get(HolderCustomTechniqueRow, (holder_id, kind_id))
    if not held:
        if row is not None:
            await ctx.session.delete(row)
            await ctx.session.flush()
        return None
    if row is None:
        row = HolderCustomTechniqueRow(holder_entity_id=holder_id, kind_id=kind_id, since_epoch=ctx.epoch, secret=secret)
        ctx.session.add(row)
    row.secret = secret
    await ctx.session.flush()
    return row


async def creed_of(ctx: TickContext, ideology_id: int) -> IdeologyProfileRow:
    entity = await living_entity(ctx.session, ideology_id)
    row = await ctx.session.get(IdeologyProfileRow, ideology_id) if entity is not None else None
    if entity is None or row is None or entity.entity_type is not EntityType.IDEOLOGY:
        raise NotFoundError("No such living creed.")
    return row


async def set_custom_tenet(ctx: TickContext, ideology_id: int, kind_id: int, *, held: bool) -> IdeologyCustomTenetRow | None:
    profile = await creed_of(ctx, ideology_id)
    custom = await kind_of(ctx.session, kind_id, CustomCatalog.TENET)
    if custom is None:
        raise NotFoundError("No such tenet of your own making.")
    params = params_of(custom, TenetParams)
    row = await ctx.session.get(IdeologyCustomTenetRow, (ideology_id, kind_id))
    sign = 1 if held else -1
    if held == (row is not None):
        return row
    for axis, value in params.values.items():
        key = str(axis)
        profile.value_delta = {**profile.value_delta, key: profile.value_delta.get(key, 0) + sign * value}
    for social_class, value in params.appeal.items():
        key = str(social_class)
        profile.appeal = {**profile.appeal, key: max(0, profile.appeal.get(key, 0) + sign * value)}
    base = IdeologyTenet(custom.base)
    if held:
        row = IdeologyCustomTenetRow(ideology_entity_id=ideology_id, kind_id=kind_id)
        ctx.session.add(row)
        if await ctx.session.get(IdeologyTenetRow, (ideology_id, base)) is None:
            ctx.session.add(IdeologyTenetRow(ideology_entity_id=ideology_id, tenet=base))
    elif row is not None:
        await ctx.session.delete(row)
        row = None
    profile.locked = lock(lock(profile.locked, "value_delta"), "appeal")
    await ctx.session.flush()
    return row


async def suppress_creed(ctx: TickContext, ideology_id: int, authority_id: int | None) -> int:
    await creed_of(ctx, ideology_id)
    entity = await living_entity(ctx.session, ideology_id)
    assert entity is not None
    count = await ideology.suppress(ctx, entity, authority_id)
    await ctx.session.flush()
    return count
