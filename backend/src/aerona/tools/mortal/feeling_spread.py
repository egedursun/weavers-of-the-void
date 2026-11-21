from typing import Any

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.households import HouseholdMemberRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.mind import Emotion
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.feeling_spread.moods import mood_of
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.stats import stat
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail

BASE_STIR = 10
CHARISMA_SHARE = 4


class StirFeelingInput(ToolInput):
    place_or_household_id: int
    feeling: Emotion


async def stir_feeling_tool(call: MortalCall, args: StirFeelingInput) -> str:
    household = await call.session.scalar(
        select(HouseholdMemberRow.household_id).where(
            HouseholdMemberRow.member_node_id == call.me.id, HouseholdMemberRow.household_id == args.place_or_household_id
        )
    )
    place = await call.session.get(EntityRow, args.place_or_household_id) if household is None else None
    if household is None and (place is None or call.me.location_id != place.id):
        fail(MortalResult.MOOD_REFUSED, why="you stir the feeling of the place you stand in or of your own household")
    if place is not None and held(place.id):
        fail(MortalResult.MOOD_REFUSED, why="a god holds that place as it is")
    row = await mood_of(call.tick, settlement=place.id if place is not None else None, household=household)
    if "feelings" in (row.locked or []):
        fail(MortalResult.MOOD_REFUSED, why="a god holds that mood as it is")
    gain = BASE_STIR + (stat(call.me, "charisma") or 0) // CHARISMA_SHARE
    feelings = dict(row.feelings or {})
    feelings[args.feeling.value] = clamp_int(feelings.get(args.feeling.value, 0) + gain, 0, PERCENT)
    row.feelings, row.updated_epoch = feelings, call.tick.epoch
    subject = place.id if place is not None else call.me.id
    call.target(subject)
    await call.record(
        "mood.stirred",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.SUBJECT: subject},
        facts={"feeling": args.feeling, "strength": feelings[args.feeling.value]},
    )
    return result(MortalResult.FEELING_STIRRED, feeling=spoken(args.feeling), strength=feelings[args.feeling.value])


def specs() -> list[ToolSpec[MortalCall, Any]]:
    return [ToolSpec(MortalToolId.STIR_FEELING, AgentKind.MORTAL, StirFeelingInput, ToolMeta(ActionKind.INFLUENCE, mortal_standard_action), stir_feeling_tool)]
