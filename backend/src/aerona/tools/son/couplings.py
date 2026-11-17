from typing import Annotated, Any

from pydantic import Field

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.couplings import SealKind, TeachingKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.couplings.deep import active_seal, seal_deep
from aerona.engine.couplings.teachers import lesson
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.son.support import ensure_in_reach

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]
TEACHERS = frozenset({EntityType.SPIRIT, EntityType.BEAST})


class SendTeacherInput(ToolInput):
    teacher_id: int
    learner_id: int
    kind: TeachingKind
    reason: Reason


class SealBreachInput(ToolInput):
    place_id: int
    reason: Reason


async def present(call: SonCall, entity_id: int) -> EntityRow | None:
    entity = await call.session.get(EntityRow, entity_id)
    return entity if entity is not None and entity.status is EntityStatus.CANON else None


async def send_teacher(call: SonCall, args: SendTeacherInput) -> str:
    teacher, learner = await present(call, args.teacher_id), await present(call, args.learner_id)
    if teacher is None or teacher.entity_type not in TEACHERS:
        fail(SonResult.TEACHER_REFUSED, why="only a living spirit or beast can teach this way")
    if learner is None or learner.entity_type not in COMMUNITY_TYPES:
        fail(SonResult.TEACHER_REFUSED, why="only a living community can be taught")
    if held(teacher.id, learner.id):
        fail(SonResult.TEACHER_REFUSED, why="a stronger hand holds them")
    await ensure_in_reach(call, learner)
    row = await lesson(call.tick, teacher, learner, kinds=(args.kind,))
    if row is None:
        fail(SonResult.TEACHER_REFUSED, why=f"{teacher.name} has nothing of that kind to teach {learner.name}, or is forbidden to")
    call.target(learner.id)
    await call.record(
        "tools.son.send_teacher",
        roles={IncidentRole.ACTOR: call.son.id},
        facts={"teacher_detail": str(teacher.name), "learner_detail": str(learner.name), "reason": args.reason},
        kind=ChronicleKind.DIVINE_SIGN,
    )
    return result(SonResult.TEACHER_SENT, teacher=teacher.name, learner=learner.name)


async def seal_breach(call: SonCall, args: SealBreachInput) -> str:
    place = await present(call, args.place_id)
    if place is None:
        fail(SonResult.BREACH_REFUSED, why="there is no such place")
    if held(place.id):
        fail(SonResult.BREACH_REFUSED, why="a stronger hand holds it")
    await ensure_in_reach(call, place)
    if await active_seal(call.session, place.id) is not None:
        fail(SonResult.BREACH_REFUSED, why="it is already sealed")
    row = await seal_deep(call.tick, place.id, SealKind.DIVINE, call.son.id)
    call.target(place.id)
    await call.record(
        "tools.son.seal_breach",
        roles={IncidentRole.ACTOR: call.son.id},
        facts={"place_detail": str(place.name), "reason": args.reason},
        kind=ChronicleKind.DIVINE_SIGN,
    )
    return result(SonResult.BREACH_SEALED, place=place.name, strength=row.strength)


def specs() -> list[ToolSpec[SonCall, Any]]:
    meta = ToolMeta(ActionKind.INFLUENCE, son_standard_action)
    return [
        ToolSpec(SonToolId.SEND_TEACHER, AgentKind.SON, SendTeacherInput, meta, send_teacher),
        ToolSpec(SonToolId.SEAL_BREACH, AgentKind.SON, SealBreachInput, meta, seal_breach),
    ]
