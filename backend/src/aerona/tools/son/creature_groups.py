from typing import Annotated, Any

from pydantic import Field

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.core.grammar import spoken
from aerona.db.tables.creature_groups import CreatureGroupRow
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.creature_groups import GroupAim
from aerona.domain.enums.modifier import IncidentRole
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.son.support import ensure_in_reach

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


class LeadCreaturesInput(ToolInput):
    group_id: int
    aim: GroupAim
    reason: Reason


async def lead_creatures(call: SonCall, args: LeadCreaturesInput) -> str:
    group = await call.session.get(CreatureGroupRow, args.group_id)
    region = await call.session.get(EntityRow, group.region_entity_id) if group is not None else None
    if group is None or region is None:
        fail(SonResult.CREATURES_REFUSED, why="there is no such group of creatures")
    await ensure_in_reach(call, region)
    if held(group.species_entity_id) or "aim" in group.locked:
        fail(SonResult.CREATURES_REFUSED, why="they are held unchanged")
    group.aim, group.aim_until_epoch = args.aim, call.tick.epoch + call.rules.creature_groups.aim_epochs
    call.target(group.species_entity_id)
    await call.record("beasts.group_led", roles={IncidentRole.SUBJECT: group.species_entity_id}, facts={"aim": args.aim})
    return result(SonResult.CREATURES_LED, aim=spoken(args.aim), until=group.aim_until_epoch)


def specs() -> list[ToolSpec[SonCall, Any]]:
    return [ToolSpec(SonToolId.LEAD_CREATURES, AgentKind.SON, LeadCreaturesInput, ToolMeta(ActionKind.INFLUENCE, son_standard_action), lead_creatures)]
