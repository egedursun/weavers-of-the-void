from pydantic import Field

from aerona.core.grammar import several
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.ages import AgeCycle, ArcRole, ArcStage, ArcTemplate, SetupKind
from aerona.engine.storyteller import control
from aerona.services.player.cosmography import Edited
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

SPAN = 100
MANY = 1_000_000
BEAT_TEXT = 400


class WorldTarget(Command):
    world_id: int


class WorldEdit(Edited):
    world_id: int


class FormationDraft(Command):
    world_id: int
    reshape: bool = False


class SeasonDraft(Command):
    world_id: int


class ForecastDraft(Command):
    world_id: int
    people_id: int
    predicted_end_epoch: int = Field(default=0, ge=0, le=MANY)
    heeded: bool = True


class ForecastTarget(Command):
    forecast_id: int


class ForecastEdit(Edited):
    forecast_id: int


class TransformationDraft(Command):
    plan_id: int
    target_moisture: int = Field(default=60, ge=0, le=SPAN)
    target_forest: int = Field(default=50, ge=0, le=SPAN)
    target_fertility: int = Field(default=60, ge=0, le=SPAN)


class PlanTarget(Command):
    plan_id: int


class PlanEdit(Edited):
    plan_id: int


class CycleChoice(Command):
    cycle: AgeCycle = AgeCycle.LINEAR


class AgeTurn(Command):
    pass


class AgeTarget(Command):
    age_id: int


class AgeEdit(Edited):
    age_id: int


class EchoDraft(Command):
    age_id: int
    template: ArcTemplate = ArcTemplate.QUEST
    source_id: int | None = None
    weight: int = Field(default=60, ge=0, le=SPAN)


class EchoTarget(Command):
    echo_id: int


class EchoEdit(Edited):
    echo_id: int


class ArcDraft(Command):
    subject_id: int
    template: ArcTemplate = ArcTemplate.QUEST
    figure_id: int | None = None
    role: ArcRole | None = None


class ArcPress(Command):
    arc_id: int
    drama: int = Field(default=60, ge=0, le=SPAN)


class ArcTarget(Command):
    arc_id: int


class ArcEdit(Edited):
    arc_id: int


class FigureDraft(Command):
    arc_id: int
    node_id: int
    role: ArcRole = ArcRole.ALLY


class FigureTarget(Command):
    arc_id: int
    node_id: int


class FigureEdit(Edited):
    arc_id: int
    node_id: int


class BeatDraft(Command):
    arc_id: int
    stage: ArcStage = ArcStage.RISING
    text: str = Field(default="", max_length=BEAT_TEXT)


class BeatTarget(Command):
    beat_id: int


class BeatEdit(Edited):
    beat_id: int


class SetupDraft(Command):
    kind: SetupKind = SetupKind.OMEN
    source_id: int = Field(default=0, ge=0)
    subject_id: int | None = None


class SetupTarget(Command):
    setup_id: int


class SetupEdit(Edited):
    setup_id: int


@player_action("formation:read", ActionKind.EDIT_RECORD)
async def formation_read(scope: PlayerScope, command: FormationDraft) -> Effect:
    row = await control.read_formation(await scope.context("formation_read"), command.world_id, command.reshape)
    return Effect("The world was shaped anew by its forming." if row.shaped else "The forming of the world is read.", command.world_id)


@player_action("formation:reshape", ActionKind.EDIT_RECORD)
async def formation_reshape(scope: PlayerScope, command: WorldTarget) -> Effect:
    await control.reshape_world(await scope.context("formation_reshape"), command.world_id)
    return Effect("The world takes the shape its forming gives it.", command.world_id)


@player_action("irregular_season:create", ActionKind.EDIT_RECORD)
async def irregular_season_create(scope: PlayerScope, command: SeasonDraft) -> Effect:
    await control.unsettle_seasons(await scope.context("irregular_season_create"), command.world_id, None)
    return Effect("The seasons of the world lose their measure.", command.world_id)


@player_action("irregular_season:forecast", ActionKind.EDIT_RECORD)
async def irregular_season_forecast(scope: PlayerScope, command: WorldTarget) -> Effect:
    made = await control.read_winter(await scope.context("irregular_season_forecast"), command.world_id)
    return Effect(f"{several(made, 'people', 'peoples')} read the coming of the seasons.", command.world_id)


@player_action("winter_forecast:set", ActionKind.EDIT_RECORD)
async def winter_forecast_set(scope: PlayerScope, command: ForecastDraft) -> Effect:
    row = await control.set_forecast(
        await scope.context("winter_forecast_set"), command.world_id, command.people_id, command.predicted_end_epoch, command.heeded
    )
    return Effect("The people's forecast is set.", command.people_id, values={"forecast_id": row.id})


@player_action("eco_transformation:set", ActionKind.EDIT_RECORD)
async def eco_transformation_set(scope: PlayerScope, command: TransformationDraft) -> Effect:
    await control.aim_transformation(
        await scope.context("eco_transformation_set"), command.plan_id, command.target_moisture, command.target_forest, command.target_fertility
    )
    return Effect("The plan aims the land so.")


@player_action("age:cycle", ActionKind.EDIT_RECORD)
async def age_cycle(scope: PlayerScope, command: CycleChoice) -> Effect:
    await control.set_cycle(await scope.context("age_cycle"), command.cycle)
    return Effect("The cosmos turns in ages." if command.cycle is AgeCycle.CYCLIC else "The cosmos runs on to its end.")


@player_action("age:turn", ActionKind.EDIT_RECORD)
async def age_turn(scope: PlayerScope, command: AgeTurn) -> Effect:
    row = await control.turn_now(await scope.context("age_turn"))
    return Effect(f"The age turns; age {row.number} begins.", values={"age_id": row.id})


@player_action("age_echo:create", ActionKind.EDIT_RECORD)
async def age_echo_create(scope: PlayerScope, command: EchoDraft) -> Effect:
    row = await control.add_echo(await scope.context("age_echo_create"), command.age_id, command.template, command.source_id, command.weight)
    return Effect("A great life will echo in the age.", command.source_id, values={"echo_id": row.id})


@player_action("arc:create", ActionKind.EDIT_RECORD)
async def arc_create(scope: PlayerScope, command: ArcDraft) -> Effect:
    row = await control.begin_arc(await scope.context("arc_create"), command.subject_id, command.template, command.figure_id, command.role)
    return Effect("A tale begins in the life.", command.subject_id, values={"arc_id": row.id})


@player_action("arc:press", ActionKind.EDIT_RECORD)
async def arc_press(scope: PlayerScope, command: ArcPress) -> Effect:
    row = await control.press_arc(await scope.context("arc_press"), command.arc_id, command.drama)
    return Effect("The tale is pressed toward its next turn.", row.subject_node_id)


@player_action("arc_figure:create", ActionKind.EDIT_RECORD)
async def arc_figure_create(scope: PlayerScope, command: FigureDraft) -> Effect:
    await control.add_figure(await scope.context("arc_figure_create"), command.arc_id, command.node_id, command.role)
    return Effect("A figure enters the tale.", command.node_id)


@player_action("arc_figure:edit", ActionKind.EDIT_RECORD)
async def arc_figure_edit(scope: PlayerScope, command: FigureEdit) -> Effect:
    key = (command.arc_id, command.node_id)
    await control.edit_record(await scope.context("arc_figure_edit"), "arc_figure", key, command.values, command.release)
    return Effect("The figure is set so.", command.node_id)


@player_action("arc_figure:delete", ActionKind.EDIT_RECORD)
async def arc_figure_delete(scope: PlayerScope, command: FigureTarget) -> Effect:
    await control.delete_record(await scope.context("arc_figure_delete"), "arc_figure", (command.arc_id, command.node_id))
    return Effect("The figure leaves the tale.", command.node_id)


@player_action("arc_beat:create", ActionKind.EDIT_RECORD)
async def arc_beat_create(scope: PlayerScope, command: BeatDraft) -> Effect:
    row = await control.add_beat(await scope.context("arc_beat_create"), command.arc_id, command.stage, command.text)
    return Effect("The tale takes a beat.", values={"beat_id": row.id})


@player_action("setup:create", ActionKind.EDIT_RECORD)
async def setup_create(scope: PlayerScope, command: SetupDraft) -> Effect:
    row = await control.add_setup(await scope.context("setup_create"), command.kind, command.source_id, command.subject_id)
    return Effect("Something is set up to be paid off.", command.subject_id, values={"setup_id": row.id})


@player_action("formation:edit", ActionKind.EDIT_RECORD)
async def formation_edit(scope: PlayerScope, command: WorldEdit) -> Effect:
    await control.edit_record(await scope.context("formation_edit"), "formation", command.world_id, command.values, command.release)
    return Effect("The forming of the world is set so.")


@player_action("formation:delete", ActionKind.EDIT_RECORD)
async def formation_delete(scope: PlayerScope, command: WorldTarget) -> Effect:
    await control.delete_record(await scope.context("formation_delete"), "formation", command.world_id)
    return Effect("The world's forming is forgotten.")


@player_action("irregular_season:edit", ActionKind.EDIT_RECORD)
async def irregular_season_edit(scope: PlayerScope, command: WorldEdit) -> Effect:
    await control.edit_record(await scope.context("irregular_season_edit"), "irregular_season", command.world_id, command.values, command.release)
    return Effect("The irregular seasons are set so.")


@player_action("irregular_season:delete", ActionKind.EDIT_RECORD)
async def irregular_season_delete(scope: PlayerScope, command: WorldTarget) -> Effect:
    await control.delete_record(await scope.context("irregular_season_delete"), "irregular_season", command.world_id)
    return Effect("The seasons keep their measure again.")


@player_action("winter_forecast:edit", ActionKind.EDIT_RECORD)
async def winter_forecast_edit(scope: PlayerScope, command: ForecastEdit) -> Effect:
    await control.edit_record(await scope.context("winter_forecast_edit"), "winter_forecast", command.forecast_id, command.values, command.release)
    return Effect("The forecast is set so.")


@player_action("winter_forecast:delete", ActionKind.EDIT_RECORD)
async def winter_forecast_delete(scope: PlayerScope, command: ForecastTarget) -> Effect:
    await control.delete_record(await scope.context("winter_forecast_delete"), "winter_forecast", command.forecast_id)
    return Effect("The forecast is forgotten.")


@player_action("eco_transformation:edit", ActionKind.EDIT_RECORD)
async def eco_transformation_edit(scope: PlayerScope, command: PlanEdit) -> Effect:
    await control.edit_record(await scope.context("eco_transformation_edit"), "eco_transformation", command.plan_id, command.values, command.release)
    return Effect("The remaking of the land is set so.")


@player_action("eco_transformation:delete", ActionKind.EDIT_RECORD)
async def eco_transformation_delete(scope: PlayerScope, command: PlanTarget) -> Effect:
    await control.delete_record(await scope.context("eco_transformation_delete"), "eco_transformation", command.plan_id)
    return Effect("The plan no longer aims the land.")


@player_action("age:edit", ActionKind.EDIT_RECORD)
async def age_edit(scope: PlayerScope, command: AgeEdit) -> Effect:
    await control.edit_record(await scope.context("age_edit"), "age", command.age_id, command.values, command.release)
    return Effect("The age is set so.")


@player_action("age:delete", ActionKind.EDIT_RECORD)
async def age_delete(scope: PlayerScope, command: AgeTarget) -> Effect:
    await control.delete_record(await scope.context("age_delete"), "age", command.age_id)
    return Effect("The age is struck from the record.")


@player_action("age_echo:edit", ActionKind.EDIT_RECORD)
async def age_echo_edit(scope: PlayerScope, command: EchoEdit) -> Effect:
    await control.edit_record(await scope.context("age_echo_edit"), "age_echo", command.echo_id, command.values, command.release)
    return Effect("The echo is set so.")


@player_action("age_echo:delete", ActionKind.EDIT_RECORD)
async def age_echo_delete(scope: PlayerScope, command: EchoTarget) -> Effect:
    await control.delete_record(await scope.context("age_echo_delete"), "age_echo", command.echo_id)
    return Effect("The echo is silenced.")


@player_action("arc:edit", ActionKind.EDIT_RECORD)
async def arc_edit(scope: PlayerScope, command: ArcEdit) -> Effect:
    await control.edit_record(await scope.context("arc_edit"), "arc", command.arc_id, command.values, command.release)
    return Effect("The tale is set so.")


@player_action("arc:delete", ActionKind.EDIT_RECORD)
async def arc_delete(scope: PlayerScope, command: ArcTarget) -> Effect:
    await control.delete_record(await scope.context("arc_delete"), "arc", command.arc_id)
    return Effect("The tale is struck from the record.")


@player_action("arc_beat:edit", ActionKind.EDIT_RECORD)
async def arc_beat_edit(scope: PlayerScope, command: BeatEdit) -> Effect:
    await control.edit_record(await scope.context("arc_beat_edit"), "arc_beat", command.beat_id, command.values, command.release)
    return Effect("The beat is set so.")


@player_action("arc_beat:delete", ActionKind.EDIT_RECORD)
async def arc_beat_delete(scope: PlayerScope, command: BeatTarget) -> Effect:
    await control.delete_record(await scope.context("arc_beat_delete"), "arc_beat", command.beat_id)
    return Effect("The beat is struck from the tale.")


@player_action("setup:edit", ActionKind.EDIT_RECORD)
async def setup_edit(scope: PlayerScope, command: SetupEdit) -> Effect:
    await control.edit_record(await scope.context("setup_edit"), "setup", command.setup_id, command.values, command.release)
    return Effect("The setup is set so.")


@player_action("setup:delete", ActionKind.EDIT_RECORD)
async def setup_delete(scope: PlayerScope, command: SetupTarget) -> Effect:
    await control.delete_record(await scope.context("setup_delete"), "setup", command.setup_id)
    return Effect("The setup is struck from the record.")
