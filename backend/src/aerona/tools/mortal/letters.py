from typing import Any

from aerona.catalog.communication import CONTENT_LABELS, MEDIUM_LABELS
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.communication import DispatchContent, Medium
from aerona.engine.communication.post import send
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail, require_canon
from aerona.tools.mortal import lines

MORTAL_MEDIA = frozenset({Medium.ENVOY, Medium.LETTER, Medium.HERALD, Medium.BIRD, Medium.SIGNAL_FIRE})


class DispatchInput(ToolInput):
    recipient_id: int
    content: DispatchContent
    medium: Medium


async def send_dispatch(call: MortalCall, args: DispatchInput) -> str:
    recipient = await require_canon(call.session, args.recipient_id)
    if recipient.id == call.me.id:
        fail(MortalResult.DISPATCH_REFUSED, why="a message goes to someone else")
    if args.medium not in MORTAL_MEDIA:
        fail(MortalResult.DISPATCH_REFUSED, why="dreams and magic sendings are not yours to send")
    row = await send(call.tick, call.me.id, recipient.id, args.content, args.medium)
    if row is None:
        fail(MortalResult.DISPATCH_REFUSED, why="a god holds you against change")
    label = CONTENT_LABELS[args.content].lower()
    call.target(recipient.id)
    await call.chronicle(ChronicleKind.WORLD, lines.DISPATCH_SENT, entity_ids=[call.me.id, recipient.id], me=call.me.name, target=recipient.name, deed=label)
    return result(MortalResult.DISPATCH_SENT, deed=label, target=recipient.name, medium=MEDIUM_LABELS[args.medium].lower(), epoch=row.arrival_epoch)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    return [ToolSpec(MortalToolId.SEND_DISPATCH, AgentKind.MORTAL, DispatchInput, ToolMeta(ActionKind.INFLUENCE, mortal_standard_action), send_dispatch)]
