from typing import Any

from sqlalchemy import select

from aerona.catalog.life.tools import VENUE_REACH
from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.media import MediaOutletRow
from aerona.db.tables.speech import SpeechRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.speech import SpeechAim, SpeechVenue
from aerona.engine.speech.oratory import skill_of
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail


class GiveSpeechInput(ToolInput):
    venue: SpeechVenue
    aim: SpeechAim
    audience_node_id: int | None = None


class SatiriseInput(ToolInput):
    target_id: int
    venue: SpeechVenue = SpeechVenue.SQUARE


async def speak(call: MortalCall, venue: SpeechVenue, aim: SpeechAim, audience: int | None) -> SpeechRow:
    town = await call.session.get(EntityRow, call.me.location_id) if call.me.location_id is not None else None
    if town is None or town.entity_type is not EntityType.SETTLEMENT:
        fail(MortalResult.SPEECH_REFUSED, why="a speech is given in a town")
    if held(town.id):
        fail(MortalResult.SPEECH_REFUSED, why="a god holds this town as it is")
    if audience is not None and await call.session.get(EntityRow, audience) is None:
        fail(MortalResult.SPEECH_REFUSED, why="there is no such audience or subject")
    reach = VENUE_REACH[venue]
    if venue is SpeechVenue.OUTLET:
        outlet = await call.session.scalar(
            select(MediaOutletRow)
            .where(MediaOutletRow.seat_entity_id == town.id, MediaOutletRow.owner_node_id == call.me.id)
            .order_by(MediaOutletRow.id)
            .limit(1)
        )
        if outlet is None:
            fail(MortalResult.SPEECH_REFUSED, why="you own no outlet in this town to speak through")
        reach = outlet.reach
    speech = SpeechRow(
        speaker_node_id=call.me.id,
        place_entity_id=town.id,
        venue=venue,
        aim=aim,
        audience_node_id=audience,
        skill=skill_of(call.me),
        reach=min(PERCENT, reach),
        epoch=call.epoch,
        locked=[],
    )
    call.session.add(speech)
    call.target(town.id)
    await call.record(
        "speech.given",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.PLACE: town.id, **({IncidentRole.TARGET: audience} if audience is not None else {})},
        facts={"venue": venue, "aim": aim},
        place=town.id,
    )
    return speech


async def give_speech(call: MortalCall, args: GiveSpeechInput) -> str:
    speech = await speak(call, args.venue, args.aim, args.audience_node_id)
    return result(MortalResult.SPEECH_GIVEN, venue=spoken(args.venue), aim=spoken(args.aim), reach=speech.reach)


async def satirise(call: MortalCall, args: SatiriseInput) -> str:
    if args.target_id == call.me.id:
        fail(MortalResult.SPEECH_REFUSED, why="mock another, not yourself")
    speech = await speak(call, args.venue, SpeechAim.MOCK, args.target_id)
    return result(MortalResult.SPEECH_GIVEN, venue=spoken(args.venue), aim=spoken(SpeechAim.MOCK), reach=speech.reach)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    meta = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.GIVE_SPEECH, AgentKind.MORTAL, GiveSpeechInput, meta, give_speech),
        ToolSpec(MortalToolId.SATIRISE, AgentKind.MORTAL, SatiriseInput, meta, satirise),
    ]
