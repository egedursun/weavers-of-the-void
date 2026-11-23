from typing import Annotated, Any

from pydantic import Field

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.constants.units import PERCENT
from aerona.db.tables.economy import CurrencyRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import living_entity
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.son.support import ensure_in_reach

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]
SHAKE_MAX = 30


class ShakeCoinInput(ToolInput):
    currency_id: int
    trust_change: int = Field(ge=-SHAKE_MAX, le=SHAKE_MAX)
    reason: Reason


async def shake_coin(call: SonCall, args: ShakeCoinInput) -> str:
    currency = await call.session.get(CurrencyRow, args.currency_id)
    issuer = await living_entity(call.session, currency.issuer_entity_id) if currency is not None else None
    if currency is None or issuer is None:
        fail(SonResult.MONEY_REFUSED, why="there is no such currency with a living issuer")
    await ensure_in_reach(call, issuer)
    if currency.held or held(issuer.id):
        fail(SonResult.MONEY_REFUSED, why="that money is held")
    if not args.trust_change:
        fail(SonResult.MONEY_REFUSED, why="a shake moves trust one way or the other")
    currency.trust = clamp_int(currency.trust + args.trust_change, 0, PERCENT)
    call.target(issuer.id)
    await call.record(
        "money.coin_shaken",
        roles={IncidentRole.SUBJECT: currency.item_entity_id},
        facts={"currency": currency.name, "change": args.trust_change, "trust": currency.trust},
    )
    return result(SonResult.COIN_SHAKEN, currency=currency.name, trust=currency.trust)


def specs() -> list[ToolSpec[SonCall, Any]]:
    return [ToolSpec(SonToolId.SHAKE_COIN, AgentKind.SON, ShakeCoinInput, ToolMeta(ActionKind.INFLUENCE, son_standard_action), shake_coin)]
