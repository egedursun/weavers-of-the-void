from pydantic import Field

from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.operations import CarrierKind, CrewStation, EchelonLevel, ExpeditionRole, PointOfSail, QuirkKind, ShotKind
from aerona.engine.operations import control
from aerona.services.player.cosmography import Edited
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

SPAN = 100
MANY = 1_000_000_000
NAME = 200
LEGS = 50


class EchelonDraft(Command):
    owner_id: int
    level: EchelonLevel = EchelonLevel.BRIGADE
    name: str = Field(min_length=1, max_length=NAME)
    army_id: int | None = None
    parent_id: int | None = None
    commander_id: int | None = None


class EchelonTarget(Command):
    echelon_id: int


class EchelonEdit(Edited):
    echelon_id: int


class StackAssignment(Command):
    stack_id: int
    echelon_id: int | None = None


class DepotDraft(Command):
    owner_id: int
    region_id: int
    field: bool = False
    capacity: int = Field(default=600, ge=0, le=MANY)
    supplies: int = Field(default=0, ge=0, le=MANY)


class DepotTarget(Command):
    depot_id: int


class DepotEdit(Edited):
    depot_id: int


class TransportDraft(Command):
    owner_id: int
    kind: CarrierKind = CarrierKind.WAGONS
    count: int = Field(default=10, ge=1, le=MANY)
    depot_id: int | None = None


class TransportTarget(Command):
    transport_id: int


class TransportEdit(Edited):
    transport_id: int


class FlowTarget(Command):
    flow_id: int


class FlowEdit(Edited):
    flow_id: int


class OperationDraft(Command):
    army_id: int
    culminated: bool = False
    pause_seasons: int = Field(default=0, ge=0, le=LEGS)


class ArmyTarget(Command):
    army_id: int


class ArmyEdit(Edited):
    army_id: int


class TheatreDraft(Command):
    owner_id: int
    war_id: int
    priority: int = Field(default=50, ge=0, le=SPAN)


class TheatreTarget(Command):
    theatre_id: int


class TheatreEdit(Edited):
    theatre_id: int


class ShipDraft(Command):
    vessel_id: int
    shot: ShotKind = ShotKind.ROUND
    point_of_sail: PointOfSail = PointOfSail.REACHING


class VesselTarget(Command):
    vessel_id: int


class VesselEdit(Edited):
    vessel_id: int


class CrewDraft(Command):
    vessel_id: int
    station: CrewStation = CrewStation.GUNNERS
    count: int = Field(default=10, ge=0, le=MANY)
    skill: int = Field(default=40, ge=0, le=SPAN)


class CrewTarget(Command):
    vessel_id: int
    station: CrewStation


class CrewEdit(Edited):
    vessel_id: int
    station: CrewStation


class AdmiraltyDraft(Command):
    polity_id: int
    budget_share: int = Field(default=25, ge=0, le=SPAN)


class PolityTarget(Command):
    polity_id: int


class PolityEdit(Edited):
    polity_id: int


class ExpeditionDraft(Command):
    leader_id: int
    target_id: int
    companion_ids: list[int] = Field(default_factory=list)
    sponsor_id: int | None = None


class ExpeditionTarget(Command):
    expedition_id: int


class ExpeditionEdit(Edited):
    expedition_id: int


class ExpeditionPush(Command):
    expedition_id: int
    legs: int = Field(default=1, ge=1, le=LEGS)


class MemberDraft(Command):
    expedition_id: int
    mortal_id: int
    role: ExpeditionRole = ExpeditionRole.PORTER


class MemberTarget(Command):
    member_id: int


class MemberEdit(Edited):
    member_id: int


class LogTarget(Command):
    log_id: int


class LogEdit(Edited):
    log_id: int


class QuirkDraft(Command):
    mortal_id: int
    kind: QuirkKind = QuirkKind.HARDY
    source_id: int | None = None


class QuirkTarget(Command):
    quirk_id: int


class QuirkEdit(Edited):
    quirk_id: int


@player_action("echelon:create", ActionKind.EDIT_RECORD)
async def echelon_create(scope: PlayerScope, command: EchelonDraft) -> Effect:
    row = await control.form_echelon(
        await scope.context("echelon_create"),
        command.owner_id,
        command.level,
        command.name,
        army_id=command.army_id,
        parent_id=command.parent_id,
        commander_id=command.commander_id,
    )
    return Effect("A formation takes its place in the order of battle.", command.army_id or command.owner_id, values={"echelon_id": row.id})


@player_action("echelon:edit", ActionKind.EDIT_RECORD)
async def echelon_edit(scope: PlayerScope, command: EchelonEdit) -> Effect:
    row = await control.edit_record(await scope.context("echelon_edit"), "echelon", command.echelon_id, command.values, command.release)
    return Effect("The formation is set so.", getattr(row, "army_entity_id", None) or getattr(row, "owner_entity_id", None))


@player_action("echelon:assign", ActionKind.EDIT_RECORD)
async def echelon_assign(scope: PlayerScope, command: StackAssignment) -> Effect:
    stack = await control.assign_stack(await scope.context("echelon_assign"), command.stack_id, command.echelon_id)
    return Effect("The stack answers to its new formation.", stack.army_entity_id)


@player_action("echelon:delete", ActionKind.EDIT_RECORD)
async def echelon_delete(scope: PlayerScope, command: EchelonTarget) -> Effect:
    await control.delete_record(await scope.context("echelon_delete"), "echelon", command.echelon_id)
    return Effect("The formation is struck from the order of battle.")


@player_action("depot:create", ActionKind.EDIT_RECORD)
async def depot_create(scope: PlayerScope, command: DepotDraft) -> Effect:
    row = await control.found_depot(
        await scope.context("depot_create"), command.owner_id, command.region_id, field=command.field, capacity=command.capacity, supplies=command.supplies
    )
    return Effect("A depot is stocked.", command.owner_id, values={"depot_id": row.id})


@player_action("depot:edit", ActionKind.EDIT_RECORD)
async def depot_edit(scope: PlayerScope, command: DepotEdit) -> Effect:
    row = await control.edit_record(await scope.context("depot_edit"), "depot", command.depot_id, command.values, command.release)
    return Effect("The depot is set so.", getattr(row, "owner_entity_id", None))


@player_action("depot:delete", ActionKind.EDIT_RECORD)
async def depot_delete(scope: PlayerScope, command: DepotTarget) -> Effect:
    await control.delete_record(await scope.context("depot_delete"), "depot", command.depot_id)
    return Effect("The depot is emptied and gone.")


@player_action("transport:create", ActionKind.EDIT_RECORD)
async def transport_create(scope: PlayerScope, command: TransportDraft) -> Effect:
    row = await control.add_transport(await scope.context("transport_create"), command.owner_id, command.kind, command.count, command.depot_id)
    return Effect("Transport joins the train.", command.owner_id, values={"transport_id": row.id})


@player_action("transport:edit", ActionKind.EDIT_RECORD)
async def transport_edit(scope: PlayerScope, command: TransportEdit) -> Effect:
    row = await control.edit_record(await scope.context("transport_edit"), "transport", command.transport_id, command.values, command.release)
    return Effect("The transport is set so.", getattr(row, "owner_entity_id", None))


@player_action("transport:delete", ActionKind.EDIT_RECORD)
async def transport_delete(scope: PlayerScope, command: TransportTarget) -> Effect:
    await control.delete_record(await scope.context("transport_delete"), "transport", command.transport_id)
    return Effect("The transport is gone from the train.")


@player_action("supply_flow:edit", ActionKind.EDIT_RECORD)
async def supply_flow_edit(scope: PlayerScope, command: FlowEdit) -> Effect:
    row = await control.edit_record(await scope.context("supply_flow_edit"), "supply_flow", command.flow_id, command.values, command.release)
    return Effect("The supply flow is set so.", getattr(row, "army_entity_id", None))


@player_action("supply_flow:delete", ActionKind.EDIT_RECORD)
async def supply_flow_delete(scope: PlayerScope, command: FlowTarget) -> Effect:
    await control.delete_record(await scope.context("supply_flow_delete"), "supply_flow", command.flow_id)
    return Effect("The supply flow is struck from the record.")


@player_action("army_operation:set", ActionKind.EDIT_RECORD)
async def army_operation_set(scope: PlayerScope, command: OperationDraft) -> Effect:
    values = {"culminated": command.culminated, "pause_seasons": command.pause_seasons}
    await control.set_operation(await scope.context("army_operation_set"), command.army_id, values)
    return Effect("The army's offensive is set.", command.army_id)


@player_action("army_operation:edit", ActionKind.EDIT_RECORD)
async def army_operation_edit(scope: PlayerScope, command: ArmyEdit) -> Effect:
    await control.edit_record(await scope.context("army_operation_edit"), "army_operation", command.army_id, command.values, command.release)
    return Effect("The army's offensive is set so.", command.army_id)


@player_action("army_operation:delete", ActionKind.EDIT_RECORD)
async def army_operation_delete(scope: PlayerScope, command: ArmyTarget) -> Effect:
    await control.delete_record(await scope.context("army_operation_delete"), "army_operation", command.army_id)
    return Effect("The army's offensive will be read anew.", command.army_id)


@player_action("theatre:set", ActionKind.EDIT_RECORD)
async def theatre_set(scope: PlayerScope, command: TheatreDraft) -> Effect:
    row = await control.open_theatre(await scope.context("theatre_set"), command.owner_id, command.war_id, {"priority": command.priority})
    return Effect("The front's share of reserves is set.", command.owner_id, values={"theatre_id": row.id})


@player_action("theatre:edit", ActionKind.EDIT_RECORD)
async def theatre_edit(scope: PlayerScope, command: TheatreEdit) -> Effect:
    row = await control.edit_record(await scope.context("theatre_edit"), "theatre", command.theatre_id, command.values, command.release)
    return Effect("The theatre is set so.", getattr(row, "owner_entity_id", None))


@player_action("theatre:delete", ActionKind.EDIT_RECORD)
async def theatre_delete(scope: PlayerScope, command: TheatreTarget) -> Effect:
    await control.delete_record(await scope.context("theatre_delete"), "theatre", command.theatre_id)
    return Effect("The theatre will be drawn anew.")


@player_action("ship_state:set", ActionKind.EDIT_RECORD)
async def ship_state_set(scope: PlayerScope, command: ShipDraft) -> Effect:
    values = {"shot": command.shot.value, "point_of_sail": command.point_of_sail.value}
    await control.set_ship(await scope.context("ship_state_set"), command.vessel_id, values)
    return Effect("The ship's sailing and gunnery are set.", command.vessel_id)


@player_action("ship_state:edit", ActionKind.EDIT_RECORD)
async def ship_state_edit(scope: PlayerScope, command: VesselEdit) -> Effect:
    await control.edit_record(await scope.context("ship_state_edit"), "ship_state", command.vessel_id, command.values, command.release)
    return Effect("The ship's state is set so.", command.vessel_id)


@player_action("ship_state:delete", ActionKind.EDIT_RECORD)
async def ship_state_delete(scope: PlayerScope, command: VesselTarget) -> Effect:
    await control.delete_record(await scope.context("ship_state_delete"), "ship_state", command.vessel_id)
    return Effect("The ship's state will be read anew.", command.vessel_id)


@player_action("ship_crew:set", ActionKind.EDIT_RECORD)
async def ship_crew_set(scope: PlayerScope, command: CrewDraft) -> Effect:
    await control.set_crew(await scope.context("ship_crew_set"), command.vessel_id, command.station, {"count": command.count, "skill": command.skill})
    return Effect("The crew station is manned.", command.vessel_id)


@player_action("ship_crew:edit", ActionKind.EDIT_RECORD)
async def ship_crew_edit(scope: PlayerScope, command: CrewEdit) -> Effect:
    key = (command.vessel_id, command.station)
    await control.edit_record(await scope.context("ship_crew_edit"), "ship_crew", key, command.values, command.release)
    return Effect("The crew station is set so.", command.vessel_id)


@player_action("ship_crew:delete", ActionKind.EDIT_RECORD)
async def ship_crew_delete(scope: PlayerScope, command: CrewTarget) -> Effect:
    await control.delete_record(await scope.context("ship_crew_delete"), "ship_crew", (command.vessel_id, command.station))
    return Effect("The crew station will be manned anew.", command.vessel_id)


@player_action("admiralty:set", ActionKind.EDIT_RECORD)
async def admiralty_set(scope: PlayerScope, command: AdmiraltyDraft) -> Effect:
    await control.set_admiralty(await scope.context("admiralty_set"), command.polity_id, {"budget_share": command.budget_share})
    return Effect("The admiralty's share of the war budget is set.", command.polity_id)


@player_action("admiralty:edit", ActionKind.EDIT_RECORD)
async def admiralty_edit(scope: PlayerScope, command: PolityEdit) -> Effect:
    await control.edit_record(await scope.context("admiralty_edit"), "admiralty", command.polity_id, command.values, command.release)
    return Effect("The admiralty is set so.", command.polity_id)


@player_action("admiralty:delete", ActionKind.EDIT_RECORD)
async def admiralty_delete(scope: PlayerScope, command: PolityTarget) -> Effect:
    await control.delete_record(await scope.context("admiralty_delete"), "admiralty", command.polity_id)
    return Effect("The admiralty will be drawn anew.", command.polity_id)


@player_action("expedition:create", ActionKind.EDIT_RECORD)
async def expedition_create(scope: PlayerScope, command: ExpeditionDraft) -> Effect:
    row = await control.send_expedition(
        await scope.context("expedition_create"), command.leader_id, command.target_id, command.companion_ids, command.sponsor_id
    )
    return Effect("An expedition sets out.", command.leader_id, values={"expedition_id": row.id})


@player_action("expedition:edit", ActionKind.EDIT_RECORD)
async def expedition_edit(scope: PlayerScope, command: ExpeditionEdit) -> Effect:
    row = await control.edit_record(await scope.context("expedition_edit"), "expedition", command.expedition_id, command.values, command.release)
    return Effect("The expedition is set so.", getattr(row, "leader_entity_id", None))


@player_action("expedition:advance", ActionKind.EDIT_RECORD)
async def expedition_advance(scope: PlayerScope, command: ExpeditionPush) -> Effect:
    row = await control.press_on(await scope.context("expedition_advance"), command.expedition_id, command.legs)
    return Effect("The expedition presses on.", row.leader_entity_id)


@player_action("expedition:recall", ActionKind.EDIT_RECORD)
async def expedition_recall(scope: PlayerScope, command: ExpeditionTarget) -> Effect:
    row = await control.recall(await scope.context("expedition_recall"), command.expedition_id)
    return Effect("The expedition turns for home.", row.leader_entity_id)


@player_action("expedition:delete", ActionKind.EDIT_RECORD)
async def expedition_delete(scope: PlayerScope, command: ExpeditionTarget) -> Effect:
    await control.delete_record(await scope.context("expedition_delete"), "expedition", command.expedition_id)
    return Effect("The expedition is struck from the record.")


@player_action("expedition_member:create", ActionKind.EDIT_RECORD)
async def expedition_member_create(scope: PlayerScope, command: MemberDraft) -> Effect:
    row = await control.add_member(await scope.context("expedition_member_create"), command.expedition_id, command.mortal_id, command.role)
    return Effect("A member joins the party.", command.mortal_id, values={"member_id": row.id})


@player_action("expedition_member:edit", ActionKind.EDIT_RECORD)
async def expedition_member_edit(scope: PlayerScope, command: MemberEdit) -> Effect:
    row = await control.edit_record(await scope.context("expedition_member_edit"), "expedition_member", command.member_id, command.values, command.release)
    return Effect("The member is set so.", getattr(row, "mortal_entity_id", None))


@player_action("expedition_member:delete", ActionKind.EDIT_RECORD)
async def expedition_member_delete(scope: PlayerScope, command: MemberTarget) -> Effect:
    await control.delete_record(await scope.context("expedition_member_delete"), "expedition_member", command.member_id)
    return Effect("The member leaves the party.")


@player_action("expedition_log:edit", ActionKind.EDIT_RECORD)
async def expedition_log_edit(scope: PlayerScope, command: LogEdit) -> Effect:
    await control.edit_record(await scope.context("expedition_log_edit"), "expedition_log", command.log_id, command.values, command.release)
    return Effect("The log entry is set so.")


@player_action("expedition_log:delete", ActionKind.EDIT_RECORD)
async def expedition_log_delete(scope: PlayerScope, command: LogTarget) -> Effect:
    await control.delete_record(await scope.context("expedition_log_delete"), "expedition_log", command.log_id)
    return Effect("The log entry is struck out.")


@player_action("quirk:create", ActionKind.EDIT_RECORD)
async def quirk_create(scope: PlayerScope, command: QuirkDraft) -> Effect:
    row = await control.give_quirk(await scope.context("quirk_create"), command.mortal_id, command.kind, command.source_id)
    return Effect("A quirk marks the mortal.", command.mortal_id, values={"quirk_id": row.id})


@player_action("quirk:edit", ActionKind.EDIT_RECORD)
async def quirk_edit(scope: PlayerScope, command: QuirkEdit) -> Effect:
    row = await control.edit_record(await scope.context("quirk_edit"), "quirk", command.quirk_id, command.values, command.release)
    return Effect("The quirk is set so.", getattr(row, "mortal_entity_id", None))


@player_action("quirk:delete", ActionKind.EDIT_RECORD)
async def quirk_delete(scope: PlayerScope, command: QuirkTarget) -> Effect:
    await control.delete_record(await scope.context("quirk_delete"), "quirk", command.quirk_id)
    return Effect("The quirk fades.")
