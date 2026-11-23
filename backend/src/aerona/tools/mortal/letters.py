from typing import Any

from aerona.catalog.communication import CONTENT_LABELS, MEDIUM_LABELS, MORTAL_MEDIA
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.communication import DispatchContent, Medium
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import StepAction, StepOutcome
from aerona.engine.communication.dispatches import ARMY, REGION
from aerona.engine.communication.post import send
from aerona.engine.recording.record import StepDraft
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail, require_canon


class DispatchInput(ToolInput):
    recipient_id: int
    content: DispatchContent
    medium: Medium
    army_id: int | None = None
    region_id: int | None = None


async def send_dispatch(call: MortalCall, args: DispatchInput) -> str:
    recipient = await require_canon(call.session, args.recipient_id)
    if recipient.id == call.me.id:
        fail(MortalResult.DISPATCH_REFUSED, why="a message goes to someone else")
    if args.medium not in MORTAL_MEDIA:
        fail(MortalResult.DISPATCH_REFUSED, why="dreams and magic sendings are not yours to send")
    orders = {ARMY: args.army_id, REGION: args.region_id} if args.army_id is not None and args.region_id is not None else None
    row = await send(call.tick, call.me.id, recipient.id, args.content, args.medium, payload=orders)
    if row is None:
        fail(MortalResult.DISPATCH_REFUSED, why="a god holds you against change")
    label = CONTENT_LABELS[args.content].lower()
    call.target(recipient.id)
    await call.record(
        "tools.mortal.dispatch_sent",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.RECEIVER: recipient.id},
        facts={"content": args.content, "medium": args.medium, "arrival_epoch": row.arrival_epoch},
        steps=(StepDraft(StepAction.WRITE, actor=call.me.id, target=recipient.id, instrument_key=args.medium.value, outcome=StepOutcome.SUCCESS),),
    )
    return result(MortalResult.DISPATCH_SENT, deed=label, target=recipient.name, medium=MEDIUM_LABELS[args.medium].lower(), epoch=row.arrival_epoch)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    return [ToolSpec(MortalToolId.SEND_DISPATCH, AgentKind.MORTAL, DispatchInput, ToolMeta(ActionKind.INFLUENCE, mortal_standard_action), send_dispatch)]
