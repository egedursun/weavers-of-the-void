from pydantic import Field

from aerona.core.grammar import spoken
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.physics import CosmicFeatureKind, ImpactBody, SurveyLevel, SystemRole, TerraformAim
from aerona.engine.cosmos import physics_control as control
from aerona.engine.phases.physics import world_physics
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

Edit = dict[str, int | float | str | bool | list[str] | None]


class Edited(Command):
    values: Edit = Field(default_factory=dict)
    release: list[str] = Field(default_factory=list)


class StarPhysicsEdit(Edited):
    star_id: int


class SystemDraft(Command):
    name: str = ""
    star_ids: list[int]
    separation: float = 0.0


class SystemEdit(Edited):
    system_id: int


class SystemTarget(Command):
    system_id: int


class StarMove(Command):
    star_id: int
    system_id: int
    role: SystemRole = SystemRole.COMPANION


class WorldPhysicsEdit(Edited):
    world_id: int


class LifeEdit(Edited):
    world_id: int


class FeatureDraft(Command):
    kind: CosmicFeatureKind
    name: str = ""
    star_id: int | None = None
    galaxy_id: int | None = None
    world_id: int | None = None
    world_b_id: int | None = None
    density: int | None = None
    richness: int | None = None
    pirates: int | None = None
    instability: int | None = None
    period_epochs: int | None = None


class FeatureEdit(Edited):
    feature_id: int


class FeatureTarget(Command):
    feature_id: int


class ImpactCall(Command):
    world_id: int
    region_id: int | None = None
    size: int | None = None
    body: ImpactBody = ImpactBody.CALLED


class ImpactTarget(Command):
    impact_id: int


class ImpactEdit(Edited):
    impact_id: int


class TerraformDraft(Command):
    world_id: int
    aim: TerraformAim
    step: int | None = None
    epochs: int | None = None


class TerraformEdit(Edited):
    project_id: int


class TerraformTarget(Command):
    project_id: int


class SurveySet(Command):
    observer_id: int
    world_id: int
    level: SurveyLevel


class SurveyTarget(Command):
    survey_id: int


@player_action("star_physics:edit", ActionKind.EDIT_RECORD)
async def edit_star_physics(scope: PlayerScope, command: StarPhysicsEdit) -> Effect:
    row = await control.edit_star_physics(await scope.context("star_physics_edit"), command.star_id, command.values, command.release)
    return Effect("The star's body is reshaped.", row.star_id)


@player_action("star_system:create", ActionKind.EDIT_RECORD)
async def create_system(scope: PlayerScope, command: SystemDraft) -> Effect:
    row = await control.create_system(await scope.context("star_system_create"), command.name, command.star_ids, command.separation)
    return Effect(f"{row.name} is gathered.", command.star_ids[0], values={"system_id": row.id})


@player_action("star_system:edit", ActionKind.EDIT_RECORD)
async def edit_system(scope: PlayerScope, command: SystemEdit) -> Effect:
    row = await control.edit_system(await scope.context("star_system_edit"), command.system_id, command.values, command.release)
    return Effect(f"{row.name} is reshaped.")


@player_action("star_system:delete", ActionKind.EDIT_RECORD)
async def delete_system(scope: PlayerScope, command: SystemTarget) -> Effect:
    await control.delete_system(await scope.context("star_system_delete"), command.system_id)
    return Effect("The system is broken up; each of its stars stands alone.")


@player_action("star_system:move", ActionKind.EDIT_RECORD)
async def move_star(scope: PlayerScope, command: StarMove) -> Effect:
    await control.move_star(await scope.context("star_system_move"), command.star_id, command.system_id, command.role)
    return Effect("The star now belongs to that system.", command.star_id)


@player_action("world_physics:edit", ActionKind.EDIT_RECORD)
async def edit_world_physics(scope: PlayerScope, command: WorldPhysicsEdit) -> Effect:
    ctx = await scope.context("world_physics_edit")
    await control.edit_world_physics(ctx, command.world_id, command.values, command.release)
    await world_physics(ctx)
    return Effect("The world's body is reshaped.", command.world_id)


@player_action("life_class:edit", ActionKind.EDIT_RECORD)
async def edit_life(scope: PlayerScope, command: LifeEdit) -> Effect:
    await control.edit_life(await scope.context("life_class_edit"), command.world_id, command.values, command.release)
    return Effect("The life of the world is reshaped.", command.world_id)


@player_action("cosmic_feature:create", ActionKind.EDIT_RECORD)
async def create_feature(scope: PlayerScope, command: FeatureDraft) -> Effect:
    values = command.model_dump(exclude={"kind", "name"})
    row = await control.create_feature(await scope.context("cosmic_feature_create"), command.kind, command.name, values)
    return Effect(f"{row.name} takes its place in the heavens.", values={"feature_id": row.id})


@player_action("cosmic_feature:edit", ActionKind.EDIT_RECORD)
async def edit_feature(scope: PlayerScope, command: FeatureEdit) -> Effect:
    row = await control.edit_feature(await scope.context("cosmic_feature_edit"), command.feature_id, command.values, command.release)
    return Effect(f"{row.name} is reshaped.")


@player_action("cosmic_feature:delete", ActionKind.EDIT_RECORD)
async def delete_feature(scope: PlayerScope, command: FeatureTarget) -> Effect:
    await control.delete_feature(await scope.context("cosmic_feature_delete"), command.feature_id)
    return Effect("The feature is gone from the heavens.")


@player_action("impact:call", ActionKind.EDIT_RECORD)
async def call_impact(scope: PlayerScope, command: ImpactCall) -> Effect:
    creator = await scope.creator()
    row = await control.call(await scope.context("impact_call"), command.world_id, command.region_id, creator.id, size=command.size, body=command.body)
    return Effect("A body falls toward the world.", command.world_id, values={"impact_id": row.id})


@player_action("impact:deflect", ActionKind.EDIT_RECORD)
async def deflect_impact(scope: PlayerScope, command: ImpactTarget) -> Effect:
    creator = await scope.creator()
    row = await control.deflect(await scope.context("impact_deflect"), command.impact_id, creator.id)
    return Effect(row.text, row.world_id)


@player_action("impact:edit", ActionKind.EDIT_RECORD)
async def edit_impact(scope: PlayerScope, command: ImpactEdit) -> Effect:
    row = await control.edit_impact(await scope.context("impact_edit"), command.impact_id, command.values, command.release)
    return Effect("The impact is reshaped.", row.world_id)


@player_action("impact:delete", ActionKind.EDIT_RECORD)
async def delete_impact(scope: PlayerScope, command: ImpactTarget) -> Effect:
    await control.delete_impact(await scope.context("impact_delete"), command.impact_id)
    return Effect("The impact is struck from the record.")


@player_action("terraform:start", ActionKind.EDIT_RECORD)
async def start_terraform(scope: PlayerScope, command: TerraformDraft) -> Effect:
    creator = await scope.creator()
    row = await control.start_terraform(
        await scope.context("terraform_start"), command.world_id, command.aim, creator.id, step=command.step, epochs=command.epochs
    )
    return Effect("The world begins to change.", command.world_id, values={"project_id": row.id})


@player_action("terraform:edit", ActionKind.EDIT_RECORD)
async def edit_terraform(scope: PlayerScope, command: TerraformEdit) -> Effect:
    row = await control.edit_terraform(await scope.context("terraform_edit"), command.project_id, command.values, command.release)
    return Effect("The work on the world is reshaped.", row.world_id)


@player_action("terraform:stop", ActionKind.EDIT_RECORD)
async def stop_terraform(scope: PlayerScope, command: TerraformTarget) -> Effect:
    await control.stop_terraform(await scope.context("terraform_stop"), command.project_id)
    return Effect("The work on the world is stopped.")


@player_action("survey:set", ActionKind.EDIT_RECORD)
async def set_survey(scope: PlayerScope, command: SurveySet) -> Effect:
    row = await control.set_survey(await scope.context("survey_set"), command.observer_id, command.world_id, command.level)
    return Effect(f"They now know the world as {spoken(row.level)}.", command.observer_id)


@player_action("survey:forget", ActionKind.EDIT_RECORD)
async def forget_survey(scope: PlayerScope, command: SurveyTarget) -> Effect:
    await control.forget_survey(await scope.context("survey_forget"), command.survey_id)
    return Effect("What they knew of the world is forgotten.")
