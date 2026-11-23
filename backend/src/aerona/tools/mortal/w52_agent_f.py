from typing import Any

from aerona.catalog.life_traits import DUEL_CONTEXT_TRAITS, having
from aerona.core.grammar import spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.life_traits import DuelContextTrait
from aerona.domain.enums.military import DuelContext, DuelEnd
from aerona.domain.enums.mind import ActKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.lore.taboos import forbidden
from aerona.engine.military.terms import war_between
from aerona.engine.phases.warfare import Theatre, duel
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.stats import stat
from aerona.engine.recording.record import FactInput
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail

AT_WAR = having(DUEL_CONTEXT_TRAITS, DuelContextTrait.AT_WAR)


class ChallengeToDuelInput(ToolInput):
    target_id: int
    context: DuelContext
    ending: DuelEnd | None = None


async def opponent(call: MortalCall, target_id: int) -> EntityRow:
    foe = await living_entity(call.session, target_id)
    if foe is None or foe.entity_type is not EntityType.MORTAL or foe.status is not EntityStatus.CANON or foe.id == call.me.id:
        fail(MortalResult.DUEL_REFUSED, why="there is no such mortal to face")
    if held(call.me.id, foe.id):
        fail(MortalResult.DUEL_REFUSED, why="one of you is held")
    if stat(call.me, "hp") == 0 or stat(foe, "hp") == 0:
        fail(MortalResult.DUEL_REFUSED, why="one of you cannot stand to fight")
    if await forbidden(call.tick, call.me.id, ActKind.DUELLING):
        fail(MortalResult.DUEL_REFUSED, why="your people forbid the duel")
    return foe


async def challenge_to_duel(call: MortalCall, args: ChallengeToDuelInput) -> str:
    foe = await opponent(call, args.target_id)
    war_id = None
    if args.context in AT_WAR:
        mine, theirs = call.me.location_id, foe.location_id
        war_id = await war_between(call.tick, mine, theirs) if mine is not None and theirs is not None else None
        if war_id is None:
            fail(MortalResult.DUEL_REFUSED, why=f"a duel of {spoken(args.context)} needs a war between your homes")
    elif foe.location_id != call.me.location_id:
        fail(MortalResult.DUEL_REFUSED, why=f"{foe.name} is not in the same place")
    theatre = await Theatre.load(call.tick)
    fought = await duel(call.tick, theatre, call.me, foe, war=None, anchor_id=None, context=args.context, ending=args.ending)
    call.target(foe.id)
    facts: dict[str, FactInput] = {"context": args.context}
    if args.ending is not None:
        facts["end"] = args.ending
    await call.record(
        "tools.mortal.challenge_to_duel", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.OPPONENT: foe.id}, facts=facts, cause=fought.incident_id
    )
    return result(MortalResult.DUEL_FOUGHT, text=fought.text)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    return [
        ToolSpec(
            MortalToolId.CHALLENGE_TO_DUEL, AgentKind.MORTAL, ChallengeToDuelInput, ToolMeta(ActionKind.INFLUENCE, mortal_standard_action), challenge_to_duel
        )
    ]
