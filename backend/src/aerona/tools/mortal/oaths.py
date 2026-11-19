from typing import Any

from aerona.core.grammar import spoken
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind, TurnCounter
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.polity import OathKind
from aerona.engine.polity.oaths import swear
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, no_cost
from aerona.tools.framework.validation import fail
from aerona.tools.mortal.support import require_target


class SwearInput(ToolInput):
    kind: OathKind
    recipient_id: int | None = None
    words: str | None = None


async def swear_oath(call: MortalCall, args: SwearInput) -> str:
    tools = call.rules.mortal_tools
    await call.within_limit(TurnCounter.OATHS_SWORN, tools.swear_oath_per_epoch, "mortal_tools.swear_oath_per_epoch", MortalResult.OATH_LIMIT)
    if call.me.entity_type is not EntityType.MORTAL:
        fail(MortalResult.OATH_NOT_MORTAL)
    recipient = await require_target(call, args.recipient_id) if args.recipient_id is not None else None
    oath = await swear(call.tick, call.me, args.kind, recipient_id=recipient.id if recipient is not None else None, note_text=args.words)
    await call.bump(TurnCounter.OATHS_SWORN)
    call.target(oath.recipient_node_id or call.me.id)
    return result(MortalResult.OATH_SWORN, kind=spoken(args.kind), witnessed="before a god" if oath.witness_son_id else "before the people")


def specs() -> list[ToolSpec[MortalCall, Any]]:
    return [ToolSpec(MortalToolId.SWEAR_OATH, AgentKind.MORTAL, SwearInput, ToolMeta(ActionKind.SWEAR_OATH, no_cost), swear_oath)]
