from typing import Annotated, Any

from pydantic import Field

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.core.grammar import spoken
from aerona.db.tables.economy import ResourceProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.crafts import AffinityMode
from aerona.domain.enums.culture import MagicSchool
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mind import Emotion
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.crafts import control
from aerona.engine.primitives.queries import living_entity
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.son.support import ensure_in_reach

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


class WakeSpiritInput(ToolInput):
    region_id: int
    emotion: Emotion
    reason: Reason


class LayAffinityInput(ToolInput):
    resource_id: int
    school: MagicSchool
    mode: AffinityMode
    reason: Reason


async def wake_spirit(call: SonCall, args: WakeSpiritInput) -> str:
    region = await living_entity(call.session, args.region_id)
    if region is None or region.entity_type is not EntityType.REGION:
        fail(SonResult.SPIRIT_REFUSED, why="there is no such land")
    await ensure_in_reach(call, region)
    if held(region.id):
        fail(SonResult.SPIRIT_REFUSED, why="it is held")
    table = call.tick.rules.emotion_spirits
    await control.set_record(
        call.tick,
        "emotion_spirit",
        {},
        {"region_entity_id": region.id, "emotion": args.emotion, "strength": 50, "born_epoch": call.tick.epoch, "lifetime": table.lifetime},
    )
    call.target(region.id)
    await call.record(
        "tools.son.wake_spirit",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.PLACE: region.id},
        facts={"emotion": args.emotion, "reason": args.reason},
        place=region.id,
        kind=ChronicleKind.MIRACLE,
    )
    return result(SonResult.SPIRIT_WOKEN, region=region.name, emotion=spoken(args.emotion))


async def lay_affinity(call: SonCall, args: LayAffinityInput) -> str:
    resource = await living_entity(call.session, args.resource_id)
    profile = await call.session.get(ResourceProfileRow, args.resource_id)
    if resource is None or profile is None:
        fail(SonResult.AFFINITY_REFUSED, why="there is no such resource")
    await ensure_in_reach(call, resource)
    if profile.world_material_id is None:
        fail(SonResult.AFFINITY_REFUSED, why="its stuff is of no material of this world's own")
    if held(resource.id):
        fail(SonResult.AFFINITY_REFUSED, why="it is held")
    await control.set_record(
        call.tick, "material_affinity", {"material_id": profile.world_material_id, "school": args.school}, {"mode": args.mode, "power": 50}
    )
    call.target(resource.id)
    told = spoken(args.school)
    await call.record(
        "tools.son.lay_affinity",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: resource.id},
        facts={"school": str(told), "reason": args.reason},
        kind=ChronicleKind.RESOURCE,
    )
    return result(SonResult.AFFINITY_LAID, resource=resource.name, school=told, mode=spoken(args.mode))


def specs() -> list[ToolSpec[SonCall, Any]]:
    son = AgentKind.SON
    meta = ToolMeta(ActionKind.INFLUENCE, son_standard_action)
    return [
        ToolSpec(SonToolId.WAKE_SPIRIT, son, WakeSpiritInput, meta, wake_spirit),
        ToolSpec(SonToolId.LAY_AFFINITY, son, LayAffinityInput, meta, lay_affinity),
    ]
