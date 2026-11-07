from typing import Any

from sqlalchemy import select

from aerona.catalog.intrigue import HOOK_DEMAND_LABELS, SCHEMES
from aerona.db.tables.intrigue import SchemeRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.intrigue import HookDemand, PlotKind
from aerona.engine.intrigue.leverage import press
from aerona.engine.intrigue.schemes import OPEN, begin_scheme
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail, require_canon
from aerona.tools.mortal import lines


class PlotInput(ToolInput):
    kind: PlotKind
    target_id: int


class PressInput(ToolInput):
    target_id: int
    demand: HookDemand


async def plot_scheme(call: MortalCall, args: PlotInput) -> str:
    target = await require_canon(call.session, args.target_id)
    if target.id == call.me.id:
        fail(MortalResult.SCHEME_REFUSED, why="you cannot plot against yourself")
    running = await call.session.scalar(select(SchemeRow.id).where(SchemeRow.owner_node_id == call.me.id, SchemeRow.phase.in_(list(OPEN))).limit(1))
    if running is not None:
        fail(MortalResult.SCHEME_REFUSED, why="you already have a scheme under way")
    row = await begin_scheme(call.tick, call.me, args.kind, target)
    if row is None:
        fail(MortalResult.SCHEME_REFUSED, why="a god holds you or your target against change")
    label = SCHEMES[args.kind].label.lower()
    call.target(target.id)
    await call.chronicle(ChronicleKind.WORLD, lines.SCHEME_BEGUN, entity_ids=[call.me.id], me=call.me.name, scheme=label)
    return result(MortalResult.SCHEME_BEGUN, scheme=label, target=target.name, difficulty=SCHEMES[args.kind].difficulty)


async def press_leverage(call: MortalCall, args: PressInput) -> str:
    target = await require_canon(call.session, args.target_id)
    if target.id == call.me.id:
        fail(MortalResult.LEVERAGE_FAILED, why="you hold nothing over yourself")
    done = await press(call.tick, call.me.id, target.id, args.demand)
    if done is None:
        fail(MortalResult.LEVERAGE_FAILED, why=f"you hold no hook or favour that moved {target.name}, or they could not do it")
    call.target(target.id)
    await call.chronicle(ChronicleKind.WORLD, lines.LEVERAGE_PRESSED, entity_ids=[call.me.id, target.id], me=call.me.name, target=target.name, deed=done)
    return result(MortalResult.LEVERAGE_PRESSED, target=target.name, demand=HOOK_DEMAND_LABELS[args.demand].lower(), deed=done)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    return [
        ToolSpec(MortalToolId.PLOT_SCHEME, AgentKind.MORTAL, PlotInput, ToolMeta(ActionKind.INFLUENCE, mortal_standard_action), plot_scheme),
        ToolSpec(MortalToolId.PRESS_LEVERAGE, AgentKind.MORTAL, PressInput, ToolMeta(ActionKind.INFLUENCE, mortal_standard_action), press_leverage),
    ]
