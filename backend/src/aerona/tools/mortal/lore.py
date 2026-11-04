from typing import Any

from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.entity import EntityType
from aerona.prompts import MortalToolId
from aerona.tools.framework import lore_tools
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.lore_inputs import CastRiteInput, CommissionInput, DesignRiteInput, FoundSchoolInput, LoreToolResult
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail


async def commission_artwork(call: MortalCall, args: CommissionInput) -> str:
    return await lore_tools.commission(call.tick, call.me, args)


async def design_rite(call: MortalCall, args: DesignRiteInput) -> str:
    return await lore_tools.design(call.tick, call.me, args)


async def cast_rite(call: MortalCall, args: CastRiteInput) -> str:
    call.target(args.rite_id)
    return await lore_tools.cast(call.tick, call.me, args.rite_id, args.target_id)


async def found_school(call: MortalCall, args: FoundSchoolInput) -> str:
    if call.me.entity_type is not EntityType.MORTAL:
        fail(LoreToolResult.NO_FOUNDER)
    return await lore_tools.found(call.tick, call.me, args)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    mortal = AgentKind.MORTAL
    standard = mortal_standard_action
    return [
        ToolSpec(MortalToolId.COMMISSION_ARTWORK, mortal, CommissionInput, ToolMeta(ActionKind.CREATE_CULTURE, standard), commission_artwork),
        ToolSpec(MortalToolId.DESIGN_RITE, mortal, DesignRiteInput, ToolMeta(ActionKind.DEVELOP_KNOWLEDGE, standard), design_rite),
        ToolSpec(MortalToolId.CAST_RITE, mortal, CastRiteInput, ToolMeta(ActionKind.INFLUENCE, standard), cast_rite),
        ToolSpec(MortalToolId.FOUND_SCHOOL, mortal, FoundSchoolInput, ToolMeta(ActionKind.CREATE_CULTURE, standard), found_school),
    ]
