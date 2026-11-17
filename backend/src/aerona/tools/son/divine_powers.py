from typing import Annotated, Any

from pydantic import Field

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.db.tables.divine_powers import DivinePowerRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.divine.grammar import pay, wield
from aerona.engine.primitives.queries import living_entity
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.son.support import ensure_in_reach

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


class WieldInput(ToolInput):
    power_id: int
    target_id: int | None = None
    reason: Reason


async def wield_power(call: SonCall, args: WieldInput) -> str:
    row = await call.session.get(DivinePowerRow, args.power_id)
    if row is None or row.holder_node_id != call.son.id:
        fail(SonResult.POWER_REFUSED, why="that power is not yours")
    if row.last_used_epoch is not None and call.epoch - row.last_used_epoch < row.cooldown:
        fail(SonResult.POWER_REFUSED, why="that power is not ready again yet")
    target = await living_entity(call.session, args.target_id) if args.target_id is not None else None
    if args.target_id is not None:
        if target is None:
            fail(SonResult.POWER_REFUSED, why="there is no one there")
        await ensure_in_reach(call, target)
    if not await pay(call.tick, row):
        fail(SonResult.POWER_REFUSED, why="it costs more than you can give")
    touched = await wield(call.tick, row, args.target_id)
    if target is not None:
        call.target(target.id)
    await call.record(
        "tools.son.wield_power",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: [*([target.id] if target is not None else [])]},
        facts={"power": row.name, "reason": args.reason},
        kind=ChronicleKind.FATE,
    )
    return result(SonResult.POWER_WIELDED, power=row.name, touched=touched)


def specs() -> list[ToolSpec[SonCall, Any]]:
    return [ToolSpec(SonToolId.WIELD_POWER, AgentKind.SON, WieldInput, ToolMeta(ActionKind.INFLUENCE, son_standard_action), wield_power)]
