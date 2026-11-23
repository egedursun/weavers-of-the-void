from typing import Annotated, Any

from pydantic import Field

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.core.total import total
from aerona.db.tables.securities import MOOD_MAX, MOOD_MIN, StockExchangeRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.securities import MoodDirection
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
DIRECTION_SIGN = total(MoodDirection, {MoodDirection.UP: 1, MoodDirection.DOWN: -1})


class StirMarketMoodInput(ToolInput):
    exchange_id: int
    direction: MoodDirection
    reason: Reason


async def stir_market_mood(call: SonCall, args: StirMarketMoodInput) -> str:
    exchange = await call.session.get(StockExchangeRow, args.exchange_id)
    town = await living_entity(call.session, exchange.settlement_entity_id) if exchange is not None else None
    if exchange is None or town is None:
        fail(SonResult.SECURITIES_REFUSED, why="there is no such exchange in a living town")
    await ensure_in_reach(call, town)
    if held(town.id) or "mood" in (exchange.locked or []):
        fail(SonResult.SECURITIES_REFUSED, why="that exchange is held")
    step = call.tick.rules.securities.stir_mood
    exchange.mood = clamp_int(exchange.mood + step * DIRECTION_SIGN[args.direction], MOOD_MIN, MOOD_MAX)
    call.target(town.id)
    await call.record(
        "securities.mood_stirred",
        roles={IncidentRole.PLACE: town.id},
        facts={"exchange": exchange.name, "direction": args.direction, "mood": exchange.mood},
        place=town.id,
    )
    return result(SonResult.MARKET_MOOD_STIRRED, exchange=exchange.name, mood=exchange.mood)


def specs() -> list[ToolSpec[SonCall, Any]]:
    return [ToolSpec(SonToolId.STIR_MARKET_MOOD, AgentKind.SON, StirMarketMoodInput, ToolMeta(ActionKind.INFLUENCE, son_standard_action), stir_market_mood)]
