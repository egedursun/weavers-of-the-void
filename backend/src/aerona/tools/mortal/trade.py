from typing import Any

from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import COMMUNITY_TYPES
from aerona.domain.enums.mind import MemoryKind
from aerona.engine.services.community_relations import change_relation
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.mortal import lines
from aerona.tools.mortal.inputs import TradeInput
from aerona.tools.mortal.support import enemies, fail_with_candidates, is_community, near, require_target

TRADE_EVENT = "trade"


async def establish_trade(call: MortalCall, args: TradeInput) -> str:
    target = await require_target(call, args.target_id)
    if target.id == call.me.id or not is_community(target):
        await fail_with_candidates(call, MortalResult.INVALID_PARTNER, COMMUNITY_TYPES)
    if not await near(call, target):
        await fail_with_candidates(call, MortalResult.TOO_FAR_TO_TRADE, COMMUNITY_TYPES)
    if await enemies(call, call.me.id, target.id):
        fail(MortalResult.NO_TRADE_WITH_ENEMY)
    bonds = BondRepository(call.session)
    if await bonds.exists_between(call.me.id, target.id, BondKind.TRADES_WITH):
        fail(MortalResult.ALREADY_TRADING)
    await bonds.connect(BondDraft(call.me.id, target.id, BondKind.TRADES_WITH, call.epoch, args.goods))
    await change_relation(call.tick, call.me.id, target.id, call.rules.mortal_tools.trade_relation, MemoryKind.TRADED_WITH, note=TRADE_EVENT)
    call.target(target.id)
    await call.chronicle(ChronicleKind.TRADE, lines.TRADE, entity_ids=[call.me.id, target.id], me=call.me.name, target=target.name, goods=args.goods)
    return result(MortalResult.TRADE_BEGUN, name=target.name)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    return [ToolSpec(MortalToolId.ESTABLISH_TRADE, AgentKind.MORTAL, TradeInput, ToolMeta(ActionKind.ESTABLISH_TRADE, mortal_standard_action), establish_trade)]
