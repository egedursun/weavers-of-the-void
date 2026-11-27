from enum import StrEnum
from typing import Annotated, Any

from pydantic import Field

from aerona.catalog.gates import Gate
from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind, TurnCounter
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.node import ActorKind
from aerona.engine.gods.devotion import SchemeKind, hinder_return, resurrection_state, scheme_cost, sibling_scheme
from aerona.engine.gods.essence import endow
from aerona.engine.gods.mortality import Killer, attempt_kill, failed_kill_refund, kill_cost
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, gate, son_standard_action
from aerona.tools.framework.validation import fail, require_canon, require_type
from aerona.tools.son.support import ensure_in_reach, require_sibling

PLOT_RULE = "death.sibling_intrigues_per_epoch"


class PlotPath(StrEnum):
    RITE = "rite"
    DESCENT = "descent"
    BARGAIN = "bargain"


class TakeLifeInput(ToolInput):
    entity_id: int
    how: Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


class ResurrectInput(ToolInput):
    son_id: int
    path: PlotPath


class ScatterInput(ToolInput):
    son_id: int


async def take_life(call: SonCall, args: TakeLifeInput) -> str:
    death = call.rules.death
    await call.within_limit(TurnCounter.TAKE_LIFE, death.take_life_per_epoch, "death.take_life_per_epoch", SonResult.TAKE_LIFE_LIMIT)
    victim = require_type(await require_canon(call.session, args.entity_id), {EntityType.MORTAL}, SonResult.ONLY_NAMED_MORTAL)
    await ensure_in_reach(call, victim)
    cost = await kill_cost(call.session, call.rules, victim)
    if call.son.essence < cost:
        fail(SonResult.LIFE_TOO_COSTLY, name=victim.name, cost=cost, have=call.son.essence)
    call.spend_essence(cost)
    await call.bump(TurnCounter.TAKE_LIFE)
    call.target(victim.id)
    creator = await CosmosRepository(call.session).require_creator()
    killer = Killer(ActorKind.SON, call.son.name, call.son.id, call.son.might)
    outcome = await attempt_kill(call.tick, victim, killer, creator.name, how=args.how)
    refund = 0 if outcome.success else failed_kill_refund(call.rules, cost)
    if refund > 0:
        endow(call.rules, call.son, refund)
        call.log.essence_spent -= refund
    return result(SonResult.TAKE_LIFE_DONE, text=outcome.text, chance=outcome.percent, cost=cost, refund=refund)


async def _dead_sibling(call: SonCall, son_id: int) -> SonRow:
    await call.within_limit(TurnCounter.INTRIGUE, call.rules.death.sibling_intrigues_per_epoch, PLOT_RULE, SonResult.PLOT_LIMIT)
    return await require_sibling(call, son_id)


async def resurrect_sibling(call: SonCall, args: ResurrectInput) -> str:
    dead = await _dead_sibling(call, args.son_id)
    kind = SchemeKind(args.path.value)
    cost = scheme_cost(call.rules, kind)
    call.target(dead.id)
    outcome = await sibling_scheme(call.tick, call.son, dead, kind)
    call.log.essence_spent += cost
    await call.bump(TurnCounter.INTRIGUE)
    state = await resurrection_state(call.session, call.rules, dead, call.epoch)
    devotion = state.devotion if state is not None and outcome.contribution else None
    wait = state.remaining if state is not None else 0
    return result(SonResult.SCHEME_DONE, text=outcome.text, devotion=devotion, needed=call.rules.death.resurrection_devotion_required, wait=wait)


async def scatter(call: SonCall, args: ScatterInput) -> str:
    dead = await _dead_sibling(call, args.son_id)
    call.target(dead.id)
    outcome = await hinder_return(call.tick, call.son, dead)
    call.log.essence_spent += call.rules.death.hinder_return_cost
    await call.bump(TurnCounter.INTRIGUE)
    return result(SonResult.RETURN_HINDERED, text=outcome.text)


def specs() -> list[ToolSpec[SonCall, Any]]:
    son = AgentKind.SON
    return [
        ToolSpec(SonToolId.TAKE_LIFE, son, TakeLifeInput, ToolMeta(ActionKind.TAKE_LIFE, son_standard_action, rarity_gate=gate(Gate.TAKE_LIFE)), take_life),
        ToolSpec(SonToolId.RESURRECT_SIBLING, son, ResurrectInput, ToolMeta(ActionKind.SIBLING_SCHEME, son_standard_action), resurrect_sibling),
        ToolSpec(
            SonToolId.HINDER_RETURN,
            son,
            ScatterInput,
            ToolMeta(ActionKind.HINDER_RETURN, son_standard_action, essence_cost=lambda rules: rules.death.hinder_return_cost),
            scatter,
        ),
    ]
