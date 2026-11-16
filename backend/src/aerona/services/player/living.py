from pydantic import BaseModel, Field

from aerona.core.errors import ValidationFailedError
from aerona.core.grammar import an
from aerona.db.base import Base
from aerona.db.tables.living import GeneBankRow, GeneBankSampleRow, LivingLineSourceRow, LivingLineTraitRow, LivingProfileRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.living import CultivationMethod, Fertility, HostPlacement, HostRelation, LineTrait, Metabolism
from aerona.engine.living import control
from aerona.engine.living.kin import clone, line_of, remove_symbiont
from aerona.engine.living.lines import LineDraft, make_line
from aerona.engine.powers.control import add_part, delete_part, edit_fields, edit_part, part_table
from aerona.services.player.cosmography import Edited
from aerona.services.player.powers import PartCreate, PartEdit, PartTarget, typed
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

PERCENT = 100
NAME = Field(min_length=1, max_length=120)
LINE_PARTS: dict[str, type[Base]] = {"trait": LivingLineTraitRow, "source": LivingLineSourceRow}
BANK_PARTS: dict[str, type[Base]] = {"sample": GeneBankSampleRow}
LINE_FIELDS = {
    "name",
    "method",
    "outcome",
    "stability",
    "generation",
    "drift_pct",
    "fertility",
    "metabolism",
    "owner_node_id",
    "maker_node_id",
    "species_entity_id",
    "licensed",
    "escaped",
}
LIFE_FIELDS = {
    "line_id",
    "metabolism",
    "feed_commodity",
    "feed_per_season",
    "growth_stage",
    "size_pct",
    "regeneration",
    "health",
    "temperament",
    "bonded_to_node_id",
    "bond",
    "fertility",
    "lifespan_years",
    "age_seasons",
    "designed_by_node_id",
}
BANK_FIELDS = {"holder_node_id", "upkeep", "unpaid_epochs"}
SYMBIONT_FIELDS = {"line_id", "mind_node_id", "placement", "relation", "strength"}


class TraitPick(BaseModel):
    trait: LineTrait
    strength: int = Field(default=30, ge=-PERCENT, le=PERCENT)


class LineCreate(Command):
    name: str = NAME
    method: CultivationMethod = CultivationMethod.SELECTIVE_BREEDING
    maker_id: int
    owner_id: int | None = None
    source_ids: list[int] = Field(default_factory=list)
    traits: list[TraitPick] = Field(default_factory=list)
    fertility: Fertility = Fertility.BREEDS_TRUE


class LineTarget(Command):
    line_id: int


class LineEdit(Edited):
    line_id: int
    hold: bool = False


class LifeGive(Command):
    thing_id: int
    line_id: int | None = None
    metabolism: Metabolism = Metabolism.FEEDING
    lifespan: int = Field(default=40, ge=1, le=100000)
    bonded_to: int | None = None


class LifeTarget(Command):
    thing_id: int


class LifeEdit(Edited):
    thing_id: int
    hold: bool = False


class BankCreate(Command):
    structure_id: int
    holder_id: int | None = None


class BankTarget(Command):
    structure_id: int


class BankEdit(Edited):
    structure_id: int
    hold: bool = False


class SampleRaise(Command):
    sample_id: int
    maker_id: int


class SymbiontCreate(Command):
    host_id: int
    line_id: int | None = None
    placement: HostPlacement = HostPlacement.SKIN
    relation: HostRelation = HostRelation.MUTUAL
    strength: int = Field(default=30, ge=0, le=PERCENT)


class SymbiontTarget(Command):
    symbiont_id: int


class SymbiontEdit(Edited):
    symbiont_id: int
    hold: bool = False


class CloneCommand(Command):
    source_id: int
    maker_id: int | None = None


@player_action("line:create", ActionKind.EDIT_RECORD)
async def line_create(scope: PlayerScope, command: LineCreate) -> Effect:
    draft = LineDraft(
        command.name,
        command.method,
        command.maker_id,
        command.owner_id,
        tuple(command.source_ids),
        tuple((pick.trait, pick.strength) for pick in command.traits),
        command.fertility,
    )
    row = await make_line(await scope.context("line_create"), draft, forced=True)
    return Effect(f"{row.name} is a living line now.", command.maker_id, values={"line_id": row.id})


@player_action("line:edit", ActionKind.EDIT_RECORD)
async def line_edit(scope: PlayerScope, command: LineEdit) -> Effect:
    row = await line_of(await scope.context("line_edit"), command.line_id)
    changed = await edit_fields(row, typed(type(row), command.values), command.hold, command.release, LINE_FIELDS)
    return Effect(f"{row.name}: {', '.join(changed) or 'nothing'} set.", row.owner_node_id)


@player_action("line:delete", ActionKind.EDIT_RECORD)
async def line_delete(scope: PlayerScope, command: LineTarget) -> Effect:
    ctx = await scope.context("line_delete")
    row = await line_of(ctx, command.line_id)
    await ctx.session.delete(row)
    return Effect(f"{row.name} is unmade.", row.owner_node_id)


@player_action("line:escape", ActionKind.EDIT_RECORD)
async def line_release(scope: PlayerScope, command: LineTarget) -> Effect:
    ctx = await scope.context("line_release")
    row = await control.release(ctx, await line_of(ctx, command.line_id))
    return Effect(f"{row.name} runs wild now.", row.species_entity_id)


@player_action("line:contain", ActionKind.EDIT_RECORD)
async def line_contain(scope: PlayerScope, command: LineTarget) -> Effect:
    ctx = await scope.context("line_contain")
    row = await control.contain(ctx, await line_of(ctx, command.line_id))
    return Effect(f"{row.name} is held in again.", row.owner_node_id)


@player_action("line_part:create", ActionKind.EDIT_RECORD)
async def line_part_create(scope: PlayerScope, command: PartCreate) -> Effect:
    ctx = await scope.context("line_part_create")
    await line_of(ctx, command.owner_id)
    row = await add_part(ctx, LINE_PARTS, command.part, command.owner_id, typed(part_table(command.part, LINE_PARTS), command.values))
    return Effect(f"The line gains {an(command.part)}.", values={"part_id": int(getattr(row, "id", 0))})


@player_action("line_part:edit", ActionKind.EDIT_RECORD)
async def line_part_edit(scope: PlayerScope, command: PartEdit) -> Effect:
    values = typed(part_table(command.part, LINE_PARTS), command.values)
    await edit_part(await scope.context("line_part_edit"), LINE_PARTS, command.part, command.part_id, values, hold=command.hold, release=command.release)
    return Effect(f"The {command.part} of the line is set.")


@player_action("line_part:delete", ActionKind.EDIT_RECORD)
async def line_part_delete(scope: PlayerScope, command: PartTarget) -> Effect:
    await delete_part(await scope.context("line_part_delete"), LINE_PARTS, command.part, command.part_id)
    return Effect(f"The {command.part} is taken from the line.")


@player_action("living:create", ActionKind.EDIT_RECORD)
async def life_give(scope: PlayerScope, command: LifeGive) -> Effect:
    ctx = await scope.context("life_give")
    await control.give_life(
        ctx, command.thing_id, line_id=command.line_id, metabolism=command.metabolism, lifespan=command.lifespan, bonded_to=command.bonded_to
    )
    return Effect("It lives.", command.thing_id)


@player_action("living:edit", ActionKind.EDIT_RECORD)
async def life_edit(scope: PlayerScope, command: LifeEdit) -> Effect:
    ctx = await scope.context("life_edit")
    row = await ctx.session.get(LivingProfileRow, command.thing_id)
    if row is None:
        raise ValidationFailedError("That is not alive.")
    changed = await edit_fields(row, typed(type(row), command.values), command.hold, command.release, LIFE_FIELDS)
    return Effect(f"Its life: {', '.join(changed) or 'nothing'} set.", command.thing_id)


@player_action("living:delete", ActionKind.EDIT_RECORD)
async def life_delete(scope: PlayerScope, command: LifeTarget) -> Effect:
    ctx = await scope.context("life_delete")
    row = await ctx.session.get(LivingProfileRow, command.thing_id)
    if row is None:
        raise ValidationFailedError("That is not alive.")
    await ctx.session.delete(row)
    return Effect("It is no longer a living thing, and nothing is lost of it.", command.thing_id)


@player_action("living:end", ActionKind.EDIT_RECORD)
async def life_end(scope: PlayerScope, command: LifeTarget) -> Effect:
    await control.end_life(await scope.context("life_end"), command.thing_id)
    return Effect("Its life ends.", command.thing_id)


@player_action("clone:create", ActionKind.EDIT_RECORD)
async def life_clone(scope: PlayerScope, command: CloneCommand) -> Effect:
    row = await clone(await scope.context("life_clone"), command.source_id, command.maker_id, forced=True)
    return Effect(f"{row.name} is grown.", row.id, values={"clone_id": row.id})


@player_action("bank:create", ActionKind.EDIT_RECORD)
async def bank_create(scope: PlayerScope, command: BankCreate) -> Effect:
    await control.found_bank(await scope.context("bank_create"), command.structure_id, command.holder_id)
    return Effect("A bank of life is kept there now.", command.structure_id)


@player_action("bank:edit", ActionKind.EDIT_RECORD)
async def bank_edit(scope: PlayerScope, command: BankEdit) -> Effect:
    ctx = await scope.context("bank_edit")
    row = await ctx.session.get(GeneBankRow, command.structure_id)
    if row is None:
        raise ValidationFailedError("No bank of life is kept there.")
    changed = await edit_fields(row, typed(type(row), command.values), command.hold, command.release, BANK_FIELDS)
    return Effect(f"The bank: {', '.join(changed) or 'nothing'} set.", command.structure_id)


@player_action("bank:delete", ActionKind.EDIT_RECORD)
async def bank_delete(scope: PlayerScope, command: BankTarget) -> Effect:
    ctx = await scope.context("bank_delete")
    row = await ctx.session.get(GeneBankRow, command.structure_id)
    if row is None:
        raise ValidationFailedError("No bank of life is kept there.")
    await ctx.session.delete(row)
    return Effect("The bank of life is emptied and closed.", command.structure_id)


@player_action("sample:create", ActionKind.EDIT_RECORD)
async def bank_part_create(scope: PlayerScope, command: PartCreate) -> Effect:
    ctx = await scope.context("bank_part_create")
    if await ctx.session.get(GeneBankRow, command.owner_id) is None:
        raise ValidationFailedError("No bank of life is kept there.")
    values = {"taken_epoch": ctx.epoch, **typed(part_table(command.part, BANK_PARTS), command.values)}
    row = await add_part(ctx, BANK_PARTS, command.part, command.owner_id, values)
    return Effect(f"The bank keeps {an(command.part)} more.", command.owner_id, values={"part_id": int(getattr(row, "id", 0))})


@player_action("sample:edit", ActionKind.EDIT_RECORD)
async def bank_part_edit(scope: PlayerScope, command: PartEdit) -> Effect:
    values = typed(part_table(command.part, BANK_PARTS), command.values)
    await edit_part(await scope.context("bank_part_edit"), BANK_PARTS, command.part, command.part_id, values, hold=command.hold, release=command.release)
    return Effect(f"The {command.part} in the bank is set.")


@player_action("sample:delete", ActionKind.EDIT_RECORD)
async def bank_part_delete(scope: PlayerScope, command: PartTarget) -> Effect:
    await delete_part(await scope.context("bank_part_delete"), BANK_PARTS, command.part, command.part_id)
    return Effect(f"The {command.part} is taken from the bank.")


@player_action("sample:raise", ActionKind.EDIT_RECORD)
async def sample_raise(scope: PlayerScope, command: SampleRaise) -> Effect:
    row = await control.raise_line(await scope.context("sample_raise"), command.sample_id, command.maker_id)
    return Effect(f"{row.name} is raised from what the bank kept.", command.maker_id, values={"line_id": row.id})


@player_action("symbiont:host", ActionKind.EDIT_RECORD)
async def symbiont_create(scope: PlayerScope, command: SymbiontCreate) -> Effect:
    ctx = await scope.context("symbiont_create")
    row = await control.host(ctx, command.host_id, line_id=command.line_id, placement=command.placement, relation=command.relation, strength=command.strength)
    return Effect("Something lives within it now.", command.host_id, values={"symbiont_id": row.id})


@player_action("symbiont:edit", ActionKind.EDIT_RECORD)
async def symbiont_edit(scope: PlayerScope, command: SymbiontEdit) -> Effect:
    row = await control.symbiont_of(await scope.context("symbiont_edit"), command.symbiont_id)
    changed = await edit_fields(row, typed(type(row), command.values), command.hold, command.release, SYMBIONT_FIELDS)
    return Effect(f"What lives within: {', '.join(changed) or 'nothing'} set.", row.host_node_id)


@player_action("symbiont:remove", ActionKind.EDIT_RECORD)
async def symbiont_delete(scope: PlayerScope, command: SymbiontTarget) -> Effect:
    ctx = await scope.context("symbiont_delete")
    row = await control.symbiont_of(ctx, command.symbiont_id)
    await remove_symbiont(ctx, row)
    return Effect("What lived within is taken out.", row.host_node_id)
