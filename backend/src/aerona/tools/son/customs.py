from typing import Annotated, Any

from pydantic import Field
from sqlalchemy import select

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.core.grammar import spoken
from aerona.db.tables.customs import RevivalRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.customs import MemberRight, Membership, RevivalAim, RevivalGoal
from aerona.domain.enums.entity import EntityType
from aerona.engine.customs import control
from aerona.engine.primitives.queries import living_entity
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.son import lines
from aerona.tools.son.support import ensure_in_reach

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]
AIMS = {
    RevivalGoal.REVIVE_LANGUAGE: RevivalAim.RESTORE,
    RevivalGoal.RESTORE_GOD: RevivalAim.RESTORE,
    RevivalGoal.EXPEL_FOREIGNERS: RevivalAim.RESTORE,
    RevivalGoal.ADOPT_WAYS: RevivalAim.ADOPT,
}


class StirRevivalInput(ToolInput):
    people_id: int
    goal: RevivalGoal
    reason: Reason


class ProclaimRightInput(ToolInput):
    realm_id: int
    category: Membership
    right: MemberRight
    granted: bool = True
    reason: Reason


async def stir_revival(call: SonCall, args: StirRevivalInput) -> str:
    people = await living_entity(call.session, args.people_id)
    if people is None or people.entity_type is not EntityType.PEOPLE:
        fail(SonResult.REVIVAL_REFUSED, why="there is no such people")
    await ensure_in_reach(call, people)
    if held(people.id):
        fail(SonResult.REVIVAL_REFUSED, why="a stronger hand holds it")
    if await call.session.scalar(select(RevivalRow.id).where(RevivalRow.people_entity_id == people.id, RevivalRow.ended_epoch.is_(None)).limit(1)) is not None:
        fail(SonResult.REVIVAL_REFUSED, why="a movement already stirs among them")
    await control.set_record(
        call.tick, "revival", {}, {"people_entity_id": people.id, "aim": AIMS[args.goal], "goal": args.goal, "started_epoch": call.tick.epoch}
    )
    call.target(people.id)
    told = args.goal.value.replace("_", " ")
    await call.chronicle(
        ChronicleKind.CULTURE, lines.STIR_REVIVAL, entity_ids=[people.id], son=call.son.name, people=people.name, goal=told, reason=args.reason
    )
    return result(SonResult.REVIVAL_STIRRED, people=people.name, goal=told)


async def proclaim_right(call: SonCall, args: ProclaimRightInput) -> str:
    realm = await living_entity(call.session, args.realm_id)
    if realm is None or realm.entity_type is not EntityType.POLITY:
        fail(SonResult.RIGHT_REFUSED, why="there is no such realm")
    await ensure_in_reach(call, realm)
    if held(realm.id):
        fail(SonResult.RIGHT_REFUSED, why="a stronger hand holds it")
    await control.grant_right(call.tick, realm.id, args.category, args.right, granted=args.granted)
    call.target(realm.id)
    told = f"{spoken(args.right)} for {spoken(args.category)}s"
    await call.chronicle(
        ChronicleKind.CIVILIZATION, lines.PROCLAIM_RIGHT, entity_ids=[realm.id], son=call.son.name, realm=realm.name, right=told, reason=args.reason
    )
    return result(SonResult.RIGHT_PROCLAIMED, realm=realm.name, right=told, granted=args.granted)


def specs() -> list[ToolSpec[SonCall, Any]]:
    son = AgentKind.SON
    meta = ToolMeta(ActionKind.INFLUENCE, son_standard_action)
    return [
        ToolSpec(SonToolId.STIR_REVIVAL, son, StirRevivalInput, meta, stir_revival),
        ToolSpec(SonToolId.PROCLAIM_RIGHT, son, ProclaimRightInput, meta, proclaim_right),
    ]
