from typing import Annotated, Any

from pydantic import Field

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.core.grammar import spoken
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.competition import EntryBarrier, PriceWarOutcome
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.competition.cartels import break_cartel, cartel_over
from aerona.engine.competition.law import split_holder
from aerona.engine.competition.structure import structure_of
from aerona.engine.competition.wars import close_war, war_over
from aerona.engine.primitives.queries import living_entity
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.son.support import ensure_in_reach

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


class BreakMarketInput(ToolInput):
    market_id: int
    goods_kind: CommodityKind
    reason: Reason


async def break_market(call: SonCall, args: BreakMarketInput) -> str:
    market = await living_entity(call.session, args.market_id)
    structure = await structure_of(call.tick, args.market_id, args.goods_kind) if market is not None else None
    if market is None or structure is None:
        fail(SonResult.MARKET_REFUSED, why=f"no one is counted as selling {spoken(args.goods_kind)} there")
    await ensure_in_reach(call, market)
    if held(market.id) or "barriers" in (structure.locked or []):
        fail(SonResult.MARKET_REFUSED, why="that market is held")
    undone: list[str] = []
    for barrier in sorted(structure.barriers or {}):
        await call.record(
            "market.barrier_fell",
            roles={IncidentRole.PLACE: market.id},
            facts={"barrier": EntryBarrier(barrier), "commodity": args.goods_kind},
            place=market.id,
        )
    if structure.barriers:
        undone.append("its barriers fell")
    structure.barriers = {}
    cartel = await cartel_over(call.tick, market.id, args.goods_kind)
    if cartel is not None:
        await break_cartel(call.tick, cartel, args.reason)
        undone.append("its compact broke")
    war = await war_over(call.tick, market.id, args.goods_kind)
    if war is not None:
        await close_war(call.tick, war, PriceWarOutcome.CALLED_OFF)
        undone.append("its price war ended")
    if await split_holder(call.tick, structure) is not None:
        undone.append("its single seller was split")
    if not undone:
        fail(SonResult.MARKET_REFUSED, why="nothing closes that market to newcomers")
    call.target(market.id)
    return result(SonResult.MARKET_BROKEN, market=market.name, commodity=spoken(args.goods_kind), undone="; ".join(undone))


def specs() -> list[ToolSpec[SonCall, Any]]:
    return [ToolSpec(SonToolId.BREAK_MARKET, AgentKind.SON, BreakMarketInput, ToolMeta(ActionKind.INFLUENCE, son_standard_action), break_market)]
