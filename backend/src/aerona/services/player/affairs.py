from pydantic import Field

from aerona.catalog.statecraft import RESOLUTION_TEXT as KIND_TEXT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.grammar import agree, an, several, spoken
from aerona.db.faction_kinds import kind_of
from aerona.db.tables.affairs import (
    RATE_MAX,
    CouncilSeatRow,
    CourtPositionRow,
    CourtRow,
    ElectionRow,
    MandateRow,
    NobleDemandRow,
    PolicyApprovalRow,
    ResolutionRow,
    ResolutionVoteRow,
    TaxPolicyRow,
)
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.polity import OfficeRow, PolityProfileRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.settlement import DistrictKind
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.statecraft import CouncilTask, CourtPosition, MandateKind, MandateState, NobleWant, ResolutionKind, ResolutionState, TaxKind
from aerona.engine.polity.book import RealmBook
from aerona.engine.polity.elections import ElectionTally, elect
from aerona.engine.polity.laws import LawBook
from aerona.engine.polity.mandates import issue
from aerona.engine.primitives.manual import manual_context
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

SPAN = 100
POLITY = frozenset({EntityType.POLITY})


class SetTask(Command):
    office_id: int
    task: CouncilTask | None = None
    target_id: int | None = None
    diligence: int | None = Field(default=None, ge=0, le=SPAN)
    hold: bool = True


class CallElection(Command):
    polity_id: int


class ElectionTarget(Command):
    election_id: int


class SetSeat(Command):
    polity_id: int
    holder_id: int
    seats: int = Field(ge=0, le=200)
    votes: int = Field(default=0, ge=0, le=SPAN)
    hold: bool = True


class SeatTarget(Command):
    polity_id: int
    holder_id: int


class SetCorruption(Command):
    polity_id: int
    corruption: int = Field(ge=0, le=SPAN)
    hold: bool = True


class SetTax(Command):
    polity_id: int
    kind: TaxKind
    rate: int | None = Field(default=None, ge=0, le=RATE_MAX)
    farmed: bool | None = None
    efficiency: int | None = Field(default=None, ge=0, le=SPAN)
    hold: bool = True


class TaxTarget(Command):
    polity_id: int
    kind: TaxKind


class IssueMandate(Command):
    polity_id: int
    kind: MandateKind
    settlement_id: int | None = None
    commodity: CommodityKind | None = None
    district: DistrictKind | None = None
    amount: int = Field(default=0, ge=0, le=1_000_000)


class EditMandate(Command):
    mandate_id: int
    state: MandateState | None = None
    until_epoch: int | None = Field(default=None, ge=0)
    amount: int | None = Field(default=None, ge=0, le=1_000_000)
    hold: bool = True


class MandateTarget(Command):
    mandate_id: int


class SetDemand(Command):
    mortal_id: int
    want: NobleWant
    met: bool = False
    hold: bool = True


class DemandTarget(Command):
    mortal_id: int
    want: NobleWant


class SetApproval(Command):
    polity_id: int
    social_class: SocialClass
    approval: int = Field(ge=-SPAN, le=SPAN)
    hold: bool = True


class ApprovalTarget(Command):
    polity_id: int
    social_class: SocialClass


def held(locked: list[str] | None, fields: list[str], hold: bool) -> list[str]:
    found = set(locked or [])
    return sorted(found | set(fields)) if hold else sorted(found - set(fields))


async def realm(scope: PlayerScope, entity_id: int) -> EntityRow:
    found = await scope.session.get(EntityRow, entity_id)
    if found is None or found.entity_type not in POLITY:
        raise ValidationFailedError("That is not a realm.")
    return found


@player_action("council:task", ActionKind.EDIT_RECORD)
async def set_task(scope: PlayerScope, command: SetTask) -> Effect:
    office = await scope.session.get(OfficeRow, command.office_id)
    if office is None:
        raise NotFoundError("No such office.")
    touched: list[str] = []
    if command.task is not None:
        office.task = command.task
        touched.append("task")
    if command.target_id is not None:
        if await scope.session.get(NodeRow, command.target_id) is None:
            raise ValidationFailedError("The target must be a thing of the cosmos.")
        office.task_target_node_id = command.target_id
        touched.append("task")
    if command.diligence is not None:
        office.diligence = command.diligence
        touched.append("diligence")
    if not touched:
        raise ValidationFailedError("Set a task, a target or a diligence.")
    office.locked = held(office.locked, touched, command.hold)
    await scope.session.flush()
    task = spoken(office.task) if office.task is not None else "no task"
    return Effect(f"The {spoken(office.kind)} works at {task}, diligence {office.diligence}.", target_node_id=office.polity_entity_id)


@player_action("election:call", ActionKind.EDIT_RECORD)
async def call_election(scope: PlayerScope, command: CallElection) -> Effect:
    found = await realm(scope, command.polity_id)
    ctx = await manual_context(scope.session, "election.call")
    book = await RealmBook.load(scope.session)
    target = book.realms.get(found.id)
    if target is None:
        raise ValidationFailedError("That realm has fallen.")
    tally = ElectionTally()
    await elect(ctx, book, await LawBook.load(scope.session), target, tally, force=True)
    await scope.session.flush()
    return Effect(
        f"{found.name} went to the polls; {several(tally.seats, 'seat', 'seats')} {agree(tally.seats, 'was', 'were')} filled.", target_node_id=found.id
    )


@player_action("election:delete", ActionKind.EDIT_RECORD)
async def delete_election(scope: PlayerScope, command: ElectionTarget) -> Effect:
    row = await scope.session.get(ElectionRow, command.election_id)
    if row is None:
        raise NotFoundError("No such election.")
    polity = row.polity_entity_id
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect("The election was struck from the record.", target_node_id=polity)


@player_action("seat:set", ActionKind.EDIT_RECORD)
async def set_seat(scope: PlayerScope, command: SetSeat) -> Effect:
    found = await realm(scope, command.polity_id)
    if await scope.session.get(NodeRow, command.holder_id) is None:
        raise ValidationFailedError("The holder must be a thing of the cosmos.")
    row = await scope.session.get(CouncilSeatRow, (found.id, command.holder_id))
    if row is None:
        row = CouncilSeatRow(polity_entity_id=found.id, holder_node_id=command.holder_id, since_epoch=await scope.epoch())
        scope.session.add(row)
    row.seats, row.votes, row.locked = command.seats, command.votes, command.hold
    await scope.session.flush()
    return Effect(f"The holder sits with {several(command.seats, 'seat', 'seats')} in the council of {found.name}.", target_node_id=found.id)


@player_action("seat:remove", ActionKind.EDIT_RECORD)
async def remove_seat(scope: PlayerScope, command: SeatTarget) -> Effect:
    row = await scope.session.get(CouncilSeatRow, (command.polity_id, command.holder_id))
    if row is None:
        raise NotFoundError("That holder has no seat.")
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect("The seat was emptied.", target_node_id=command.polity_id)


@player_action("corruption:set", ActionKind.EDIT_RECORD)
async def set_corruption(scope: PlayerScope, command: SetCorruption) -> Effect:
    found = await realm(scope, command.polity_id)
    profile = await scope.session.get(PolityProfileRow, found.id)
    if profile is None:
        raise ValidationFailedError("That realm has no profile.")
    profile.corruption = command.corruption
    profile.locked = held(profile.locked, ["corruption"], command.hold)
    await scope.session.flush()
    return Effect(f"Corruption in {found.name} stands at {command.corruption}.", target_node_id=found.id)


@player_action("tax:set", ActionKind.EDIT_RECORD)
async def set_tax(scope: PlayerScope, command: SetTax) -> Effect:
    found = await realm(scope, command.polity_id)
    row = await scope.session.get(TaxPolicyRow, (found.id, command.kind))
    if row is None:
        row = TaxPolicyRow(polity_entity_id=found.id, kind=command.kind, epoch=await scope.epoch(), locked=[])
        scope.session.add(row)
    touched: list[str] = []
    for key in ("rate", "farmed", "efficiency"):
        value = getattr(command, key)
        if value is not None:
            setattr(row, key, value)
            touched.append(key)
    if not touched:
        raise ValidationFailedError("Set a rate, farming or efficiency.")
    row.locked = held(row.locked, touched, command.hold)
    await scope.session.flush()
    farmed = ", farmed out" if row.farmed else ""
    return Effect(f"The {spoken(command.kind)} tax of {found.name} stands at {row.rate}{farmed}.", target_node_id=found.id)


@player_action("tax:remove", ActionKind.EDIT_RECORD)
async def remove_tax(scope: PlayerScope, command: TaxTarget) -> Effect:
    row = await scope.session.get(TaxPolicyRow, (command.polity_id, command.kind))
    if row is None:
        raise NotFoundError("The realm keeps no such tax.")
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect("The tax returns to its custom at the next epoch.", target_node_id=command.polity_id)


@player_action("mandate:issue", ActionKind.EDIT_RECORD)
async def issue_mandate(scope: PlayerScope, command: IssueMandate) -> Effect:
    found = await realm(scope, command.polity_id)
    if command.settlement_id is not None:
        town = await scope.session.get(EntityRow, command.settlement_id)
        if town is None or town.entity_type is not EntityType.SETTLEMENT:
            raise ValidationFailedError("A mandate is laid on a settlement.")
    ctx = await manual_context(scope.session, "mandate.issue")
    target = (await RealmBook.load(scope.session)).realms.get(found.id)
    if target is None:
        raise ValidationFailedError("That realm has fallen.")
    row = await issue(
        ctx, target, command.kind, settlement_id=command.settlement_id, commodity=command.commodity, district=command.district, amount=command.amount
    )
    if row is None:
        raise ValidationFailedError("Such a mandate already stands, or a god holds the realm.")
    await scope.session.flush()
    return Effect(f"{found.name} issued {an(spoken(command.kind))} mandate.", target_node_id=found.id, values={"mandate_id": row.id})


@player_action("mandate:edit", ActionKind.EDIT_RECORD)
async def edit_mandate(scope: PlayerScope, command: EditMandate) -> Effect:
    row = await scope.session.get(MandateRow, command.mandate_id)
    if row is None:
        raise NotFoundError("No such mandate.")
    touched: list[str] = []
    for key in ("state", "until_epoch", "amount"):
        value = getattr(command, key)
        if value is not None:
            setattr(row, key, value)
            touched.append(key)
    if not touched:
        raise ValidationFailedError("Set at least one value.")
    row.locked = held(row.locked, touched, command.hold)
    await scope.session.flush()
    return Effect(f"The mandate stands {spoken(row.state)} until epoch {row.until_epoch}.", target_node_id=row.polity_entity_id)


@player_action("mandate:delete", ActionKind.EDIT_RECORD)
async def delete_mandate(scope: PlayerScope, command: MandateTarget) -> Effect:
    row = await scope.session.get(MandateRow, command.mandate_id)
    if row is None:
        raise NotFoundError("No such mandate.")
    polity = row.polity_entity_id
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect("The mandate was withdrawn.", target_node_id=polity)


@player_action("demand:set", ActionKind.EDIT_RECORD)
async def set_demand(scope: PlayerScope, command: SetDemand) -> Effect:
    noble = await scope.session.get(EntityRow, command.mortal_id)
    if noble is None or noble.entity_type is not EntityType.MORTAL:
        raise ValidationFailedError("Only a mortal makes demands.")
    row = await scope.session.get(NobleDemandRow, (noble.id, command.want))
    if row is None:
        row = NobleDemandRow(mortal_entity_id=noble.id, want=command.want, since_epoch=await scope.epoch())
        scope.session.add(row)
    row.met, row.locked = command.met, command.hold
    await scope.session.flush()
    state = "met" if command.met else "unmet"
    return Effect(f"{noble.name}'s demand for {spoken(command.want)} stands {state}.", target_node_id=noble.id)


@player_action("demand:remove", ActionKind.EDIT_RECORD)
async def remove_demand(scope: PlayerScope, command: DemandTarget) -> Effect:
    row = await scope.session.get(NobleDemandRow, (command.mortal_id, command.want))
    if row is None:
        raise NotFoundError("No such demand.")
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect("The demand was forgotten.", target_node_id=command.mortal_id)


@player_action("approval:set", ActionKind.EDIT_RECORD)
async def set_approval(scope: PlayerScope, command: SetApproval) -> Effect:
    found = await realm(scope, command.polity_id)
    row = await scope.session.get(PolicyApprovalRow, (found.id, command.social_class))
    if row is None:
        row = PolicyApprovalRow(polity_entity_id=found.id, social_class=command.social_class, epoch=await scope.epoch(), locked=[])
        scope.session.add(row)
    row.approval = command.approval
    row.locked = held(row.locked, ["approval"], command.hold)
    await scope.session.flush()
    return Effect(f"The {spoken(command.social_class)} class approves of the realm's ways at {command.approval}.", target_node_id=found.id)


@player_action("approval:remove", ActionKind.EDIT_RECORD)
async def remove_approval(scope: PlayerScope, command: ApprovalTarget) -> Effect:
    row = await scope.session.get(PolicyApprovalRow, (command.polity_id, command.social_class))
    if row is None:
        raise NotFoundError("No such approval.")
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect("The approval will be weighed anew.", target_node_id=command.polity_id)


class ProposeResolution(Command):
    assembly_id: int
    kind: ResolutionKind
    target_id: int | None = None


class ResolutionTarget(Command):
    resolution_id: int


class EditResolution(Command):
    resolution_id: int
    state: ResolutionState | None = None
    until_epoch: int | None = Field(default=None, ge=0)
    votes_for: int | None = Field(default=None, ge=0, le=1_000_000)
    votes_against: int | None = Field(default=None, ge=0, le=1_000_000)
    hold: bool = True


class HoldResolution(Command):
    resolution_id: int
    hold: bool = True


class SetVote(Command):
    resolution_id: int
    member_id: int
    aye: bool
    weight: int = Field(default=1, ge=0, le=1_000_000)
    hold: bool = True


class VoteTarget(Command):
    resolution_id: int
    member_id: int


class EditCourt(Command):
    polity_id: int
    grandeur: int | None = Field(default=None, ge=0, le=SPAN)
    courtiers: int | None = Field(default=None, ge=0, le=10_000)
    hold: bool = True


class SetPosition(Command):
    polity_id: int
    position: CourtPosition
    holder_id: int | None = None
    hold: bool = True


class PositionTarget(Command):
    polity_id: int
    position: CourtPosition


RESOLUTION_FIELDS = ["state", "until_epoch", "votes_for", "votes_against"]


async def resolution_of(scope: PlayerScope, resolution_id: int) -> ResolutionRow:
    row = await scope.session.get(ResolutionRow, resolution_id)
    if row is None:
        raise NotFoundError("No such resolution.")
    return row


@player_action("resolution:propose", ActionKind.EDIT_RECORD)
async def propose_resolution(scope: PlayerScope, command: ProposeResolution) -> Effect:
    assembly = await scope.session.get(EntityRow, command.assembly_id)
    if assembly is None or await kind_of(scope.session, assembly.id) is not FactionKind.INTERWORLD_FEDERATION:
        raise ValidationFailedError("Resolutions are brought before an interworld assembly.")
    if command.target_id is not None and await scope.session.get(NodeRow, command.target_id) is None:
        raise ValidationFailedError("The target must be a thing of the cosmos.")
    row = ResolutionRow(assembly_entity_id=assembly.id, kind=command.kind, target_node_id=command.target_id, proposed_epoch=await scope.epoch(), locked=[])
    scope.session.add(row)
    await scope.session.flush()
    return Effect(f"A resolution to {KIND_TEXT[command.kind]} stands before {assembly.name}.", target_node_id=assembly.id, values={"resolution_id": row.id})


@player_action("resolution:edit", ActionKind.EDIT_RECORD)
async def edit_resolution(scope: PlayerScope, command: EditResolution) -> Effect:
    row = await resolution_of(scope, command.resolution_id)
    touched: list[str] = []
    for key in RESOLUTION_FIELDS:
        value = getattr(command, key)
        if value is not None:
            setattr(row, key, value)
            touched.append(key)
    if not touched:
        raise ValidationFailedError("Set at least one value.")
    row.locked = held(row.locked, touched, command.hold)
    await scope.session.flush()
    return Effect(f"The resolution stands {spoken(row.state)}, {row.votes_for} for and {row.votes_against} against.", target_node_id=row.assembly_entity_id)


@player_action("resolution:hold", ActionKind.EDIT_RECORD)
async def hold_resolution(scope: PlayerScope, command: HoldResolution) -> Effect:
    row = await resolution_of(scope, command.resolution_id)
    row.locked = held(row.locked, RESOLUTION_FIELDS, command.hold)
    await scope.session.flush()
    return Effect("The resolution is held as it stands." if command.hold else "The resolution runs its course again.", target_node_id=row.assembly_entity_id)


@player_action("resolution:delete", ActionKind.EDIT_RECORD)
async def delete_resolution(scope: PlayerScope, command: ResolutionTarget) -> Effect:
    row = await resolution_of(scope, command.resolution_id)
    assembly = row.assembly_entity_id
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect("The resolution was struck.", target_node_id=assembly)


@player_action("vote:set", ActionKind.EDIT_RECORD)
async def set_vote(scope: PlayerScope, command: SetVote) -> Effect:
    row = await resolution_of(scope, command.resolution_id)
    if await scope.session.get(NodeRow, command.member_id) is None:
        raise ValidationFailedError("The voter must be a thing of the cosmos.")
    found = await scope.session.get(ResolutionVoteRow, (row.id, command.member_id))
    if found is None:
        found = ResolutionVoteRow(resolution_id=row.id, member_node_id=command.member_id)
        scope.session.add(found)
    found.aye, found.weight, found.locked = command.aye, command.weight, command.hold
    await scope.session.flush()
    return Effect(f"The vote stands {'for' if command.aye else 'against'}, with weight {command.weight}.", target_node_id=row.assembly_entity_id)


@player_action("vote:remove", ActionKind.EDIT_RECORD)
async def remove_vote(scope: PlayerScope, command: VoteTarget) -> Effect:
    found = await scope.session.get(ResolutionVoteRow, (command.resolution_id, command.member_id))
    if found is None:
        raise NotFoundError("That member cast no vote.")
    await scope.session.delete(found)
    await scope.session.flush()
    return Effect("The vote was struck.", target_node_id=command.member_id)


@player_action("court:edit", ActionKind.EDIT_RECORD)
async def edit_court(scope: PlayerScope, command: EditCourt) -> Effect:
    found = await realm(scope, command.polity_id)
    row = await scope.session.get(CourtRow, found.id)
    if row is None:
        row = CourtRow(polity_entity_id=found.id, epoch=await scope.epoch(), locked=[])
        scope.session.add(row)
    touched: list[str] = []
    for key in ("grandeur", "courtiers"):
        value = getattr(command, key)
        if value is not None:
            setattr(row, key, value)
            touched.append(key)
    if not touched:
        raise ValidationFailedError("Set a grandeur or a count of courtiers.")
    row.locked = held(row.locked, touched, command.hold)
    await scope.session.flush()
    return Effect(f"The court of {found.name} now stands at grandeur {row.grandeur}.", target_node_id=found.id)


@player_action("position:set", ActionKind.EDIT_RECORD)
async def set_position(scope: PlayerScope, command: SetPosition) -> Effect:
    found = await realm(scope, command.polity_id)
    holder = await scope.session.get(EntityRow, command.holder_id) if command.holder_id is not None else None
    if command.holder_id is not None and (holder is None or holder.entity_type is not EntityType.MORTAL):
        raise ValidationFailedError("A court position is held by a mortal.")
    row = await scope.session.get(CourtPositionRow, (found.id, command.position))
    if row is None:
        row = CourtPositionRow(polity_entity_id=found.id, position=command.position, since_epoch=await scope.epoch())
        scope.session.add(row)
    row.holder_entity_id, row.locked = command.holder_id, command.hold
    await scope.session.flush()
    who = holder.name if holder is not None else "no one"
    return Effect(f"The {spoken(command.position)} of {found.name} is {who}.", target_node_id=found.id)


@player_action("position:remove", ActionKind.EDIT_RECORD)
async def remove_position(scope: PlayerScope, command: PositionTarget) -> Effect:
    row = await scope.session.get(CourtPositionRow, (command.polity_id, command.position))
    if row is None:
        raise NotFoundError("The court has no such position.")
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect("The position was struck from the court.", target_node_id=command.polity_id)
