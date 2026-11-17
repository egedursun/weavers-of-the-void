from typing import Annotated, Any

from pydantic import Field

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.fortune import FortuneSourceKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.fortune.profiles import shift_fortune
from aerona.engine.primitives.queries import living_entity
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.son.support import ensure_in_reach

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


class FortuneInput(ToolInput):
    target_id: int
    reason: Reason


async def judge(call: SonCall, args: FortuneInput, sign: int) -> str:
    target = await living_entity(call.session, args.target_id)
    if target is None:
        fail(SonResult.FORTUNE_REFUSED, why="there is no one there")
    await ensure_in_reach(call, target)
    strength = call.rules.fortune.blessing_strength * sign
    kind = FortuneSourceKind.DIVINE_FAVOUR if sign > 0 else FortuneSourceKind.DIVINE_DISFAVOUR
    await shift_fortune(call.tick, target.id, strength, kind, call.son.id)
    call.target(target.id)
    await call.record(
        "tools.son.bless_fortune" if sign > 0 else "tools.son.curse_fortune",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.TARGET: target.id},
        facts={"reason": args.reason, "strength": abs(strength)},
        kind=ChronicleKind.FATE,
    )
    return result(SonResult.FORTUNE_BLESSED if sign > 0 else SonResult.FORTUNE_CURSED, name=target.name)


async def bless_fortune(call: SonCall, args: FortuneInput) -> str:
    return await judge(call, args, 1)


async def curse_fortune(call: SonCall, args: FortuneInput) -> str:
    return await judge(call, args, -1)


def specs() -> list[ToolSpec[SonCall, Any]]:
    meta = ToolMeta(ActionKind.INFLUENCE, son_standard_action)
    return [
        ToolSpec(SonToolId.BLESS_FORTUNE, AgentKind.SON, FortuneInput, meta, bless_fortune),
        ToolSpec(SonToolId.CURSE_FORTUNE, AgentKind.SON, FortuneInput, meta, curse_fortune),
    ]
