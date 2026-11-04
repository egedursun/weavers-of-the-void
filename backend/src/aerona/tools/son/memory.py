import re
from typing import Annotated, Any

from pydantic import Field

from aerona.constants.tool_inputs import PLAN_MAX, PLAN_MIN, REASON_MAX, REASON_MIN
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind, TurnCounter
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.engine.gods.dedication import may_anchor
from aerona.engine.primitives.holds import ANCHOR_KEY, is_held
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, no_cost
from aerona.tools.framework.validation import fail, require_canon
from aerona.tools.son import lines
from aerona.tools.son.support import require_essence


class WritePlanInput(ToolInput):
    plan: Annotated[str, Field(min_length=PLAN_MIN, max_length=PLAN_MAX)]


class ChooseAnchorInput(ToolInput):
    entity_id: int
    reason: Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


TOOL_NAMES = re.compile(rf"\b(?:{'|'.join(sorted((re.escape(tool.value) for tool in SonToolId), key=len, reverse=True))})\b")


RECORD_NUMBERS = re.compile(r"\(?#\d+\)?")


def clean_plan(text: str) -> str:
    return " ".join(TOOL_NAMES.sub("", RECORD_NUMBERS.sub("", text)).split())


async def write_plan(call: SonCall, args: WritePlanInput) -> str:
    call.son.plan = clean_plan(args.plan) or args.plan.strip()
    call.son.plan_epoch = call.epoch
    return result(SonResult.PLAN_WRITTEN)


async def choose_anchor(call: SonCall, args: ChooseAnchorInput) -> str:
    if await is_held(call.session, call.son.id, ANCHOR_KEY, call.epoch):
        fail(SonResult.ANCHOR_HELD)
    cap = call.rules.son_tools.anchor_per_epoch
    await call.within_limit(TurnCounter.ANCHOR_CHOSEN, cap, "son_tools.anchor_per_epoch", SonResult.ANCHOR_LIMIT)
    entity = await require_canon(call.session, args.entity_id)
    if not await may_anchor(call.session, call.son, entity):
        fail(SonResult.ANCHOR_NOT_OWN)
    cost = call.rules.costs.anchor
    require_essence(call, cost)
    call.spend_essence(cost)
    call.son.anchor_entity_id = entity.id
    call.target(entity.id)
    await call.bump(TurnCounter.ANCHOR_CHOSEN)
    await call.chronicle(ChronicleKind.EXISTENCE, lines.ANCHOR, entity_ids=[entity.id], son=call.son.name, entity=entity.name, reason=args.reason)
    return result(SonResult.ANCHOR_SET, name=entity.name)


def specs() -> list[ToolSpec[SonCall, Any]]:
    son = AgentKind.SON
    return [
        ToolSpec(SonToolId.WRITE_PLAN, son, WritePlanInput, ToolMeta(ActionKind.WRITE_PLAN, no_cost), write_plan),
        ToolSpec(
            SonToolId.CHOOSE_ANCHOR,
            son,
            ChooseAnchorInput,
            ToolMeta(ActionKind.CHANGE_ANCHOR, no_cost, essence_cost=lambda rules: rules.costs.anchor),
            choose_anchor,
        ),
    ]
