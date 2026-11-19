from typing import Any

from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.youth import YouthGroupMemberRow, YouthGroupRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.youth import YouthMeasure, YouthPurpose
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.youth.groups import DELINQUENT, is_youth, members_of
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail

MEASURE_PURPOSES = {YouthMeasure.SERVICE: YouthPurpose.SERVICE, YouthMeasure.SPORT: YouthPurpose.SPORT, YouthMeasure.DISCIPLINE: YouthPurpose.DEFENCE}
TEN = 10


class LeadYouthInput(ToolInput):
    group_id: int
    purpose: YouthPurpose


class ReformYouthInput(ToolInput):
    group_id: int
    measure: YouthMeasure


async def group_here(call: MortalCall, group_id: int) -> YouthGroupRow:
    group = await call.session.get(YouthGroupRow, group_id)
    if group is None or group.settlement_entity_id != call.me.location_id:
        fail(MortalResult.YOUTH_REFUSED, why="there is no such youth group in your town")
    if held(group.settlement_entity_id):
        fail(MortalResult.YOUTH_REFUSED, why="a god holds this town as it is")
    return group


async def lead_youth(call: MortalCall, args: LeadYouthInput) -> str:
    group = await group_here(call, args.group_id)
    if not await is_youth(call.session, call.me):
        fail(MortalResult.YOUTH_REFUSED, why="only one in the years of youth leads a youth group")
    if "leader_node_id" in (group.locked or []) or "purpose" in (group.locked or []):
        fail(MortalResult.YOUTH_REFUSED, why="a god holds who leads this group and what it is for")
    if await call.session.get(YouthGroupMemberRow, (group.id, call.me.id)) is None:
        call.session.add(YouthGroupMemberRow(group_id=group.id, member_node_id=call.me.id, joined_epoch=call.epoch, locked=[]))
    group.leader_node_id, group.purpose = call.me.id, args.purpose
    call.target(group.settlement_entity_id)
    await call.record(
        "youth.led", roles={IncidentRole.ACTOR: call.me.id}, facts={"group": group.name, "purpose": args.purpose}, place=group.settlement_entity_id
    )
    return result(MortalResult.YOUTH_LED, group=group.name, purpose=spoken(args.purpose))


async def reform_youth(call: MortalCall, args: ReformYouthInput) -> str:
    group = await group_here(call, args.group_id)
    if await is_youth(call.session, call.me):
        fail(MortalResult.YOUTH_REFUSED, why="a youth cannot reform its own kind; only an elder of the town can")
    if "purpose" in (group.locked or []):
        fail(MortalResult.YOUTH_REFUSED, why="a god holds what this group is for")
    purpose = MEASURE_PURPOSES.get(args.measure)
    if purpose is not None and (args.measure is not YouthMeasure.DISCIPLINE or group.purpose in DELINQUENT):
        group.purpose = purpose
    if args.measure is YouthMeasure.DISCIPLINE and "standing" not in (group.locked or []):
        group.standing = clamp_int(group.standing + TEN, 0, PERCENT)
    if args.measure is YouthMeasure.SCHOOLING:
        for member in await members_of(call.session, group.id):
            profile = await call.session.get(MortalProfileRow, member.member_node_id)
            if profile is not None and not held(member.member_node_id) and "education" not in (profile.locked or []):
                profile.education = clamp_int(profile.education + call.rules.youth.member_effect, 0, PERCENT)
        if group.purpose in DELINQUENT:
            group.purpose = YouthPurpose.SPORT
    call.target(group.settlement_entity_id)
    await call.record(
        "youth.reformed", roles={IncidentRole.ACTOR: call.me.id}, facts={"group": group.name, "measure": args.measure}, place=group.settlement_entity_id
    )
    return result(MortalResult.YOUTH_REFORMED, group=group.name, measure=spoken(args.measure), purpose=spoken(group.purpose))


def specs() -> list[ToolSpec[MortalCall, Any]]:
    return [
        ToolSpec(MortalToolId.LEAD_YOUTH, AgentKind.MORTAL, LeadYouthInput, ToolMeta(ActionKind.INFLUENCE, mortal_standard_action), lead_youth),
        ToolSpec(MortalToolId.REFORM_YOUTH, AgentKind.MORTAL, ReformYouthInput, ToolMeta(ActionKind.INFLUENCE, mortal_standard_action), reform_youth),
    ]
