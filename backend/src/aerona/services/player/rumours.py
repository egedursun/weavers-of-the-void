from aerona.domain.enums.action import ActionKind
from aerona.engine.lore import rumours
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class PlantRumour(Command):
    community_id: int
    incident_id: int | None = None
    subject_id: int | None = None
    text: str = ""
    fidelity: int = 80
    atrocity: bool = False


class EditRumour(Command):
    rumour_id: int
    fidelity: int | None = None
    release: bool = False


class SuppressRumour(Command):
    rumour_id: int
    everywhere: bool = False


@player_action("rumour:plant", ActionKind.OTHER)
async def plant_rumour(scope: PlayerScope, command: PlantRumour) -> Effect:
    row = await rumours.plant(
        await scope.context("rumour_plant"),
        command.community_id,
        incident_id=command.incident_id,
        subject_id=command.subject_id,
        text=command.text,
        fidelity=command.fidelity,
        atrocity=command.atrocity,
    )
    return Effect(f"The whisper takes root, {row.fidelity}% true to the tale.", command.community_id)


@player_action("rumour:edit", ActionKind.EDIT_RECORD)
async def edit_rumour(scope: PlayerScope, command: EditRumour) -> Effect:
    row = await rumours.edit(await scope.context("rumour_edit"), command.rumour_id, fidelity=command.fidelity, release=command.release)
    held = "held" if "fidelity" in row.locked else "free to fade"
    return Effect(f"The rumour runs {row.fidelity}% true, {held}.", row.carrier_entity_id)


@player_action("rumour:suppress", ActionKind.EDIT_RECORD)
async def suppress_rumour(scope: PlayerScope, command: SuppressRumour) -> Effect:
    count = await rumours.suppress(await scope.context("rumour_suppress"), command.rumour_id, everywhere=command.everywhere)
    return Effect("The talk dies away." if count == 1 else f"The talk dies away in {count} places.", None)
