from typing import Annotated, Any

from pydantic import Field

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mind import Emotion
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.feeling_spread.moods import mood_of
from aerona.engine.primitives.queries import living_entity
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.son.support import ensure_in_reach

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


class MoveHeartsInput(ToolInput):
    place_id: int
    feeling: Emotion
    strength: int = Field(ge=1, le=PERCENT)
    reason: Reason


async def move_hearts(call: SonCall, args: MoveHeartsInput) -> str:
    place = await living_entity(call.session, args.place_id)
    if place is None or place.entity_type is not EntityType.SETTLEMENT:
        fail(SonResult.HEARTS_REFUSED, why="there is no such settlement")
    await ensure_in_reach(call, place)
    row = await mood_of(call.tick, settlement=place.id)
    if held(place.id) or "feelings" in (row.locked or []):
        fail(SonResult.HEARTS_REFUSED, why="that mood is held as it is")
    feelings = dict(row.feelings or {})
    feelings[args.feeling.value] = args.strength
    row.feelings, row.leading, row.updated_epoch = feelings, args.feeling, call.tick.epoch
    call.target(place.id)
    await call.record("mood.moved", roles={IncidentRole.SUBJECT: place.id}, facts={"feeling": args.feeling, "strength": args.strength})
    return result(SonResult.HEARTS_MOVED, place=place.name, feeling=spoken(args.feeling), strength=args.strength)


def specs() -> list[ToolSpec[SonCall, Any]]:
    return [ToolSpec(SonToolId.MOVE_HEARTS, AgentKind.SON, MoveHeartsInput, ToolMeta(ActionKind.INFLUENCE, son_standard_action), move_hearts)]
