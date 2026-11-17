from typing import Annotated, Any

from pydantic import Field

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.justice import CrimeCaseRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.justice import CaseStage, Verdict
from aerona.domain.enums.law_depth import LegalSystem
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import StepAction
from aerona.engine.law.systems import system_for_case
from aerona.engine.mythic.divine_spies import read_dreams as dream_secrets
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


class AnswerOracleInput(ToolInput):
    case_id: int
    verdict: Verdict
    reason: Reason


class ReadDreamsInput(ToolInput):
    mortal_id: int
    reason: Reason


async def answer_oracle(call: SonCall, args: AnswerOracleInput) -> str:
    case = await call.session.get(CrimeCaseRow, args.case_id)
    town = await call.session.get(EntityRow, case.settlement_entity_id) if case is not None and case.settlement_entity_id is not None else None
    if case is None or town is None or case.stage is not CaseStage.TRIAL:
        fail(SonResult.ORACLE_REFUSED, why="no such case waits for judgement")
    if await system_for_case(call.session, case) is not LegalSystem.ORACLE:
        fail(SonResult.ORACLE_REFUSED, why="that realm does not ask the gods for its verdicts")
    if args.verdict not in (Verdict.GUILTY, Verdict.ACQUITTED):
        fail(SonResult.ORACLE_REFUSED, why="an oracle can only name the accused guilty or innocent")
    await ensure_in_reach(call, town)
    case.oracle_answer = args.verdict
    call.target(town.id)
    await call.record(
        "tools.son.answer_oracle",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.PLACE: town.id},
        facts={"reason": args.reason},
        place=town.id,
        kind=ChronicleKind.WORLD,
        steps=(StepDraft(StepAction.ANSWER, actor=call.son.id, target=town.id, record_table=CrimeCaseRow.__tablename__, record_key=str(case.id)),),
    )
    return result(SonResult.ORACLE_ANSWERED, name=town.name, verdict=args.verdict.value)


async def read_dreams(call: SonCall, args: ReadDreamsInput) -> str:
    mortal = await living_entity(call.session, args.mortal_id)
    if mortal is None or mortal.entity_type is not EntityType.MORTAL:
        fail(SonResult.DREAMS_REFUSED, why="there is no such living mortal")
    await ensure_in_reach(call, mortal)
    learned = await dream_secrets(call.tick, call.son.id, mortal)
    if learned is None:
        fail(SonResult.DREAMS_REFUSED, why="wards or a stronger god's presence turned you aside")
    call.target(mortal.id)
    await call.record(
        "tools.son.read_dreams",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.TARGET: mortal.id},
        facts={"reason": args.reason},
        kind=ChronicleKind.WORLD,
    )
    return result(SonResult.DREAMS_READ, name=mortal.name, count=len(learned))


def specs() -> list[ToolSpec[SonCall, Any]]:
    son = AgentKind.SON
    meta = ToolMeta(ActionKind.INFLUENCE, son_standard_action)
    return [
        ToolSpec(SonToolId.ANSWER_ORACLE, son, AnswerOracleInput, meta, answer_oracle),
        ToolSpec(SonToolId.READ_DREAMS, son, ReadDreamsInput, meta, read_dreams),
    ]
