from typing import Annotated, Any

from pydantic import Field
from sqlalchemy import select

from aerona.catalog.effect_packages import PACKAGES
from aerona.catalog.grief import GRIEF_STAGES
from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.core.grammar import spoken
from aerona.db.tables.mind import GriefRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.affliction import PackageKind, Transmission
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mind import Emotion, GriefStage, ThoughtKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.body.afflictions import afflict, bearable
from aerona.engine.body.packages_w52 import Shape
from aerona.engine.mind.thoughts import think
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail, require_canon
from aerona.tools.son.support import ensure_in_reach, require_essence

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]
STIRRED = 60


class StirEmotionInput(ToolInput):
    node_id: int
    emotion: Emotion
    reason: Reason


class EaseGriefInput(ToolInput):
    mourner_id: int
    stage: GriefStage
    reason: Reason


class LayPackageInput(ToolInput):
    node_id: int
    package: PackageKind
    reason: Reason


async def stir_emotion(call: SonCall, args: StirEmotionInput) -> str:
    mortal = await require_canon(call.session, args.node_id)
    if mortal.entity_type is not EntityType.MORTAL:
        fail(SonResult.EMOTION_REFUSED, why="only a mortal mind can be stirred so")
    await ensure_in_reach(call, mortal)
    row = await think(call.session, call.rules, mortal.id, ThoughtKind.CAUGHT_FEELING, call.epoch, intensity=STIRRED, emotion=args.emotion, forced=True)
    if row is None or held(mortal.id):
        fail(SonResult.EMOTION_REFUSED, why="that mind is held as it is")
    call.target(mortal.id)
    await call.record("tools.son.stir_emotion", roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: mortal.id}, facts={"emotion": args.emotion})
    return result(SonResult.EMOTION_STIRRED, name=mortal.name, emotion=spoken(args.emotion))


async def ease_grief(call: SonCall, args: EaseGriefInput) -> str:
    mourner = await require_canon(call.session, args.mourner_id)
    await ensure_in_reach(call, mourner)
    rows = list(await call.session.scalars(select(GriefRow).where(GriefRow.mourner_node_id == mourner.id).order_by(GriefRow.id)))
    open_rows = [row for row in rows if GRIEF_STAGES[row.stage].open] or rows[-1:]
    if not open_rows or held(mourner.id):
        fail(SonResult.GRIEF_REFUSED, why=f"{mourner.name} grieves no one, or their grief is held")
    for row in open_rows:
        row.stage, row.stage_epoch = args.stage, call.epoch
    call.target(mourner.id)
    await call.record("tools.son.ease_grief", roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: mourner.id}, facts={"stage": args.stage})
    return result(SonResult.GRIEF_MOVED, name=mourner.name, count=len(open_rows), stage=spoken(args.stage))


async def lay(call: SonCall, args: LayPackageInput, *, cursed: bool) -> str:
    bearer = await require_canon(call.session, args.node_id)
    await ensure_in_reach(call, bearer)
    if not bearable(bearer):
        fail(SonResult.PACKAGE_REFUSED, why=f"{bearer.name} cannot bear an affliction")
    cost = call.rules.costs.curse
    require_essence(call, cost)
    shape = Shape(fortune_sign=-1 if cursed else 1) if args.package is PackageKind.FORTUNE else None
    route = Transmission.CURSE if cursed else Transmission.RITE
    row = await afflict(call.tick, bearer, args.package, route, source_node_id=call.son.id, shape=shape)
    if row is None:
        fail(SonResult.PACKAGE_REFUSED, why=f"{bearer.name} is shielded from afflictions")
    call.spend_essence(cost)
    call.target(bearer.id)
    key = "tools.son.curse_with" if cursed else "tools.son.bless_with"
    await call.record(key, roles={IncidentRole.ACTOR: call.son.id, IncidentRole.PATIENT: bearer.id}, facts={"package": args.package})
    return result(SonResult.PACKAGE_LAID, name=bearer.name, package=PACKAGES[args.package].label.lower())


async def curse_with(call: SonCall, args: LayPackageInput) -> str:
    return await lay(call, args, cursed=True)


async def bless_with(call: SonCall, args: LayPackageInput) -> str:
    return await lay(call, args, cursed=False)


def specs() -> list[ToolSpec[SonCall, Any]]:
    son = AgentKind.SON
    laying = ToolMeta(ActionKind.CURSE, son_standard_action, essence_cost=lambda rules: rules.costs.curse)
    return [
        ToolSpec(SonToolId.STIR_EMOTION, son, StirEmotionInput, ToolMeta(ActionKind.INFLUENCE, son_standard_action), stir_emotion),
        ToolSpec(SonToolId.EASE_GRIEF, son, EaseGriefInput, ToolMeta(ActionKind.INFLUENCE, son_standard_action), ease_grief),
        ToolSpec(SonToolId.CURSE_WITH, son, LayPackageInput, laying, curse_with),
        ToolSpec(SonToolId.BLESS_WITH, son, LayPackageInput, laying, bless_with),
    ]
