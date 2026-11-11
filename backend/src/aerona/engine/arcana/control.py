from sqlalchemy import select

from aerona.core.errors import ValidationFailedError
from aerona.db.tables.afflictions import AfflictionRow
from aerona.db.tables.arcana import (
    GRAMMAR_FIELDS,
    LAB_TEXT_FIELDS,
    LONGEVITY_FIELDS,
    UPKEEP_FIELDS,
    WARPING_FIELDS,
    LabTextRow,
    LawUpkeepRow,
    LongevityRow,
    RiteGrammarRow,
    VisStockRow,
    WarpingRow,
)
from aerona.db.tables.culture import ItemEnchantmentRow, RiteProfileRow
from aerona.db.tables.divine import NaturalLawProfileRow
from aerona.domain.enums.affliction import PackageKind
from aerona.domain.enums.arcana import RechargeRule, SpellForm
from aerona.domain.enums.culture import RiteEffectKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.society import NaturalLaw
from aerona.engine.arcana.enchantments import lay_enchantment, upkeep_row
from aerona.engine.arcana.grammar import difficulty_of, ensure_grammar, shape_of
from aerona.engine.arcana.labs import write_lab_text
from aerona.engine.arcana.longevity import begin_longevity, end_longevity
from aerona.engine.arcana.warping import settle_stage, warp_row
from aerona.engine.body.afflictions import cure
from aerona.engine.context import TickContext
from aerona.engine.divine.control import apply
from aerona.engine.gatherings.control import Values, allowed, entity, found, node
from aerona.engine.primitives.numbers import clamp_int

CHARGE_FIELDS = ("charges", "capacity", "recharge", "overuse")


async def rite_profile(ctx: TickContext, rite_id: int) -> RiteProfileRow:
    return await found(ctx, RiteProfileRow, rite_id, "rite")


async def edit_grammar(ctx: TickContext, rite_id: int, values: Values, release: list[str]) -> RiteGrammarRow:
    profile = await rite_profile(ctx, rite_id)
    row = apply(await ensure_grammar(ctx.session, ctx.rules, profile), allowed(values, GRAMMAR_FIELDS, "rite grammar"), release)
    row.difficulty = difficulty_of(ctx.rules, shape_of(row), profile.power)
    await ctx.session.flush()
    return row


async def delete_grammar(ctx: TickContext, rite_id: int) -> RiteGrammarRow:
    profile = await rite_profile(ctx, rite_id)
    current = await ctx.session.get(RiteGrammarRow, rite_id)
    if current is not None:
        await ctx.session.delete(current)
        await ctx.session.flush()
    return await ensure_grammar(ctx.session, ctx.rules, profile)


async def write_text(ctx: TickContext, rite_id: int, author_id: int) -> LabTextRow:
    rite = await entity(ctx, rite_id, "rite")
    author = await entity(ctx, author_id, "author")
    await rite_profile(ctx, rite_id)
    row = await write_lab_text(ctx, rite, author)
    if row is None:
        raise ValidationFailedError("Only a mortal mage sets down lab texts.")
    return row


async def edit_text(ctx: TickContext, book_id: int, values: Values, release: list[str]) -> LabTextRow:
    row = apply(await found(ctx, LabTextRow, book_id, "lab text"), allowed(values, LAB_TEXT_FIELDS, "lab text"), release)
    await ctx.session.flush()
    return row


async def delete_text(ctx: TickContext, book_id: int) -> None:
    await ctx.session.delete(await found(ctx, LabTextRow, book_id, "lab text"))
    await ctx.session.flush()


async def set_vis(ctx: TickContext, holder_id: int, form: SpellForm, amount: int, *, hold: bool) -> VisStockRow:
    await node(ctx, holder_id, "holder")
    row = await ctx.session.get(VisStockRow, (holder_id, form))
    if row is None:
        row = VisStockRow(holder_node_id=holder_id, form=form, amount=0, locked=[])
        ctx.session.add(row)
    apply(row, {"amount": max(0, amount)}, [] if hold else ["amount"])
    await ctx.session.flush()
    return row


async def delete_vis(ctx: TickContext, holder_id: int, form: SpellForm) -> None:
    await ctx.session.delete(await found(ctx, VisStockRow, (holder_id, form), "vis"))
    await ctx.session.flush()


async def edit_warping(ctx: TickContext, node_id: int, values: Values, release: list[str]) -> WarpingRow:
    bearer = await entity(ctx, node_id, "bearer")
    row = apply(await warp_row(ctx, bearer.id), allowed(values, WARPING_FIELDS, "warping"), release)
    await ctx.session.flush()
    await settle_stage(ctx, bearer, row)
    await ctx.session.flush()
    return row


async def delete_warping(ctx: TickContext, node_id: int) -> None:
    bearer = await entity(ctx, node_id, "bearer")
    await ctx.session.delete(await found(ctx, WarpingRow, node_id, "warping"))
    warped = await ctx.session.scalar(
        select(AfflictionRow).where(AfflictionRow.bearer_node_id == node_id, AfflictionRow.package == PackageKind.WARPING, AfflictionRow.cured_epoch.is_(None))
    )
    if warped is not None:
        await cure(ctx, bearer, warped, None)
    await ctx.session.flush()


async def start_longevity(ctx: TickContext, mortal_id: int, form: SpellForm) -> LongevityRow:
    mortal = await entity(ctx, mortal_id, "mortal")
    if mortal.entity_type is not EntityType.MORTAL:
        raise ValidationFailedError("Only a mortal can take longevity magic.")
    row = await begin_longevity(ctx, mortal, form)
    if row is None:
        raise ValidationFailedError(f"{mortal.name} cannot take longevity magic now.")
    return row


async def edit_longevity(ctx: TickContext, mortal_id: int, values: Values, release: list[str]) -> LongevityRow:
    row = apply(await found(ctx, LongevityRow, mortal_id, "longevity"), allowed(values, LONGEVITY_FIELDS, "longevity"), release)
    await ctx.session.flush()
    return row


async def stop_longevity(ctx: TickContext, mortal_id: int) -> None:
    mortal = await entity(ctx, mortal_id, "mortal")
    await end_longevity(ctx, mortal, await found(ctx, LongevityRow, mortal_id, "longevity"))
    await ctx.session.flush()


async def lay(
    ctx: TickContext, caster_id: int, *, name: str, effect: NaturalLaw, world_id: int | None, region_id: int | None, strength: int, vis_form: SpellForm | None
) -> NaturalLawProfileRow:
    await node(ctx, caster_id, "caster")
    if region_id is not None:
        region = await entity(ctx, region_id, "region")
        world_id = region.world_id
    return await lay_enchantment(
        ctx, caster_id, name=name.strip() or effect.value, effect=effect, world_id=world_id, region_id=region_id, strength=strength, vis_form=vis_form
    )


async def edit_upkeep(ctx: TickContext, law_id: int, values: Values, release: list[str]) -> LawUpkeepRow:
    law = await found(ctx, NaturalLawProfileRow, law_id, "law")
    row = await upkeep_row(ctx.session, ctx.rules, law)
    if row is None:
        row = LawUpkeepRow(law_entity_id=law_id, locked=[])
        ctx.session.add(row)
    apply(row, allowed(values, UPKEEP_FIELDS, "upkeep"), release)
    await ctx.session.flush()
    return row


async def delete_upkeep(ctx: TickContext, law_id: int) -> None:
    await ctx.session.delete(await found(ctx, LawUpkeepRow, law_id, "upkeep"))
    await ctx.session.flush()


async def dispel_law(ctx: TickContext, law_id: int) -> None:
    law = await entity(ctx, law_id, "law")
    if law.status is not EntityStatus.CANON:
        raise ValidationFailedError(f"{law.name} no longer holds.")
    law.status, law.end_epoch = EntityStatus.DESTROYED, ctx.epoch
    await ctx.session.flush()


async def edit_charges(ctx: TickContext, item_id: int, effect: RiteEffectKind, values: Values) -> ItemEnchantmentRow:
    row = await found(ctx, ItemEnchantmentRow, (item_id, effect), "enchantment")
    for key, value in allowed(values, CHARGE_FIELDS, "enchantment").items():
        setattr(row, key, RechargeRule(value) if key == "recharge" else clamp_int(int(value), 0, 1000))
    row.charges = min(row.charges, row.capacity)
    await ctx.session.flush()
    return row
