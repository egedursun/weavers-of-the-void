from aerona.core.grammar import several
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.eras import ProgrammeStage
from aerona.engine.eras import control
from aerona.services.player.cosmography import Edited
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class RunNow(Command):
    pass


class TechProgrammeDraft(Command):
    polity_id: int
    technique: Technique
    progress: int = 0
    stage: ProgrammeStage = ProgrammeStage.PLANNING
    visibility: int = 10


class TechProgrammeTarget(Command):
    record_id: int


class TechProgrammeEdit(Edited):
    record_id: int


@player_action("tech_programme:create", ActionKind.EDIT_RECORD)
async def tech_programme_create(scope: PlayerScope, command: TechProgrammeDraft) -> Effect:
    row = await control.create_programme(
        await scope.context("tech_programme_create"),
        {
            "polity_entity_id": command.polity_id,
            "technique": command.technique,
            "progress": command.progress,
            "stage": command.stage,
            "visibility": command.visibility,
        },
    )
    return Effect("The realm begins its programme.", values={"record_id": row.id})


@player_action("tech_programme:edit", ActionKind.EDIT_RECORD)
async def tech_programme_edit(scope: PlayerScope, command: TechProgrammeEdit) -> Effect:
    await control.edit_programme(await scope.context("tech_programme_edit"), command.record_id, command.values, command.release)
    return Effect("The programme is set so.")


@player_action("tech_programme:delete", ActionKind.EDIT_RECORD)
async def tech_programme_delete(scope: PlayerScope, command: TechProgrammeTarget) -> Effect:
    await control.delete_programme(await scope.context("tech_programme_delete"), command.record_id)
    return Effect("The programme is ended.")


@player_action("eras:run", ActionKind.EDIT_RECORD)
async def eras_run(scope: PlayerScope, command: RunNow) -> Effect:
    tally = await control.run_eras(await scope.context("eras_run"))
    told = [
        several(tally.floored, "community", "communities") + " set at the starting era",
        several(tally.started, "programme", "programmes") + " begun",
        several(tally.completed, "programme", "programmes") + " completed",
        several(tally.sabotaged, "sabotage", "sabotages"),
    ]
    return Effect("; ".join(told) + ".")
