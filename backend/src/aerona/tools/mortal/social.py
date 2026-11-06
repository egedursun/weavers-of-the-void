from typing import Any

from aerona.catalog.relations import CONTESTS, INTERACTIONS, STAKE_LABELS
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.relations import AppealKind, ContestEnd, ContestKind, ContestStake, InteractionKind, PersuasionAim
from aerona.engine.primitives.naming import seed_of
from aerona.engine.relations.contests import Bout, ContestTally, hold_contest
from aerona.engine.relations.interactions import SocialTally, interact, load_scene
from aerona.engine.relations.persuasion import persuade
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.mortal.support import require_target

SPAN = 100


class SocialiseInput(ToolInput):
    target_id: int
    interaction: InteractionKind


class ContestInput(ToolInput):
    target_id: int
    kind: ContestKind
    stake: ContestStake = ContestStake.HONOUR


class PersuadeInput(ToolInput):
    target_id: int
    appeal: AppealKind
    axis: ValueAxis
    toward: int = SPAN


async def fellow(call: MortalCall, target_id: int) -> EntityRow:
    if call.me.entity_type is not EntityType.MORTAL:
        fail(MortalResult.SOCIAL_NOT_MORTAL)
    other = await require_target(call, target_id)
    if other.entity_type is not EntityType.MORTAL or other.id == call.me.id:
        fail(MortalResult.SOCIAL_TARGET)
    if other.location_id != call.me.location_id:
        fail(MortalResult.SOCIAL_FAR, name=other.name)
    return other


async def socialise(call: MortalCall, args: SocialiseInput) -> str:
    other = await fellow(call, args.target_id)
    scene = await load_scene(call.tick, call.me.location_id or other.id, [call.me, other])
    rng = call.tick.rng(seed_of("chosen_interaction", call.me.id, other.id, call.epoch))
    landed = await interact(scene, call.me.id, other.id, args.interaction, rng=rng, tally=SocialTally())
    call.target(other.id)
    label = INTERACTIONS[args.interaction].label.lower()
    return result(MortalResult.SOCIALISED if landed else MortalResult.SOCIAL_MISSED, action=label, name=other.name)


async def challenge(call: MortalCall, args: ContestInput) -> str:
    other = await fellow(call, args.target_id)
    bout = Bout(args.kind, args.stake, call.me, other, place_id=call.me.location_id)
    row = await hold_contest(call.tick, bout, ContestTally())
    if row is None:
        fail(MortalResult.SOCIAL_TARGET)
    call.target(other.id)
    outcome = "drew" if row.outcome is ContestEnd.DRAWN else "won" if row.outcome is ContestEnd.CHALLENGER else "lost"
    return result(MortalResult.CONTEST_HELD, kind=CONTESTS[args.kind].label.lower(), stake=STAKE_LABELS[args.stake].lower(), name=other.name, outcome=outcome)


async def argue(call: MortalCall, args: PersuadeInput) -> str:
    other = await fellow(call, args.target_id)
    argument = await persuade(call.tick, call.me.id, other.id, args.appeal, PersuasionAim.BELIEF, axis=args.axis, toward=args.toward)
    call.target(other.id)
    return result(MortalResult.PERSUADED if argument.success else MortalResult.NOT_PERSUADED, name=other.name, score=argument.score)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    mortal = AgentKind.MORTAL
    standard = mortal_standard_action
    return [
        ToolSpec(MortalToolId.SOCIALISE, mortal, SocialiseInput, ToolMeta(ActionKind.INFLUENCE, standard), socialise),
        ToolSpec(MortalToolId.CHALLENGE_TO_CONTEST, mortal, ContestInput, ToolMeta(ActionKind.INFLUENCE, standard), challenge),
        ToolSpec(MortalToolId.PERSUADE, mortal, PersuadeInput, ToolMeta(ActionKind.INFLUENCE, standard), argue),
    ]
