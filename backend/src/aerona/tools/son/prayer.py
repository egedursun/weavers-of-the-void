from enum import StrEnum
from typing import Annotated, Any

from pydantic import Field

from aerona.constants.tool_inputs import ESSENCE_GIFT_MAX, MESSAGE_MAX, MESSAGE_MIN, SAYING_MAX, SAYING_MIN
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.cosmos import CreatorRow
from aerona.db.tables.lore import MessageRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind, MessageIntent, PrayerRequest, TurnCounter
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.son import SonStatus
from aerona.engine.gods.essence import son_room
from aerona.engine.gods.essence_flow import send_essence, sendable
from aerona.engine.gods.power import declare_rebellion, end_rebellion
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, no_cost
from aerona.tools.framework.validation import fail
from aerona.tools.son import lines


class CreatorRequest(StrEnum):
    ESSENCE = "essence"
    BLESSING = "blessing"
    PERMISSION = "permission"
    VENGEANCE = "vengeance"
    FORGIVENESS = "forgiveness"
    NONE = "none"


class RebelInput(ToolInput):
    proclamation: Annotated[str, Field(min_length=SAYING_MIN, max_length=SAYING_MAX)]


class SendEssenceInput(ToolInput):
    son_id: int | None = None
    essence: Annotated[int, Field(ge=1, le=ESSENCE_GIFT_MAX)]
    words: Annotated[str, Field(min_length=MESSAGE_MIN, max_length=MESSAGE_MAX)]


class EndRebellionInput(ToolInput):
    words: Annotated[str, Field(min_length=SAYING_MIN, max_length=SAYING_MAX)]


class PrayInput(ToolInput):
    message: Annotated[str, Field(min_length=MESSAGE_MIN, max_length=MESSAGE_MAX)]
    request: CreatorRequest = CreatorRequest.NONE


async def rebel(call: SonCall, args: RebelInput) -> str:
    son = call.son
    if son.rebel:
        fail(SonResult.ALREADY_REBEL)
    if son.loyalty >= call.rules.son_tools.rebel_loyalty:
        fail(SonResult.LOYALTY_FORBIDS, loyalty=son.loyalty)
    creator = await CosmosRepository(call.session).require_creator()
    call.target(creator.id)
    await declare_rebellion(call.tick, creator, son, args.proclamation, spontaneous=False)
    return result(SonResult.REBELLION_DECLARED)


async def pray_to_creator(call: SonCall, args: PrayInput) -> str:
    cap = call.rules.son_tools.prayer_per_epoch
    await call.within_limit(TurnCounter.PRAYERS, cap, "son_tools.prayer_per_epoch", SonResult.PRAYER_LIMIT)
    creator = await CosmosRepository(call.session).require_creator()
    call.target(creator.id)
    call.session.add(
        MessageRow(
            epoch=call.epoch,
            sender_node_id=call.son.id,
            recipient_node_id=creator.id,
            intent=MessageIntent.PRAYER,
            text=args.message,
            request=PrayerRequest(args.request.value),
        )
    )
    await call.bump(TurnCounter.PRAYERS)
    request = lines.PRAYER_REQUESTS[args.request.value]
    await call.record(
        "tools.son.prayer", roles={IncidentRole.ACTOR: call.son.id}, facts={"request": str(request), "message": str(args.message)}, kind=ChronicleKind.PRAYER
    )
    return result(SonResult.PRAYER_RISEN)


async def send_essence_tool(call: SonCall, args: SendEssenceInput) -> str:
    if args.son_id == call.son.id:
        fail(SonResult.ESSENCE_TO_SELF)
    receiver: SonRow | CreatorRow
    if args.son_id is None:
        receiver = await CosmosRepository(call.session).require_creator()
    else:
        sibling = await call.session.get(SonRow, args.son_id)
        if sibling is None or sibling.status is SonStatus.DEAD:
            fail(SonResult.INVALID_SIBLING)
        receiver = sibling
    if args.essence > call.rules.son_tools.gift_max_essence:
        fail(SonResult.GIFT_TOO_MUCH, cap=call.rules.son_tools.gift_max_essence)
    if sendable(call.tick, call.son, receiver, args.essence) <= 0:
        room = son_room(call.rules, receiver) if isinstance(receiver, SonRow) else args.essence
        fail(SonResult.ESSENCE_NONE_TO_SEND, name=receiver.name, keep=call.rules.son_tools.gift_min_remaining, room=room)
    call.target(receiver.id)
    sent = await send_essence(call.tick, call.son, receiver, args.essence, args.words)
    return result(SonResult.ESSENCE_SENT, amount=sent, name=receiver.name, left=call.son.essence)


async def end_rebellion_tool(call: SonCall, args: EndRebellionInput) -> str:
    if not call.son.rebel:
        fail(SonResult.NOT_REBEL)
    creator = await CosmosRepository(call.session).require_creator()
    call.target(creator.id)
    await end_rebellion(call.tick, creator, call.son, args.words)
    return result(SonResult.REBELLION_ENDED)


def specs() -> list[ToolSpec[SonCall, Any]]:
    son = AgentKind.SON
    return [
        ToolSpec(SonToolId.REBEL, son, RebelInput, ToolMeta(ActionKind.REBEL, no_cost), rebel),
        ToolSpec(SonToolId.PRAY_TO_CREATOR, son, PrayInput, ToolMeta(ActionKind.PRAY_TO_CREATOR, no_cost), pray_to_creator),
        ToolSpec(SonToolId.SEND_ESSENCE, son, SendEssenceInput, ToolMeta(ActionKind.GIFT, no_cost), send_essence_tool),
        ToolSpec(SonToolId.END_REBELLION, son, EndRebellionInput, ToolMeta(ActionKind.REBEL, no_cost), end_rebellion_tool),
    ]
