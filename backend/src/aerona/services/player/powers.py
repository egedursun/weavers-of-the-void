from typing import Any

from pydantic import Field
from sqlalchemy import inspect

from aerona.core.errors import ValidationFailedError
from aerona.core.grammar import an
from aerona.db.base import Base
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.arcana import SpellForm, SpellTechnique
from aerona.domain.enums.concealment import BreachCause, ConcealScope, HiddenTruthKind
from aerona.domain.enums.powers import (
    Learnability,
    PowerOrigin,
    PowerState,
    PowerStructure,
    PowerVisibility,
    SourceAccess,
    SourceLocus,
    SourceRenewal,
)
from aerona.engine.powers import control
from aerona.services.player.cosmography import Edit, Edited
from aerona.services.player.profiles import ScalarValue, coerce
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

PERCENT = 100
NAME = Field(min_length=1, max_length=120)
SOURCE_FIELDS = {"name", "description", "scope_node_id", "drawn_from", "renewal", "access", "visibility", "stability"}
SYSTEM_FIELDS = {"name", "description", "structure", "predictability", "prevalence", "cost_severity", "visibility", "access", "learnability"}
POWER_FIELDS = {
    "system_id",
    "source_id",
    "technique",
    "form",
    "range_km",
    "duration_days",
    "on_others",
    "strength",
    "control",
    "origin",
    "state",
    "visibility",
    "strain",
    "strain_cap",
    "item_node_id",
}
TRUTH_FIELDS = {"title", "description", "kind", "hidden_from", "scope_node_id", "strength", "sanity_cost", "revealed", *control.TRUTH_METHODS}


def typed(row_class: type[Base], values: Edit) -> dict[str, Any]:
    mapper = inspect(row_class)
    columns = {column.key for column in mapper.columns}
    unknown = sorted(set(values) - columns)
    if unknown:
        raise ValidationFailedError(f"No field called {', '.join(unknown)}.")
    return {key: coerce(mapper, key, value) for key, value in values.items()}


class SourceCreate(Command):
    name: str = NAME
    scope_id: int | None = None
    locus: SourceLocus = SourceLocus.PLACE
    renewal: SourceRenewal = SourceRenewal.TIME
    access: SourceAccess = SourceAccess.ANYONE
    visibility: PowerVisibility = PowerVisibility.SUBTLE
    stability: int = Field(default=60, ge=0, le=PERCENT)


class SourceTarget(Command):
    source_id: int


class SourceEdit(Edited):
    source_id: int
    hold: bool = False


class PartCreate(Command):
    owner_id: int
    part: str = Field(min_length=1, max_length=40)
    values: dict[str, ScalarValue] = Field(default_factory=dict)


class PartEdit(Command):
    part_id: int
    part: str = Field(min_length=1, max_length=40)
    values: dict[str, ScalarValue] = Field(default_factory=dict)
    hold: bool = False
    release: list[str] = Field(default_factory=list)


class PartTarget(Command):
    part_id: int
    part: str = Field(min_length=1, max_length=40)


class SystemCreate(Command):
    name: str = NAME
    scope_id: int
    structure: PowerStructure = PowerStructure.RITE
    predictability: int = Field(default=50, ge=0, le=PERCENT)
    prevalence: int = Field(default=50, ge=0, le=PERCENT)
    cost_severity: int = Field(default=50, ge=0, le=PERCENT)
    access: SourceAccess = SourceAccess.ANYONE
    learnability: Learnability = Learnability.ANYONE


class SystemTarget(Command):
    system_id: int


class SystemEdit(Edited):
    system_id: int
    hold: bool = False


class PowerCreate(Command):
    holder_id: int
    technique: SpellTechnique = SpellTechnique.PERCEIVE
    form: SpellForm = SpellForm.MIND
    strength: int = Field(default=3, ge=1, le=10)
    control: int = Field(default=40, ge=0, le=PERCENT)
    origin: PowerOrigin = PowerOrigin.BORN
    state: PowerState = PowerState.ACTIVE
    visibility: PowerVisibility = PowerVisibility.SUBTLE
    source_id: int | None = None
    system_id: int | None = None


class PowerGrant(PowerCreate):
    god_id: int


class PowerTarget(Command):
    power_id: int


class PowerRevoke(Command):
    power_id: int
    god_id: int


class PowerEdit(Edited):
    power_id: int
    hold: bool = False


class TruthCreate(Command):
    title: str = NAME
    subject_id: int
    kind: HiddenTruthKind = HiddenTruthKind.EXISTENCE
    hidden_from: ConcealScope = ConcealScope.EVERYONE
    scope_id: int | None = None
    strength: int = Field(default=60, ge=0, le=PERCENT)
    methods: list[str] = Field(default_factory=list)
    sanity_cost: int = Field(default=0, ge=0, le=PERCENT)
    keeper_id: int | None = None


class TruthTarget(Command):
    truth_id: int


class TruthEdit(Edited):
    truth_id: int
    hold: bool = False


class TruthReveal(Command):
    truth_id: int
    population_id: int


class BreachTrigger(Command):
    truth_id: int
    cause: BreachCause = BreachCause.WITNESS
    place_id: int | None = None


@player_action("source:create", ActionKind.EDIT_RECORD)
async def source_create(scope: PlayerScope, command: SourceCreate) -> Effect:
    draft = control.SourceDraft(command.name, command.scope_id, command.locus, command.renewal, command.access, command.visibility, command.stability)
    row = await control.create_source(await scope.context("source_create"), draft)
    return Effect(f"{row.name} is a source of power now.", command.scope_id, values={"source_id": row.id})


@player_action("source:edit", ActionKind.EDIT_RECORD)
async def source_edit(scope: PlayerScope, command: SourceEdit) -> Effect:
    ctx = await scope.context("source_edit")
    row = await control.source_of(ctx, command.source_id)
    changed = await control.edit_fields(row, typed(type(row), command.values), command.hold, command.release, SOURCE_FIELDS)
    return Effect(f"{row.name}: {', '.join(changed) or 'nothing'} set.", row.scope_node_id)


@player_action("source:delete", ActionKind.EDIT_RECORD)
async def source_delete(scope: PlayerScope, command: SourceTarget) -> Effect:
    ctx = await scope.context("source_delete")
    row = await control.source_of(ctx, command.source_id)
    if row.built_in is not None:
        raise ValidationFailedError("The old sources the world was made with can be edited and held but not unmade.")
    await ctx.session.delete(row)
    return Effect(f"{row.name} is gone from the world.", row.scope_node_id)


@player_action("source_part:create", ActionKind.EDIT_RECORD)
async def source_part_create(scope: PlayerScope, command: PartCreate) -> Effect:
    ctx = await scope.context("source_part_create")
    await control.source_of(ctx, command.owner_id)
    table = control.part_table(command.part, control.SOURCE_PARTS)
    row = await control.add_part(ctx, control.SOURCE_PARTS, command.part, command.owner_id, typed(table, command.values))
    return Effect(f"The source gains {an(command.part)}.", values={"part_id": int(getattr(row, "id", 0))})


@player_action("source_part:edit", ActionKind.EDIT_RECORD)
async def source_part_edit(scope: PlayerScope, command: PartEdit) -> Effect:
    table = control.part_table(command.part, control.SOURCE_PARTS)
    await control.edit_part(
        await scope.context("source_part_edit"),
        control.SOURCE_PARTS,
        command.part,
        command.part_id,
        typed(table, command.values),
        hold=command.hold,
        release=command.release,
    )
    return Effect(f"The {command.part} of the source is set.")


@player_action("source_part:delete", ActionKind.EDIT_RECORD)
async def source_part_delete(scope: PlayerScope, command: PartTarget) -> Effect:
    await control.delete_part(await scope.context("source_part_delete"), control.SOURCE_PARTS, command.part, command.part_id)
    return Effect(f"The {command.part} is taken from the source.")


@player_action("magic_system:create", ActionKind.EDIT_RECORD)
async def system_create(scope: PlayerScope, command: SystemCreate) -> Effect:
    draft = control.SystemDraft(
        command.name,
        command.scope_id,
        command.structure,
        command.predictability,
        command.prevalence,
        command.cost_severity,
        command.access,
        command.learnability,
    )
    row = await control.create_system(await scope.context("system_create"), draft)
    return Effect(f"{row.name} is a system of power now.", command.scope_id, values={"system_id": row.id})


@player_action("magic_system:edit", ActionKind.EDIT_RECORD)
async def system_edit(scope: PlayerScope, command: SystemEdit) -> Effect:
    ctx = await scope.context("system_edit")
    row = await control.system_of(ctx, command.system_id)
    changed = await control.edit_fields(row, typed(type(row), command.values), command.hold, command.release, SYSTEM_FIELDS)
    return Effect(f"{row.name}: {', '.join(changed) or 'nothing'} set.", row.scope_node_id)


@player_action("magic_system:delete", ActionKind.EDIT_RECORD)
async def system_delete(scope: PlayerScope, command: SystemTarget) -> Effect:
    ctx = await scope.context("system_delete")
    row = await control.system_of(ctx, command.system_id)
    await ctx.session.delete(row)
    return Effect(f"{row.name} is unmade.", row.scope_node_id)


@player_action("system_part:create", ActionKind.EDIT_RECORD)
async def system_part_create(scope: PlayerScope, command: PartCreate) -> Effect:
    ctx = await scope.context("system_part_create")
    await control.system_of(ctx, command.owner_id)
    table = control.part_table(command.part, control.SYSTEM_PARTS)
    row = await control.add_part(ctx, control.SYSTEM_PARTS, command.part, command.owner_id, typed(table, command.values))
    return Effect(f"The system gains {an(command.part)}.", values={"part_id": int(getattr(row, "id", 0))})


@player_action("system_part:edit", ActionKind.EDIT_RECORD)
async def system_part_edit(scope: PlayerScope, command: PartEdit) -> Effect:
    table = control.part_table(command.part, control.SYSTEM_PARTS)
    await control.edit_part(
        await scope.context("system_part_edit"),
        control.SYSTEM_PARTS,
        command.part,
        command.part_id,
        typed(table, command.values),
        hold=command.hold,
        release=command.release,
    )
    return Effect(f"The {command.part} of the system is set.")


@player_action("system_part:delete", ActionKind.EDIT_RECORD)
async def system_part_delete(scope: PlayerScope, command: PartTarget) -> Effect:
    await control.delete_part(await scope.context("system_part_delete"), control.SYSTEM_PARTS, command.part, command.part_id)
    return Effect(f"The {command.part} is taken from the system.")


def power_draft(command: PowerCreate) -> control.PowerDraft:
    return control.PowerDraft(
        command.holder_id,
        command.technique,
        command.form,
        command.strength,
        command.control,
        command.origin,
        command.state,
        command.visibility,
        source_id=command.source_id,
        system_id=command.system_id,
    )


@player_action("power:create", ActionKind.EDIT_RECORD)
async def power_create(scope: PlayerScope, command: PowerCreate) -> Effect:
    row = await control.create_power(await scope.context("power_create"), power_draft(command))
    return Effect("A power is given.", command.holder_id, values={"power_id": row.id})


@player_action("power:edit", ActionKind.EDIT_RECORD)
async def power_edit(scope: PlayerScope, command: PowerEdit) -> Effect:
    ctx = await scope.context("power_edit")
    row = await control.power_of(ctx, command.power_id)
    changed = await control.edit_fields(row, typed(type(row), command.values), command.hold, command.release, POWER_FIELDS)
    return Effect(f"The power: {', '.join(changed) or 'nothing'} set.", row.holder_node_id)


@player_action("power:delete", ActionKind.EDIT_RECORD)
async def power_delete(scope: PlayerScope, command: PowerTarget) -> Effect:
    ctx = await scope.context("power_delete")
    row = await control.power_of(ctx, command.power_id)
    await ctx.session.delete(row)
    return Effect("The power is unmade.", row.holder_node_id)


@player_action("power:awaken", ActionKind.EDIT_RECORD)
async def power_awaken(scope: PlayerScope, command: PowerTarget) -> Effect:
    row = await control.set_state(await scope.context("power_awaken"), command.power_id, PowerState.ACTIVE)
    return Effect("The power wakes.", row.holder_node_id)


@player_action("power:suppress", ActionKind.EDIT_RECORD)
async def power_suppress(scope: PlayerScope, command: PowerTarget) -> Effect:
    row = await control.set_state(await scope.context("power_suppress"), command.power_id, PowerState.SUPPRESSED)
    return Effect("The power is stilled.", row.holder_node_id)


@player_action("power:grant", ActionKind.EDIT_RECORD)
async def power_grant(scope: PlayerScope, command: PowerGrant) -> Effect:
    row = await control.grant_power(await scope.context("power_grant"), command.god_id, power_draft(command))
    return Effect("The god grants a power.", command.holder_id, values={"power_id": row.id})


@player_action("power:revoke", ActionKind.EDIT_RECORD)
async def power_revoke(scope: PlayerScope, command: PowerRevoke) -> Effect:
    row = await control.revoke_power(await scope.context("power_revoke"), command.god_id, command.power_id)
    return Effect("The god takes the power back.", row.holder_node_id)


@player_action("power_part:create", ActionKind.EDIT_RECORD)
async def power_part_create(scope: PlayerScope, command: PartCreate) -> Effect:
    ctx = await scope.context("power_part_create")
    await control.power_of(ctx, command.owner_id)
    table = control.part_table(command.part, control.POWER_PARTS)
    row = await control.add_part(ctx, control.POWER_PARTS, command.part, command.owner_id, typed(table, command.values))
    return Effect(f"The power gains {an(command.part)}.", values={"part_id": int(getattr(row, "id", 0))})


@player_action("power_part:edit", ActionKind.EDIT_RECORD)
async def power_part_edit(scope: PlayerScope, command: PartEdit) -> Effect:
    table = control.part_table(command.part, control.POWER_PARTS)
    await control.edit_part(
        await scope.context("power_part_edit"),
        control.POWER_PARTS,
        command.part,
        command.part_id,
        typed(table, command.values),
        hold=command.hold,
        release=command.release,
    )
    return Effect(f"The {command.part} of the power is set.")


@player_action("power_part:delete", ActionKind.EDIT_RECORD)
async def power_part_delete(scope: PlayerScope, command: PartTarget) -> Effect:
    await control.delete_part(await scope.context("power_part_delete"), control.POWER_PARTS, command.part, command.part_id)
    return Effect(f"The {command.part} is taken from the power.")


@player_action("truth:create", ActionKind.EDIT_RECORD)
async def truth_create(scope: PlayerScope, command: TruthCreate) -> Effect:
    draft = control.TruthDraft(
        command.title,
        command.subject_id,
        command.kind,
        command.hidden_from,
        command.scope_id,
        command.strength,
        tuple(command.methods),
        command.sanity_cost,
        command.keeper_id,
    )
    row = await control.create_truth(await scope.context("truth_create"), draft)
    return Effect(f"{row.title} is hidden now.", command.subject_id, values={"truth_id": row.id})


@player_action("truth:edit", ActionKind.EDIT_RECORD)
async def truth_edit(scope: PlayerScope, command: TruthEdit) -> Effect:
    ctx = await scope.context("truth_edit")
    row = await control.truth_of(ctx, command.truth_id)
    changed = await control.edit_fields(row, typed(type(row), command.values), command.hold, command.release, TRUTH_FIELDS)
    return Effect(f"{row.title}: {', '.join(changed) or 'nothing'} set.", row.subject_node_id)


@player_action("truth:delete", ActionKind.EDIT_RECORD)
async def truth_delete(scope: PlayerScope, command: TruthTarget) -> Effect:
    ctx = await scope.context("truth_delete")
    row = await control.truth_of(ctx, command.truth_id)
    await ctx.session.delete(row)
    return Effect(f"{row.title} is no longer hidden or kept.", row.subject_node_id)


@player_action("truth:reveal", ActionKind.EDIT_RECORD)
async def truth_reveal(scope: PlayerScope, command: TruthReveal) -> Effect:
    await control.reveal(await scope.context("truth_reveal"), command.truth_id, command.population_id)
    return Effect("What was hidden is known there now.", command.population_id)


@player_action("truth:hide", ActionKind.EDIT_RECORD)
async def truth_hide(scope: PlayerScope, command: TruthTarget) -> Effect:
    row = await control.hide(await scope.context("truth_hide"), command.truth_id)
    return Effect(f"{row.title} is hidden again.", row.subject_node_id)


@player_action("breach:trigger", ActionKind.EDIT_RECORD)
async def breach_trigger(scope: PlayerScope, command: BreachTrigger) -> Effect:
    row = await control.trigger_breach(await scope.context("breach_trigger"), command.truth_id, command.cause, command.place_id)
    return Effect("Something hidden shows itself.", command.place_id, values={"breach_id": row.id})
