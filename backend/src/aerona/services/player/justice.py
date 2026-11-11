from pydantic import Field

from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.justice import CaseWitnessRow, CrimeCaseRow, LawProposalRow, ProposalStanceRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.polity import LawProfileRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.justice import CaseStage, Deposition, ProposalStance, ProposalState, TrialKind
from aerona.domain.enums.law_depth import CourtLevel
from aerona.domain.enums.mortal import CrimeKind
from aerona.domain.enums.polity import LawKind, LegitimacyBasis
from aerona.engine.polity.enactment import law_title, pass_now
from aerona.engine.polity.laws import LawBook, validate
from aerona.engine.polity.trials import TrialTally, try_case
from aerona.engine.primitives.manual import manual_context
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

SPAN = 100
PROPOSAL_FIELDS = ("params", "champion_node_id", "progress", "support", "opposition", "stalled_epochs", "state", "basis")
CASE_FIELDS = ("accused", "culprit", "judge", "investigator", "advocate", "trial", "evidence", "stage", "verdict", "court")
TERMS = int | str | bool


class CreateProposal(Command):
    polity_id: int
    kind: LawKind
    params: dict[str, TERMS] = Field(default_factory=dict)
    champion_id: int | None = None
    law_id: int | None = None
    basis: LegitimacyBasis = LegitimacyBasis.COUNCIL


class ProposalTarget(Command):
    proposal_id: int


class EditProposal(Command):
    proposal_id: int
    params: dict[str, TERMS] | None = None
    champion_id: int | None = None
    clear_champion: bool = False
    basis: LegitimacyBasis | None = None
    progress: int | None = Field(default=None, ge=0, le=SPAN)
    support: int | None = Field(default=None, ge=0, le=SPAN)
    opposition: int | None = Field(default=None, ge=0, le=SPAN)
    stalled_epochs: int | None = Field(default=None, ge=0, le=SPAN)
    state: ProposalState | None = None
    hold: bool = True


class HoldProposal(Command):
    proposal_id: int
    hold: bool = True


class SetStance(Command):
    proposal_id: int
    node_id: int
    stance: ProposalStance
    weight: int = Field(ge=0, le=SPAN)
    hold: bool = True


class StanceTarget(Command):
    proposal_id: int
    node_id: int


class OpenCase(Command):
    settlement_id: int
    crime: CrimeKind
    accused_id: int
    culprit_id: int | None = None
    judge_id: int | None = None
    investigator_id: int | None = None
    trial: TrialKind = TrialKind.JUDGE
    evidence: int = Field(default=50, ge=0, le=SPAN)


class CaseTarget(Command):
    case_id: int


class EditCase(Command):
    case_id: int
    accused_id: int | None = None
    culprit_id: int | None = None
    clear_culprit: bool = False
    judge_id: int | None = None
    investigator_id: int | None = None
    advocate_id: int | None = None
    clear_advocate: bool = False
    trial: TrialKind | None = None
    evidence: int | None = Field(default=None, ge=0, le=SPAN)
    stage: CaseStage | None = None
    crime: CrimeKind | None = None
    court: CourtLevel | None = None
    hold: bool = True


class HoldCase(Command):
    case_id: int
    hold: bool = True


class SetWitness(Command):
    case_id: int
    witness_id: int
    testimony: Deposition
    reliability: int = Field(ge=0, le=SPAN)
    hold: bool = True


class WitnessTarget(Command):
    case_id: int
    witness_id: int


def held(locked: list[str] | None, fields: list[str] | tuple[str, ...], hold: bool) -> list[str]:
    found = set(locked or [])
    return sorted(found | set(fields)) if hold else sorted(found - set(fields))


async def entity(scope: PlayerScope, entity_id: int | None, label: str, kinds: frozenset[EntityType]) -> EntityRow:
    found = await scope.session.get(EntityRow, entity_id) if entity_id is not None else None
    if found is None or found.entity_type not in kinds:
        raise ValidationFailedError(f"{label} is not the right kind of record.")
    return found


async def node(scope: PlayerScope, node_id: int, label: str) -> NodeRow:
    found = await scope.session.get(NodeRow, node_id)
    if found is None:
        raise ValidationFailedError(f"{label} must be a living thing of the cosmos.")
    return found


async def proposal(scope: PlayerScope, proposal_id: int) -> LawProposalRow:
    row = await scope.session.get(LawProposalRow, proposal_id)
    if row is None:
        raise NotFoundError("No such proposal.")
    return row


async def case_of(scope: PlayerScope, case_id: int) -> CrimeCaseRow:
    row = await scope.session.get(CrimeCaseRow, case_id)
    if row is None:
        raise NotFoundError("No such case.")
    return row


MORTALS = frozenset({EntityType.MORTAL})


@player_action("proposal:create", ActionKind.EDIT_RECORD)
async def create_proposal(scope: PlayerScope, command: CreateProposal) -> Effect:
    realm = await entity(scope, command.polity_id, "The realm", frozenset({EntityType.POLITY}))
    if command.champion_id is not None:
        await node(scope, command.champion_id, "The champion")
    if command.law_id is not None:
        current = await scope.session.get(LawProfileRow, command.law_id)
        if current is None or current.kind is not command.kind:
            raise ValidationFailedError("An amendment must name a law of the same kind.")
    row = LawProposalRow(
        polity_entity_id=realm.id,
        kind=command.kind,
        params=validate(command.kind, command.params),
        champion_node_id=command.champion_id,
        law_entity_id=command.law_id,
        basis=command.basis,
        proposed_epoch=await scope.epoch(),
        locked=[],
    )
    scope.session.add(row)
    await scope.session.flush()
    return Effect(f"{law_title(command.kind).capitalize()} now stands before {realm.name}.", target_node_id=realm.id, values={"proposal_id": row.id})


@player_action("proposal:edit", ActionKind.EDIT_RECORD)
async def edit_proposal(scope: PlayerScope, command: EditProposal) -> Effect:
    row = await proposal(scope, command.proposal_id)
    touched: list[str] = []
    if command.params is not None:
        row.params = validate(row.kind, command.params)
        touched.append("params")
    if command.champion_id is not None:
        row.champion_node_id = (await node(scope, command.champion_id, "The champion")).id
        touched.append("champion_node_id")
    elif command.clear_champion:
        row.champion_node_id = None
        touched.append("champion_node_id")
    for key in ("basis", "progress", "support", "opposition", "stalled_epochs", "state"):
        value = getattr(command, key)
        if value is not None:
            setattr(row, key, value)
            touched.append(key)
    if command.state is not None:
        row.resolved_epoch = None if command.state is ProposalState.DEBATING else await scope.epoch()
    if not touched:
        raise ValidationFailedError("Set at least one value.")
    row.locked = held(row.locked, touched, command.hold)
    await scope.session.flush()
    return Effect(f"The proposal stands at {row.progress} of 100, {row.support} for and {row.opposition} against.", target_node_id=row.polity_entity_id)


@player_action("proposal:hold", ActionKind.EDIT_RECORD)
async def hold_proposal(scope: PlayerScope, command: HoldProposal) -> Effect:
    row = await proposal(scope, command.proposal_id)
    row.locked = held(row.locked, PROPOSAL_FIELDS, command.hold)
    await scope.session.flush()
    return Effect("The proposal is held where it stands." if command.hold else "The proposal moves with the realm again.", target_node_id=row.polity_entity_id)


@player_action("proposal:pass", ActionKind.EDIT_RECORD)
async def pass_proposal(scope: PlayerScope, command: ProposalTarget) -> Effect:
    row = await proposal(scope, command.proposal_id)
    if row.state is not ProposalState.DEBATING:
        raise ValidationFailedError("Only a proposal under debate can be carried.")
    ctx = await manual_context(scope.session, "proposal.pass")
    law = await pass_now(ctx, row)
    if law is None:
        raise ValidationFailedError("The proposal's realm no longer stands.")
    await scope.session.flush()
    return Effect(f"By the Creator's word, {law.name} became law.", target_node_id=row.polity_entity_id, values={"law_id": law.id})


@player_action("proposal:delete", ActionKind.EDIT_RECORD)
async def delete_proposal(scope: PlayerScope, command: ProposalTarget) -> Effect:
    row = await proposal(scope, command.proposal_id)
    polity = row.polity_entity_id
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect("The proposal was struck from the record.", target_node_id=polity)


@player_action("stance:set", ActionKind.EDIT_RECORD)
async def set_stance(scope: PlayerScope, command: SetStance) -> Effect:
    row = await proposal(scope, command.proposal_id)
    await node(scope, command.node_id, "The voice")
    found = await scope.session.get(ProposalStanceRow, (row.id, command.node_id))
    if found is None:
        found = ProposalStanceRow(proposal_id=row.id, node_id=command.node_id, stance=command.stance, weight=command.weight)
        scope.session.add(found)
    found.stance, found.weight, found.locked = command.stance, command.weight, command.hold
    await scope.session.flush()
    return Effect(f"A voice of weight {command.weight} now stands {command.stance.value} on the proposal.", target_node_id=row.polity_entity_id)


@player_action("stance:remove", ActionKind.EDIT_RECORD)
async def remove_stance(scope: PlayerScope, command: StanceTarget) -> Effect:
    found = await scope.session.get(ProposalStanceRow, (command.proposal_id, command.node_id))
    if found is None:
        raise NotFoundError("That voice has no stance on this proposal.")
    await scope.session.delete(found)
    await scope.session.flush()
    return Effect("The voice fell silent on the proposal.", target_node_id=command.node_id)


@player_action("case:open", ActionKind.EDIT_RECORD)
async def open_case(scope: PlayerScope, command: OpenCase) -> Effect:
    town = await entity(scope, command.settlement_id, "The court's city", frozenset({EntityType.SETTLEMENT}))
    accused = await entity(scope, command.accused_id, "The accused", MORTALS)
    culprit = await entity(scope, command.culprit_id, "The culprit", MORTALS) if command.culprit_id is not None else None
    judge = await entity(scope, command.judge_id, "The judge", MORTALS) if command.judge_id is not None else None
    finder = await entity(scope, command.investigator_id, "The investigator", MORTALS) if command.investigator_id is not None else None
    laws = await LawBook.load(scope.session)
    row = CrimeCaseRow(
        settlement_entity_id=town.id,
        polity_entity_id=laws.member_of.get(town.id),
        crime=command.crime,
        culprit_entity_id=culprit.id if culprit is not None else None,
        accused_entity_id=accused.id,
        investigator_entity_id=finder.id if finder is not None else None,
        judge_entity_id=judge.id if judge is not None else None,
        stage=CaseStage.TRIAL,
        trial=command.trial,
        evidence=command.evidence,
        opened_epoch=await scope.epoch(),
        locked=[],
    )
    scope.session.add(row)
    await scope.session.flush()
    return Effect(f"{accused.name} stands accused in {town.name}.", target_node_id=accused.id, values={"case_id": row.id})


@player_action("case:edit", ActionKind.EDIT_RECORD)
async def edit_case(scope: PlayerScope, command: EditCase) -> Effect:
    row = await case_of(scope, command.case_id)
    touched: list[str] = []
    people = (
        ("accused", "accused_entity_id", command.accused_id, "The accused"),
        ("culprit", "culprit_entity_id", command.culprit_id, "The culprit"),
        ("judge", "judge_entity_id", command.judge_id, "The judge"),
        ("investigator", "investigator_entity_id", command.investigator_id, "The investigator"),
        ("advocate", "advocate_entity_id", command.advocate_id, "The advocate"),
    )
    for field, column, value, label in people:
        if value is not None:
            setattr(row, column, (await entity(scope, value, label, MORTALS)).id)
            touched.append(field)
    if command.clear_culprit:
        row.culprit_entity_id = None
        touched.append("culprit")
    if command.clear_advocate:
        row.advocate_entity_id = None
        touched.append("advocate")
    for key in ("trial", "evidence", "stage", "crime", "court"):
        value = getattr(command, key)
        if value is not None:
            setattr(row, key, value)
            touched.append(key)
    if command.stage is not None and command.stage is not CaseStage.CLOSED:
        row.verdict, row.closed_epoch = None, None
    if not touched:
        raise ValidationFailedError("Set at least one value.")
    row.locked = held(row.locked, touched, command.hold)
    await scope.session.flush()
    return Effect(f"The case stands at {row.stage.value} with evidence {row.evidence}.", target_node_id=row.accused_entity_id)


@player_action("case:hold", ActionKind.EDIT_RECORD)
async def hold_case(scope: PlayerScope, command: HoldCase) -> Effect:
    row = await case_of(scope, command.case_id)
    row.locked = held(row.locked, CASE_FIELDS, command.hold)
    await scope.session.flush()
    return Effect(
        "The case is held, its verdict waiting on the Creator." if command.hold else "The case runs its course again.", target_node_id=row.accused_entity_id
    )


@player_action("case:try", ActionKind.EDIT_RECORD)
async def try_now(scope: PlayerScope, command: CaseTarget) -> Effect:
    row = await case_of(scope, command.case_id)
    if row.stage is CaseStage.CLOSED:
        raise ValidationFailedError("That case is already closed.")
    if row.accused_entity_id is None:
        raise ValidationFailedError("Name the accused before the trial.")
    ctx = await manual_context(scope.session, "case.try")
    await try_case(ctx, row, await LawBook.load(scope.session), TrialTally())
    await scope.session.flush()
    verdict = row.verdict.value if row.verdict is not None else "undecided"
    return Effect(f"The trial ended: {verdict}.", target_node_id=row.accused_entity_id, values={"verdict": verdict})


@player_action("case:delete", ActionKind.EDIT_RECORD)
async def delete_case(scope: PlayerScope, command: CaseTarget) -> Effect:
    row = await case_of(scope, command.case_id)
    accused = row.accused_entity_id
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect("The case was struck from the rolls.", target_node_id=accused)


@player_action("witness:set", ActionKind.EDIT_RECORD)
async def set_witness(scope: PlayerScope, command: SetWitness) -> Effect:
    row = await case_of(scope, command.case_id)
    witness = await entity(scope, command.witness_id, "The witness", MORTALS)
    found = await scope.session.get(CaseWitnessRow, (row.id, witness.id))
    if found is None:
        found = CaseWitnessRow(case_id=row.id, witness_entity_id=witness.id, testimony=command.testimony, reliability=command.reliability)
        scope.session.add(found)
    found.testimony, found.reliability, found.locked = command.testimony, command.reliability, command.hold
    await scope.session.flush()
    return Effect(f"{witness.name} {command.testimony.value} the accused, with reliability {command.reliability}.", target_node_id=witness.id)


@player_action("witness:remove", ActionKind.EDIT_RECORD)
async def remove_witness(scope: PlayerScope, command: WitnessTarget) -> Effect:
    found = await scope.session.get(CaseWitnessRow, (command.case_id, command.witness_id))
    if found is None:
        raise NotFoundError("That witness gave no testimony in this case.")
    await scope.session.delete(found)
    await scope.session.flush()
    return Effect("The testimony was struck.", target_node_id=command.witness_id)
