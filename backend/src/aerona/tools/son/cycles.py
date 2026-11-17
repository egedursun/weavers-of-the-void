from typing import Annotated, Any

from pydantic import Field
from sqlalchemy import select

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.constants.units import PERCENT
from aerona.core.errors import ValidationFailedError
from aerona.db.tables.cycles import DivineDebtRow, GiftRow, LongPlanRow
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.cycles import (
    AdoptionKind,
    ChallengeKind,
    GiftOccasion,
    GiftState,
    KinshipDescent,
    KinTermSystem,
    LongPlanKind,
    ReproductiveSystem,
    ResidenceRule,
)
from aerona.domain.enums.demography import Sex
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import FactUnit, StepAction
from aerona.domain.enums.unions import (
    KinMatch,
    PartnerScope,
    PluralSide,
    UnionArrangement,
    UnionDescent,
    UnionDissolution,
    UnionExchange,
    UnionForm,
    UnionPurpose,
    UnionResidence,
)
from aerona.engine.cycles import control
from aerona.engine.cycles.gifts import weigh_debt
from aerona.engine.primitives.queries import living_entity
from aerona.engine.recording.record import StepDraft
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.son.support import ensure_in_reach

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]
PLAN_STEPS = 100
NAME = 200
STOPS = 12


class AnswerOfferingsInput(ToolInput):
    community_id: int
    generous: bool = False
    reason: Reason


class BeginPlanInput(ToolInput):
    kind: LongPlanKind
    name: str = Field(min_length=1, max_length=NAME)
    target_id: int | None = None
    steps: int = Field(default=10, ge=1, le=PLAN_STEPS)
    secrecy: int = Field(default=50, ge=0, le=PERCENT)
    reason: Reason


class FurtherPlanInput(ToolInput):
    plan_id: int
    reason: Reason


class ShapeKinshipInput(ToolInput):
    people_id: int
    descent: KinshipDescent
    residence: ResidenceRule
    kin_terms: KinTermSystem
    adoption: AdoptionKind
    first_side: Sex
    reason: Reason


class ShapeUnionsInput(ToolInput):
    people_id: int
    form: UnionForm
    plural_side: PluralSide = PluralSide.EITHER
    purpose: UnionPurpose
    residence: UnionResidence
    descent: UnionDescent
    exchange: UnionExchange
    arrangement: UnionArrangement
    dissolution: UnionDissolution
    endogamy: PartnerScope
    exogamy: PartnerScope
    kin_match: KinMatch = KinMatch.NONE
    reason: Reason


class ShapeReproductionInput(ToolInput):
    people_id: int
    system: ReproductiveSystem
    reason: Reason


class TryRealmInput(ToolInput):
    polity_id: int
    kind: ChallengeKind
    severity: int = Field(ge=0, le=PERCENT)
    reason: Reason


class SetCircuitInput(ToolInput):
    name: str = Field(min_length=1, max_length=NAME)
    stop_ids: list[int] = Field(min_length=2, max_length=STOPS)
    reason: Reason


async def reached(call: SonCall, entity_id: int, kinds: frozenset[EntityType], refused: SonResult, why: str) -> EntityRow:
    entity = await living_entity(call.session, entity_id)
    if entity is None or entity.entity_type not in kinds:
        fail(refused, why=why)
    await ensure_in_reach(call, entity)
    if held(entity.id):
        fail(refused, why="a stronger hand holds it")
    return entity


async def answer_offerings(call: SonCall, args: AnswerOfferingsInput) -> str:
    row = await call.session.get(DivineDebtRow, (call.son.id, args.community_id))
    community = await living_entity(call.session, args.community_id)
    if row is None or community is None:
        fail(SonResult.OFFERINGS_REFUSED, why="that community has offered you nothing")
    await ensure_in_reach(call, community)
    if "answered" in row.locked:
        fail(SonResult.OFFERINGS_REFUSED, why="a stronger hand keeps that ledger")
    owed = max(0, row.offered - row.answered)
    row.answered += owed + (round(owed * call.tick.rules.reciprocity.outgive_pct / PERCENT) if args.generous else 0)
    row.last_answer_epoch = call.tick.epoch
    await weigh_debt(call.tick, row)
    gifts = await call.session.scalars(
        select(GiftRow).where(GiftRow.receiver_node_id == call.son.id, GiftRow.occasion == GiftOccasion.OFFERING, GiftRow.state == GiftState.OPEN)
    )
    steps = [StepDraft(StepAction.ANSWER, actor=call.son.id, target=community.id, amount=owed, unit=FactUnit.COUNT)]
    for gift in gifts:
        giver = await call.session.get(EntityRow, gift.giver_node_id)
        if giver is not None and community.id in {giver.id, giver.location_id} and "state" not in gift.locked:
            gift.state = GiftState.RETURNED
            gift.settled_epoch = call.tick.epoch
            steps.append(StepDraft(StepAction.RETURN_GIFT, actor=call.son.id, target=giver.id, record_table=GiftRow.__tablename__, record_key=str(gift.id)))
    call.target(community.id)
    await call.record(
        "tools.son.answer_offerings",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: community.id},
        facts={"reason": args.reason},
        kind=ChronicleKind.WORLD,
        steps=steps,
    )
    return result(SonResult.OFFERINGS_ANSWERED, name=community.name, owed=max(0, row.offered - row.answered))


async def begin_long_plan(call: SonCall, args: BeginPlanInput) -> str:
    if args.target_id is not None:
        target = await living_entity(call.session, args.target_id)
        if target is not None:
            await ensure_in_reach(call, target)
    try:
        plan = await control.new_plan(
            call.tick, call.son.id, args.kind, args.name, target_id=args.target_id, carrier_id=None, steps=args.steps, step_cost=0, secrecy=args.secrecy
        )
    except ValidationFailedError as error:
        fail(SonResult.PLAN_REFUSED, why=str(error).rstrip("."))
    await call.record(
        "tools.son.begin_long_plan", roles={IncidentRole.ACTOR: call.son.id}, facts={"plan": plan.name, "reason": args.reason}, kind=ChronicleKind.WORLD
    )
    return result(SonResult.PLAN_BEGUN, name=plan.name, id=plan.id, steps=plan.steps)


async def further_plan(call: SonCall, args: FurtherPlanInput) -> str:
    plan = await call.session.get(LongPlanRow, args.plan_id)
    if plan is None or plan.holder_node_id != call.son.id:
        fail(SonResult.PLAN_REFUSED, why="that is not one of your plans")
    if plan.finished_epoch is not None or "progress" in plan.locked:
        fail(SonResult.PLAN_REFUSED, why="that plan no longer moves")
    await control.advance_plan(call.tick, plan.id, call.tick.rules.long_plans.steps_per_epoch)
    await call.record(
        "tools.son.further_plan", roles={IncidentRole.ACTOR: call.son.id}, facts={"plan": plan.name, "reason": args.reason}, kind=ChronicleKind.WORLD
    )
    return result(SonResult.PLAN_FURTHERED, name=plan.name, progress=plan.progress, steps=plan.steps)


async def shape_unions(call: SonCall, args: ShapeUnionsInput) -> str:
    people = await reached(call, args.people_id, frozenset({EntityType.PEOPLE}), SonResult.UNIONS_REFUSED, "there is no such people")
    values = args.model_dump(exclude={"people_id", "reason"}, mode="json")
    row = await control.set_union(call.tick, people.id, values)
    call.target(people.id)
    await call.record(
        "tools.son.shape_unions",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: people.id},
        facts={"people": people.name, "reason": args.reason},
        kind=ChronicleKind.WORLD,
    )
    return result(SonResult.UNIONS_SHAPED, name=people.name, form=row.form.value, purpose=row.purpose.value, residence=row.residence.value)


async def shape_kinship(call: SonCall, args: ShapeKinshipInput) -> str:
    people = await reached(call, args.people_id, frozenset({EntityType.PEOPLE}), SonResult.KINSHIP_REFUSED, "there is no such people")
    values = {
        "descent": args.descent.value,
        "residence": args.residence.value,
        "kin_terms": args.kin_terms.value,
        "adoption": args.adoption.value,
        "first_side": args.first_side.value,
    }
    row = await control.set_kinship(call.tick, people.id, values)
    call.target(people.id)
    await call.record(
        "tools.son.shape_kinship",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: people.id},
        facts={"people": people.name, "reason": args.reason},
        kind=ChronicleKind.WORLD,
    )
    return result(
        SonResult.KINSHIP_SHAPED,
        name=people.name,
        descent=row.descent.value,
        residence=row.residence.value,
    )


async def shape_reproduction(call: SonCall, args: ShapeReproductionInput) -> str:
    people = await reached(call, args.people_id, frozenset({EntityType.PEOPLE}), SonResult.REPRODUCTION_REFUSED, "there is no such people")
    row = await control.set_reproduction(call.tick, people.id, {"system": args.system.value})
    call.target(people.id)
    await call.record(
        "tools.son.shape_reproduction",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: people.id},
        facts={"people": people.name, "reason": args.reason},
        kind=ChronicleKind.WORLD,
    )
    return result(SonResult.REPRODUCTION_SHAPED, name=people.name, system=row.system.value.replace("_", " "))


async def try_realm(call: SonCall, args: TryRealmInput) -> str:
    realm = await reached(call, args.polity_id, frozenset({EntityType.POLITY}), SonResult.REALM_TRY_REFUSED, "there is no such realm")
    challenge = await control.strike_challenge(call.tick, realm.id, args.kind, args.severity)
    call.target(realm.id)
    await call.record(
        "tools.son.try_realm",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: realm.id},
        facts={"realm": str(realm.name), "kind": args.kind, "reason": args.reason},
        kind=ChronicleKind.WORLD,
    )
    return result(SonResult.REALM_TRIED, name=realm.name, kind=args.kind.value, response=challenge.response.value)


async def set_circuit(call: SonCall, args: SetCircuitInput) -> str:
    kinds = frozenset({EntityType.SETTLEMENT, EntityType.PEOPLE, EntityType.POLITY})
    stops = [await reached(call, stop, kinds, SonResult.CIRCUIT_REFUSED, "each stop must be a living town, people or realm") for stop in args.stop_ids]
    try:
        circuit = await control.new_circuit(call.tick, args.name, [stop.id for stop in stops], None)
    except ValidationFailedError as error:
        fail(SonResult.CIRCUIT_REFUSED, why=str(error).rstrip("."))
    await call.record(
        "tools.son.set_circuit",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: [*[stop.id for stop in stops]]},
        facts={"circuit": circuit.name, "reason": args.reason},
        kind=ChronicleKind.WORLD,
    )
    return result(SonResult.CIRCUIT_SET, name=circuit.name, count=len(circuit.stops), id=circuit.id)


def specs() -> list[ToolSpec[SonCall, Any]]:
    son = AgentKind.SON
    meta = ToolMeta(ActionKind.INFLUENCE, son_standard_action)
    return [
        ToolSpec(SonToolId.ANSWER_OFFERINGS, son, AnswerOfferingsInput, meta, answer_offerings),
        ToolSpec(SonToolId.BEGIN_LONG_PLAN, son, BeginPlanInput, meta, begin_long_plan),
        ToolSpec(SonToolId.FURTHER_PLAN, son, FurtherPlanInput, meta, further_plan),
        ToolSpec(SonToolId.SHAPE_KINSHIP, son, ShapeKinshipInput, meta, shape_kinship),
        ToolSpec(SonToolId.SHAPE_UNIONS, son, ShapeUnionsInput, meta, shape_unions),
        ToolSpec(SonToolId.SHAPE_REPRODUCTION, son, ShapeReproductionInput, meta, shape_reproduction),
        ToolSpec(SonToolId.TRY_REALM, son, TryRealmInput, meta, try_realm),
        ToolSpec(SonToolId.SET_CIRCUIT, son, SetCircuitInput, meta, set_circuit),
    ]
