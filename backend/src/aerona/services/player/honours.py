from aerona.core.grammar import several
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.honours import UnitHonourKind, VeteranGrant
from aerona.engine.honours import control
from aerona.services.player.cosmography import Edited
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class RunNow(Command):
    pass


class NamedUnitDraft(Command):
    name: str
    unit_id: int | None = None
    owner_id: int | None = None
    raised_from_id: int | None = None
    esprit: int = 40
    nickname: str | None = None


class NamedUnitTarget(Command):
    record_id: int


class NamedUnitEdit(Edited):
    record_id: int


class UnitHonourDraft(Command):
    named_unit_id: int
    kind: UnitHonourKind = UnitHonourKind.VICTORY
    note: str = ""


class UnitHonourTarget(Command):
    record_id: int


class UnitHonourEdit(Edited):
    record_id: int


class VeteranGrantDraft(Command):
    polity_id: int
    kind: VeteranGrant = VeteranGrant.PENSION
    veterans: int = 10
    settlement_id: int | None = None
    war_id: int | None = None


class VeteranGrantTarget(Command):
    record_id: int


class VeteranGrantEdit(Edited):
    record_id: int


@player_action("named_unit:create", ActionKind.EDIT_RECORD)
async def named_unit_create(scope: PlayerScope, command: NamedUnitDraft) -> Effect:
    row = await control.create_record(
        await scope.context("named_unit_create"),
        "named_unit",
        {
            "name": command.name,
            "unit_id": command.unit_id,
            "owner_entity_id": command.owner_id,
            "raised_from_entity_id": command.raised_from_id,
            "esprit": command.esprit,
            "nickname": command.nickname,
        },
    )
    return Effect("The unit takes its name.", values={"record_id": getattr(row, "id", 0)})


@player_action("named_unit:edit", ActionKind.EDIT_RECORD)
async def named_unit_edit(scope: PlayerScope, command: NamedUnitEdit) -> Effect:
    await control.edit_record(await scope.context("named_unit_edit"), "named_unit", command.record_id, command.values, command.release)
    return Effect("The named unit is set so.")


@player_action("named_unit:delete", ActionKind.EDIT_RECORD)
async def named_unit_delete(scope: PlayerScope, command: NamedUnitTarget) -> Effect:
    await control.delete_record(await scope.context("named_unit_delete"), "named_unit", command.record_id)
    return Effect("The named unit is struck from the rolls.")


@player_action("unit_honour:create", ActionKind.EDIT_RECORD)
async def unit_honour_create(scope: PlayerScope, command: UnitHonourDraft) -> Effect:
    row = await control.create_record(
        await scope.context("unit_honour_create"), "unit_honour", {"named_unit_id": command.named_unit_id, "kind": command.kind, "note": command.note}
    )
    return Effect("The honour is set on the standard.", values={"record_id": getattr(row, "id", 0)})


@player_action("unit_honour:edit", ActionKind.EDIT_RECORD)
async def unit_honour_edit(scope: PlayerScope, command: UnitHonourEdit) -> Effect:
    await control.edit_record(await scope.context("unit_honour_edit"), "unit_honour", command.record_id, command.values, command.release)
    return Effect("The honour is set so.")


@player_action("unit_honour:delete", ActionKind.EDIT_RECORD)
async def unit_honour_delete(scope: PlayerScope, command: UnitHonourTarget) -> Effect:
    await control.delete_record(await scope.context("unit_honour_delete"), "unit_honour", command.record_id)
    return Effect("The honour is struck from the standard.")


@player_action("veteran_grant:create", ActionKind.EDIT_RECORD)
async def veteran_grant_create(scope: PlayerScope, command: VeteranGrantDraft) -> Effect:
    row = await control.create_record(
        await scope.context("veteran_grant_create"),
        "veteran_grant",
        {
            "polity_entity_id": command.polity_id,
            "kind": command.kind,
            "veterans": command.veterans,
            "settlement_entity_id": command.settlement_id,
            "war_entity_id": command.war_id,
        },
    )
    return Effect("The veterans are granted it.", values={"record_id": getattr(row, "id", 0)})


@player_action("veteran_grant:edit", ActionKind.EDIT_RECORD)
async def veteran_grant_edit(scope: PlayerScope, command: VeteranGrantEdit) -> Effect:
    await control.edit_record(await scope.context("veteran_grant_edit"), "veteran_grant", command.record_id, command.values, command.release)
    return Effect("The grant is set so.")


@player_action("veteran_grant:delete", ActionKind.EDIT_RECORD)
async def veteran_grant_delete(scope: PlayerScope, command: VeteranGrantTarget) -> Effect:
    await control.delete_record(await scope.context("veteran_grant_delete"), "veteran_grant", command.record_id)
    return Effect("The grant is withdrawn.")


@player_action("honours:run", ActionKind.EDIT_RECORD)
async def honours_run(scope: PlayerScope, command: RunNow) -> Effect:
    tally = await control.run_honours(await scope.context("honours_run"))
    told = [
        several(tally.veterans.granted, "grant", "grants") + " made to veterans",
        several(tally.veterans.colonies, "colony", "colonies") + " founded",
        several(tally.veterans.associations, "association", "associations") + " of veterans formed",
    ]
    return Effect("; ".join(told) + ".")
