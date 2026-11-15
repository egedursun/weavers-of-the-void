from pydantic import Field

from aerona.catalog.transformations import TRANSFORMS
from aerona.db.tables.transform import LUMINOSITY_SHIFT_MAX
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.transform import ProspectStance, TransformKind
from aerona.engine.transform import control
from aerona.engine.transform.run import force, set_stance
from aerona.services.player.cosmography import Edited
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action
from aerona.services.player.transform_undo import revert


class TransformTarget(Command):
    kind: TransformKind
    subject_id: int


class TransformationTarget(Command):
    transformation_id: int


class TransformationEdit(Edited):
    transformation_id: int


class ProspectTarget(Command):
    prospect_id: int


class ProspectEdit(Edited):
    prospect_id: int


class StarModifierDraft(Command):
    star_id: int
    luminosity_pct: int = Field(ge=-LUMINOSITY_SHIFT_MAX, le=LUMINOSITY_SHIFT_MAX)
    age_epochs: int = Field(default=0, ge=0)
    decay: int = Field(default=0, ge=0, le=100)


class StarModifierTarget(Command):
    modifier_id: int


class StarModifierEdit(Edited):
    modifier_id: int


@player_action("transform:force", ActionKind.EDIT_RECORD)
async def transform_force(scope: PlayerScope, command: TransformTarget) -> Effect:
    row = await force(await scope.context("transform_force"), command.kind, command.subject_id)
    return Effect(f"{TRANSFORMS[command.kind].label}: {row.subject_name or 'it'} is changed.", target_node_id=row.result_node_id or command.subject_id)


@player_action("transform:block", ActionKind.EDIT_RECORD)
async def transform_block(scope: PlayerScope, command: TransformTarget) -> Effect:
    await set_stance(await scope.context("transform_block"), command.kind, command.subject_id, ProspectStance.BLOCKED)
    return Effect(f"{TRANSFORMS[command.kind].label} is blocked for this thing.", target_node_id=command.subject_id)


@player_action("transform:release", ActionKind.EDIT_RECORD)
async def transform_release(scope: PlayerScope, command: TransformTarget) -> Effect:
    await set_stance(await scope.context("transform_release"), command.kind, command.subject_id, ProspectStance.OPEN)
    return Effect(f"{TRANSFORMS[command.kind].label} may come again when its time comes.", target_node_id=command.subject_id)


@player_action("transform:revert", ActionKind.EDIT_RECORD)
async def transform_revert(scope: PlayerScope, command: TransformationTarget) -> Effect:
    row = await revert(await scope.context("transform_revert"), command.transformation_id)
    return Effect(f"{TRANSFORMS[row.kind].label} is undone.", target_node_id=row.subject_node_id)


@player_action("transformation:edit", ActionKind.EDIT_RECORD)
async def transformation_edit(scope: PlayerScope, command: TransformationEdit) -> Effect:
    row = await control.edit_transformation(await scope.context("transformation_edit"), command.transformation_id, command.values, command.release)
    return Effect("The record of the transformation keeps its new values.", target_node_id=row.subject_node_id)


@player_action("transformation:delete", ActionKind.EDIT_RECORD)
async def transformation_delete(scope: PlayerScope, command: TransformationTarget) -> Effect:
    await control.remove_transformation(await scope.context("transformation_delete"), command.transformation_id)
    return Effect("The record of the transformation is struck out.")


@player_action("transform_prospect:edit", ActionKind.EDIT_RECORD)
async def prospect_edit(scope: PlayerScope, command: ProspectEdit) -> Effect:
    row = await control.edit_prospect(await scope.context("transform_prospect_edit"), command.prospect_id, command.values, command.release)
    return Effect("The prospect keeps its new values.", target_node_id=row.subject_node_id)


@player_action("transform_prospect:delete", ActionKind.EDIT_RECORD)
async def prospect_delete(scope: PlayerScope, command: ProspectTarget) -> Effect:
    await control.remove_prospect(await scope.context("transform_prospect_delete"), command.prospect_id)
    return Effect("The prospect is struck out; it starts again from nothing if its conditions return.")


@player_action("star_modifier:create", ActionKind.EDIT_RECORD)
async def star_modifier_create(scope: PlayerScope, command: StarModifierDraft) -> Effect:
    await control.add_star_modifier(await scope.context("star_modifier_create"), command.star_id, command.luminosity_pct, command.age_epochs, command.decay)
    return Effect("The star's light is changed.", target_node_id=command.star_id)


@player_action("star_modifier:edit", ActionKind.EDIT_RECORD)
async def star_modifier_edit(scope: PlayerScope, command: StarModifierEdit) -> Effect:
    row = await control.edit_star_modifier(await scope.context("star_modifier_edit"), command.modifier_id, command.values, command.release)
    return Effect("The change to the star's light keeps its new values.", target_node_id=row.star_id)


@player_action("star_modifier:delete", ActionKind.EDIT_RECORD)
async def star_modifier_delete(scope: PlayerScope, command: StarModifierTarget) -> Effect:
    await control.remove_star_modifier(await scope.context("star_modifier_delete"), command.modifier_id)
    return Effect("The change to the star's light is lifted.")
