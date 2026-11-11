from pydantic import Field

from aerona.catalog.mythic import QUEST_PARTY_MAX
from aerona.constants.schema import NAME_MAX_LENGTH
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.mind import ActKind
from aerona.domain.enums.mythic import CosmicOffice, GeasLayer, GeasMode, ServitorRank, ServitorRole
from aerona.engine.mythic import control
from aerona.services.player.cosmography import Edited
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class QuestDraft(Command):
    quester_id: int
    legend_id: int
    members: list[int] = Field(default_factory=list, max_length=QUEST_PARTY_MAX)


class QuestEdit(Edited):
    quest_id: int


class QuestTarget(Command):
    quest_id: int


class QuestParty(Command):
    quest_id: int
    members: list[int] = Field(default_factory=list, max_length=QUEST_PARTY_MAX)


class MortalEdit(Edited):
    mortal_id: int


class MortalTarget(Command):
    mortal_id: int


class ServitorDraft(Command):
    god_id: int
    name: str = Field(min_length=1, max_length=NAME_MAX_LENGTH)
    rank: ServitorRank
    role: ServitorRole
    post_id: int | None = None


class ServitorEdit(Edited):
    spirit_id: int


class ServitorTarget(Command):
    spirit_id: int


class GeasDraft(Command):
    bearer_id: int
    layer_id: int | None = None
    layer: GeasLayer = GeasLayer.GOD
    mode: GeasMode
    act: ActKind


class GeasEdit(Edited):
    geas_id: int


class GeasTarget(Command):
    geas_id: int


class OfficeSeat(Command):
    office: CosmicOffice
    holder_id: int


class OfficeEdit(Edited):
    office: CosmicOffice


class OfficeTarget(Command):
    office: CosmicOffice


@player_action("heroquest:begin", ActionKind.EDIT_RECORD)
async def begin_quest(scope: PlayerScope, command: QuestDraft) -> Effect:
    row = await control.start_quest(await scope.context("heroquest_begin"), command.quester_id, command.legend_id, command.members)
    return Effect("A heroquest begins.", command.quester_id, values={"quest_id": row.id})


@player_action("heroquest:edit", ActionKind.EDIT_RECORD)
async def edit_quest(scope: PlayerScope, command: QuestEdit) -> Effect:
    row = await control.edit_quest(await scope.context("heroquest_edit"), command.quest_id, command.values, command.release)
    return Effect("The heroquest is set so.", row.quester_entity_id)


@player_action("heroquest:advance", ActionKind.EDIT_RECORD)
async def advance_quest(scope: PlayerScope, command: QuestTarget) -> Effect:
    row = await control.step_quest(await scope.context("heroquest_advance"), command.quest_id)
    return Effect(f"The heroquest stands at step {row.step} of {row.steps}: {row.state.value}.", row.quester_entity_id)


@player_action("heroquest:party", ActionKind.EDIT_RECORD)
async def set_party(scope: PlayerScope, command: QuestParty) -> Effect:
    row = await control.set_party(await scope.context("heroquest_party"), command.quest_id, command.members)
    return Effect(f"The heroquest goes on with {len(command.members)} companions.", row.quester_entity_id)


@player_action("heroquest:delete", ActionKind.EDIT_RECORD)
async def delete_quest(scope: PlayerScope, command: QuestTarget) -> Effect:
    await control.delete_quest(await scope.context("heroquest_delete"), command.quest_id)
    return Effect("The heroquest is struck from the record.")


@player_action("mantling:edit", ActionKind.EDIT_RECORD)
async def edit_mantling(scope: PlayerScope, command: MortalEdit) -> Effect:
    await control.edit_mantling(await scope.context("mantling_edit"), command.mortal_id, command.values, command.release)
    return Effect("The mortal's path toward godhood is set so.", command.mortal_id)


@player_action("mantling:delete", ActionKind.EDIT_RECORD)
async def delete_mantling(scope: PlayerScope, command: MortalTarget) -> Effect:
    await control.delete_mantling(await scope.context("mantling_delete"), command.mortal_id)
    return Effect("The mortal walks no god's path.", command.mortal_id)


@player_action("servitor:make", ActionKind.EDIT_RECORD)
async def make_servitor(scope: PlayerScope, command: ServitorDraft) -> Effect:
    row = await control.create_servitor(
        await scope.context("servitor_make"), command.god_id, name=command.name, rank=command.rank, role=command.role, post_id=command.post_id
    )
    return Effect(f"{command.name} enters the service of its god.", row.spirit_entity_id, values={"spirit_id": row.spirit_entity_id})


@player_action("servitor:edit", ActionKind.EDIT_RECORD)
async def edit_servitor(scope: PlayerScope, command: ServitorEdit) -> Effect:
    await control.edit_servitor(await scope.context("servitor_edit"), command.spirit_id, command.values, command.release)
    return Effect("The servitor is set so.", command.spirit_id)


@player_action("servitor:release", ActionKind.EDIT_RECORD)
async def release_servitor(scope: PlayerScope, command: ServitorTarget) -> Effect:
    await control.release_servitor(await scope.context("servitor_release"), command.spirit_id)
    return Effect("The servitor is released from service.", command.spirit_id)


@player_action("geas:lay", ActionKind.EDIT_RECORD)
async def lay_geas(scope: PlayerScope, command: GeasDraft) -> Effect:
    row = await control.place_geas(
        await scope.context("geas_lay"), command.bearer_id, command.layer_id, layer=command.layer, mode=command.mode, act=command.act
    )
    return Effect("A geas is laid.", command.bearer_id, values={"geas_id": row.id})


@player_action("geas:edit", ActionKind.EDIT_RECORD)
async def edit_geas(scope: PlayerScope, command: GeasEdit) -> Effect:
    row = await control.edit_geas(await scope.context("geas_edit"), command.geas_id, command.values, command.release)
    return Effect("The geas is set so.", row.bearer_entity_id)


@player_action("geas:break", ActionKind.EDIT_RECORD)
async def break_geas(scope: PlayerScope, command: GeasTarget) -> Effect:
    row = await control.break_geas_now(await scope.context("geas_break"), command.geas_id)
    return Effect("The geas is broken and its doom falls.", row.bearer_entity_id)


@player_action("geas:delete", ActionKind.EDIT_RECORD)
async def delete_geas(scope: PlayerScope, command: GeasTarget) -> Effect:
    await control.delete_geas(await scope.context("geas_delete"), command.geas_id)
    return Effect("The geas is lifted.")


@player_action("cosmic_office:appoint", ActionKind.EDIT_RECORD)
async def appoint_office(scope: PlayerScope, command: OfficeSeat) -> Effect:
    await control.seat_office(await scope.context("cosmic_office_appoint"), command.office, command.holder_id)
    return Effect(f"The office of {command.office.value} is given.", command.holder_id)


@player_action("cosmic_office:edit", ActionKind.EDIT_RECORD)
async def edit_office(scope: PlayerScope, command: OfficeEdit) -> Effect:
    await control.edit_office(await scope.context("cosmic_office_edit"), command.office, command.values, command.release)
    return Effect(f"The office of {command.office.value} is set so.")


@player_action("cosmic_office:vacate", ActionKind.EDIT_RECORD)
async def vacate_office(scope: PlayerScope, command: OfficeTarget) -> Effect:
    await control.vacate_office(await scope.context("cosmic_office_vacate"), command.office)
    return Effect(f"The office of {command.office.value} stands empty.")
