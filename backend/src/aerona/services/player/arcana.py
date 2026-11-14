from pydantic import Field

from aerona.constants.schema import NAME_MAX_LENGTH
from aerona.core.grammar import several
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.arcana import SpellForm
from aerona.domain.enums.culture import RiteEffectKind
from aerona.domain.enums.society import NaturalLaw
from aerona.engine.arcana import control
from aerona.services.player.cosmography import Edited
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

SPAN = 100


class RiteEdit(Edited):
    rite_id: int


class RiteTarget(Command):
    rite_id: int


class TextDraft(Command):
    rite_id: int
    author_id: int


class TextEdit(Edited):
    book_id: int


class TextTarget(Command):
    book_id: int


class VisSet(Command):
    holder_id: int
    form: SpellForm
    amount: int = Field(ge=0, le=100000)
    hold: bool = True


class VisTarget(Command):
    holder_id: int
    form: SpellForm


class BearerEdit(Edited):
    node_id: int


class BearerTarget(Command):
    node_id: int


class LongevityDraft(Command):
    mortal_id: int
    form: SpellForm


class LongevityEdit(Edited):
    mortal_id: int


class LongevityTarget(Command):
    mortal_id: int


class EnchantmentDraft(Command):
    caster_id: int
    name: str = Field(default="", max_length=NAME_MAX_LENGTH)
    effect: NaturalLaw
    world_id: int | None = None
    region_id: int | None = None
    strength: int = Field(default=60, ge=0, le=SPAN)
    vis_form: SpellForm | None = None


class LawEdit(Edited):
    law_id: int


class LawTarget(Command):
    law_id: int


class ChargeEdit(Edited):
    item_id: int
    effect: RiteEffectKind


@player_action("rite_grammar:edit", ActionKind.EDIT_RECORD)
async def edit_grammar(scope: PlayerScope, command: RiteEdit) -> Effect:
    await control.edit_grammar(await scope.context("rite_grammar_edit"), command.rite_id, command.values, command.release)
    return Effect("The rite's grammar is set so.", command.rite_id)


@player_action("rite_grammar:delete", ActionKind.EDIT_RECORD)
async def delete_grammar(scope: PlayerScope, command: RiteTarget) -> Effect:
    await control.delete_grammar(await scope.context("rite_grammar_delete"), command.rite_id)
    return Effect("The rite's grammar returns to that of its school.", command.rite_id)


@player_action("lab_text:write", ActionKind.EDIT_RECORD)
async def write_text(scope: PlayerScope, command: TextDraft) -> Effect:
    row = await control.write_text(await scope.context("lab_text_write"), command.rite_id, command.author_id)
    return Effect("A lab text of the rite is written.", command.author_id, values={"book_id": row.book_entity_id})


@player_action("lab_text:edit", ActionKind.EDIT_RECORD)
async def edit_text(scope: PlayerScope, command: TextEdit) -> Effect:
    await control.edit_text(await scope.context("lab_text_edit"), command.book_id, command.values, command.release)
    return Effect("The lab text is set so.", command.book_id)


@player_action("lab_text:delete", ActionKind.EDIT_RECORD)
async def delete_text(scope: PlayerScope, command: TextTarget) -> Effect:
    await control.delete_text(await scope.context("lab_text_delete"), command.book_id)
    return Effect("The book no longer teaches its rite.", command.book_id)


@player_action("vis:set", ActionKind.EDIT_RECORD)
async def set_vis(scope: PlayerScope, command: VisSet) -> Effect:
    row = await control.set_vis(await scope.context("vis_set"), command.holder_id, command.form, command.amount, hold=command.hold)
    return Effect(f"{row.amount} {row.form.value} vis is held.", command.holder_id)


@player_action("vis:delete", ActionKind.EDIT_RECORD)
async def delete_vis(scope: PlayerScope, command: VisTarget) -> Effect:
    await control.delete_vis(await scope.context("vis_delete"), command.holder_id, command.form)
    return Effect("The vis is gone.", command.holder_id)


@player_action("warping:edit", ActionKind.EDIT_RECORD)
async def edit_warping(scope: PlayerScope, command: BearerEdit) -> Effect:
    await control.edit_warping(await scope.context("warping_edit"), command.node_id, command.values, command.release)
    return Effect("The warping is set so.", command.node_id)


@player_action("warping:delete", ActionKind.EDIT_RECORD)
async def delete_warping(scope: PlayerScope, command: BearerTarget) -> Effect:
    await control.delete_warping(await scope.context("warping_delete"), command.node_id)
    return Effect("The warping is undone.", command.node_id)


@player_action("longevity:begin", ActionKind.EDIT_RECORD)
async def begin_longevity(scope: PlayerScope, command: LongevityDraft) -> Effect:
    await control.start_longevity(await scope.context("longevity_begin"), command.mortal_id, command.form)
    return Effect("Longevity magic slows this mortal's ageing.", command.mortal_id)


@player_action("longevity:edit", ActionKind.EDIT_RECORD)
async def edit_longevity(scope: PlayerScope, command: LongevityEdit) -> Effect:
    await control.edit_longevity(await scope.context("longevity_edit"), command.mortal_id, command.values, command.release)
    return Effect("The longevity is set so.", command.mortal_id)


@player_action("longevity:end", ActionKind.EDIT_RECORD)
async def end_longevity(scope: PlayerScope, command: LongevityTarget) -> Effect:
    await control.stop_longevity(await scope.context("longevity_end"), command.mortal_id)
    return Effect("The longevity magic ends.", command.mortal_id)


@player_action("enchantment:lay", ActionKind.EDIT_RECORD)
async def lay_enchantment(scope: PlayerScope, command: EnchantmentDraft) -> Effect:
    row = await control.lay(
        await scope.context("enchantment_lay"),
        command.caster_id,
        name=command.name,
        effect=command.effect,
        world_id=command.world_id,
        region_id=command.region_id,
        strength=command.strength,
        vis_form=command.vis_form,
    )
    return Effect("A global enchantment is laid.", row.law_entity_id, values={"law_id": row.law_entity_id})


@player_action("law_upkeep:edit", ActionKind.EDIT_RECORD)
async def edit_upkeep(scope: PlayerScope, command: LawEdit) -> Effect:
    await control.edit_upkeep(await scope.context("law_upkeep_edit"), command.law_id, command.values, command.release)
    return Effect("The law's upkeep is set so.", command.law_id)


@player_action("law_upkeep:delete", ActionKind.EDIT_RECORD)
async def delete_upkeep(scope: PlayerScope, command: LawTarget) -> Effect:
    await control.delete_upkeep(await scope.context("law_upkeep_delete"), command.law_id)
    return Effect("The law no longer asks an upkeep.", command.law_id)


@player_action("enchantment:dispel", ActionKind.EDIT_RECORD)
async def dispel_enchantment(scope: PlayerScope, command: LawTarget) -> Effect:
    await control.dispel_law(await scope.context("enchantment_dispel"), command.law_id)
    return Effect("The enchantment is dispelled.", command.law_id)


@player_action("item_charge:edit", ActionKind.EDIT_RECORD)
async def edit_charges(scope: PlayerScope, command: ChargeEdit) -> Effect:
    row = await control.edit_charges(await scope.context("item_charge_edit"), command.item_id, command.effect, command.values)
    return Effect(f"The enchantment holds {row.charges} of {several(row.capacity, 'charge', 'charges')}.", command.item_id)
