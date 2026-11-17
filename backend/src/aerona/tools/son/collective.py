from typing import Annotated, Any

from pydantic import Field

from aerona.catalog.storylets import STORYLETS
from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.db.tables.collective import AccountRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.collective import CollectiveTrigger, StoryletId
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.collective.accounts import expose, scholar_in
from aerona.engine.collective.crowds import stir
from aerona.engine.collective.storylets import CASTERS, begin, conditions_hold, names
from aerona.engine.primitives.queries import living_entity
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.son.support import ensure_in_reach

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


class StirCrowdInput(ToolInput):
    town_id: int
    grievance: CollectiveTrigger
    reason: Reason


class RevealInput(ToolInput):
    account_id: int
    reason: Reason


class SetStoryletInput(ToolInput):
    storylet: StoryletId
    reason: Reason


async def stir_crowd(call: SonCall, args: StirCrowdInput) -> str:
    town = await living_entity(call.session, args.town_id)
    if town is None or await call.session.get(SettlementProfileRow, town.id) is None:
        fail(SonResult.CROWD_REFUSED, why="there is no such town")
    await ensure_in_reach(call, town)
    mood = await stir(call.tick, town.id, args.grievance)
    if mood is None:
        fail(SonResult.CROWD_REFUSED, why="a stronger hand holds that town still")
    call.target(town.id)
    await call.record(
        "tools.son.stir_crowd",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.PLACE: town.id},
        facts={"reason": args.reason},
        place=town.id,
        kind=ChronicleKind.WORLD,
    )
    return result(SonResult.CROWD_STIRRED, name=town.name, anger=mood.anger, anxiety=mood.anxiety, fervour=mood.fervour)


async def reveal_true_history(call: SonCall, args: RevealInput) -> str:
    revision = await call.session.get(AccountRow, args.account_id)
    original = await call.session.get(AccountRow, revision.revised_from_id) if revision is not None and revision.revised_from_id is not None else None
    realm = await call.session.get(EntityRow, revision.holder_entity_id) if revision is not None else None
    if revision is None or original is None or realm is None:
        fail(SonResult.HISTORY_REFUSED, why="that account was never rewritten")
    await ensure_in_reach(call, realm)
    await expose(call.tick, revision, original, await scholar_in(call.tick, realm.id))
    call.target(realm.id)
    await call.record(
        "tools.son.reveal_true_history",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: realm.id},
        facts={"reason": args.reason},
        kind=ChronicleKind.WORLD,
    )
    return result(SonResult.HISTORY_REVEALED, name=realm.name, credence=revision.credence)


async def set_storylet(call: SonCall, args: SetStoryletInput) -> str:
    world_id = call.world_id
    if world_id is None:
        fail(SonResult.STORYLET_REFUSED, why="you stand in no world")
    spec = STORYLETS[args.storylet]
    cast = await CASTERS[args.storylet](call.tick, world_id)
    if cast is None or not await conditions_hold(call.tick, spec, cast):
        fail(SonResult.STORYLET_REFUSED, why="nobody in your world fits its parts now")
    chooser = await living_entity(call.session, cast[spec.chooser])
    if chooser is None:
        fail(SonResult.STORYLET_REFUSED, why="the one it would fall to is gone")
    await ensure_in_reach(call, chooser)
    await begin(call.tick, args.storylet, world_id, cast)
    known = await names(call.session, cast)
    await call.record(
        "tools.son.set_storylet",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: chooser.id},
        facts={"title": str(spec.title), "reason": args.reason},
        kind=ChronicleKind.WORLD,
    )
    return result(SonResult.STORYLET_SET, title=spec.title, chooser=known[spec.chooser.value])


def specs() -> list[ToolSpec[SonCall, Any]]:
    son = AgentKind.SON
    meta = ToolMeta(ActionKind.INFLUENCE, son_standard_action)
    return [
        ToolSpec(SonToolId.STIR_CROWD, son, StirCrowdInput, meta, stir_crowd),
        ToolSpec(SonToolId.REVEAL_TRUE_HISTORY, son, RevealInput, meta, reveal_true_history),
        ToolSpec(SonToolId.SET_STORYLET, son, SetStoryletInput, meta, set_storylet),
    ]
