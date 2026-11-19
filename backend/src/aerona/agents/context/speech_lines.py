from sqlalchemy import or_, select

from aerona.agents.context.cycle_lines import named
from aerona.agents.context.scope import Scope
from aerona.core.grammar import spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.speech import HumourStyleRow, SpeechRow
from aerona.engine.body.customs import people_of

RECENT = 3


async def mortal_speech_lines(scope: Scope, me: EntityRow) -> list[str]:
    session = scope.session
    found: list[str] = []
    folk = await people_of(session, me)
    style = await session.get(HumourStyleRow, folk.id) if folk is not None else None
    if style is not None:
        open_to = [
            name
            for name, allowed in (("rulers", style.mock_rulers), ("gods", style.mock_gods), ("kin", style.mock_kin), ("strangers", style.mock_strangers))
            if allowed
        ]
        found.append(
            f"your people's humour runs to {spoken(style.form)}; they may mock {', '.join(open_to) or 'no one'}; "
            f"offence comes at {style.offence_threshold}, directness {style.directness}, silence {style.silence} of 100"
        )
    places = [place for place in (me.location_id,) if place is not None]
    for speech in await session.scalars(
        select(SpeechRow)
        .where(or_(SpeechRow.speaker_node_id == me.id, SpeechRow.place_entity_id.in_(places)), SpeechRow.epoch >= scope.epoch - RECENT)
        .order_by(SpeechRow.epoch.desc(), SpeechRow.id.desc())
        .limit(RECENT)
    ):
        who = "you" if speech.speaker_node_id == me.id else await named(scope, speech.speaker_node_id)
        found.append(f"{who} spoke at the {spoken(speech.venue)} to {spoken(speech.aim)}, with effect {speech.effect}")
    return found
