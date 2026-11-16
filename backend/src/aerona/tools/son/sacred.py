from typing import Annotated, Any

from pydantic import Field

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.constants.units import PERCENT
from aerona.core.errors import ValidationFailedError
from aerona.core.grammar import spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sacred import DoctrineAfterlifeRow, PetitionRow, SpiritOfficeRow, TheodicyCrisisRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.culture import ProphecyPredicate
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mind import Emotion
from aerona.domain.enums.sacred import BureauRank, DivinationQuestion, ForesightSource, OmenVerdict, SacramentKind, SacramentProtection
from aerona.engine.primitives.queries import living_entity
from aerona.engine.sacred import control
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.son import lines
from aerona.tools.son.support import ensure_in_reach

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]
PLACES = frozenset({EntityType.PLACE, EntityType.SETTLEMENT, EntityType.HOUSE})
SPIRITS = frozenset({EntityType.SPIRIT})
MORTALS = frozenset({EntityType.MORTAL})
TOWNS = frozenset({EntityType.SETTLEMENT})
CULTS = frozenset({EntityType.CULT})
REALMS = frozenset({EntityType.POLITY})
MIDDLE = 50


class BindGeniusLocusInput(ToolInput):
    place_id: int
    reason: Reason


class JudgePetitionInput(ToolInput):
    petition_id: int
    granted: bool
    reason: Reason


class AppointSpiritInput(ToolInput):
    spirit_id: int
    rank: BureauRank | None = None
    reason: Reason


class AnswerMysticInput(ToolInput):
    mortal_id: int
    reason: Reason


class EaseTheodicyInput(ToolInput):
    crisis_id: int
    reason: Reason


class TeachSacramentInput(ToolInput):
    cult_id: int
    kind: SacramentKind
    protection: SacramentProtection | None = None
    reason: Reason


class AlignAfterlifeInput(ToolInput):
    cult_id: int
    reason: Reason


class SwayDivinerInput(ToolInput):
    realm_id: int
    question: DivinationQuestion
    verdict: OmenVerdict
    reason: Reason


class GrantForesightInput(ToolInput):
    mortal_id: int
    subject_id: int
    reason: Reason


class FeedOnInput(ToolInput):
    emotion: Emotion
    weight: int = Field(ge=0, le=PERCENT)
    reason: Reason


async def reached(call: SonCall, entity_id: int | None, kinds: frozenset[EntityType], refused: SonResult, why: str) -> EntityRow:
    entity = await living_entity(call.session, entity_id)
    if entity is None or entity.entity_type not in kinds:
        fail(refused, why=why)
    await ensure_in_reach(call, entity)
    if held(entity.id):
        fail(refused, why="a stronger hand holds it")
    return entity


def reason_of(error: ValidationFailedError) -> str:
    return str(error).rstrip(".")


async def bind_genius_locus(call: SonCall, args: BindGeniusLocusInput) -> str:
    place = await reached(call, args.place_id, PLACES, SonResult.GENIUS_REFUSED, "there is no such place, town or house")
    try:
        row = await control.raise_spirit(call.tick, place.id, None, None, call.son.id)
    except ValidationFailedError as error:
        fail(SonResult.GENIUS_REFUSED, why=reason_of(error))
    call.target(row.spirit_entity_id)
    await call.chronicle(
        ChronicleKind.WORSHIP, lines.BIND_GENIUS_LOCUS, entity_ids=[place.id, row.spirit_entity_id], son=call.son.name, place=place.name, reason=args.reason
    )
    return result(SonResult.GENIUS_BOUND, place=place.name, kind=row.kind.value)


async def judge_petition(call: SonCall, args: JudgePetitionInput) -> str:
    petition = await call.session.get(PetitionRow, args.petition_id)
    if petition is None:
        fail(SonResult.PETITION_REFUSED, why="there is no such petition")
    office = await call.session.get(SpiritOfficeRow, petition.office_spirit_id)
    spirit = await reached(call, petition.office_spirit_id, SPIRITS, SonResult.PETITION_REFUSED, "its office is beyond you")
    if office is None:
        fail(SonResult.PETITION_REFUSED, why="its office stands empty")
    try:
        await control.judge(call.tick, petition.id, args.granted, call.son.id)
    except ValidationFailedError as error:
        fail(SonResult.PETITION_REFUSED, why=reason_of(error))
    call.target(spirit.id)
    verdict = "granted" if args.granted else "denied"
    await call.chronicle(
        ChronicleKind.WORSHIP, lines.JUDGE_PETITION, entity_ids=[spirit.id], son=call.son.name, office=spirit.name, verdict=verdict, reason=args.reason
    )
    return result(SonResult.PETITION_JUDGED, office=spirit.name, verdict=verdict)


async def appoint_spirit(call: SonCall, args: AppointSpiritInput) -> str:
    spirit = await reached(call, args.spirit_id, SPIRITS, SonResult.SPIRIT_APPOINT_REFUSED, "there is no such spirit")
    try:
        row = await control.appoint(call.tick, spirit.id, args.rank, call.son.id)
    except ValidationFailedError as error:
        fail(SonResult.SPIRIT_APPOINT_REFUSED, why=reason_of(error))
    call.target(spirit.id)
    standing = "dismissed" if row.dismissed else f"made a spirit of {spoken(row.rank)} rank"
    await call.chronicle(
        ChronicleKind.WORSHIP, lines.APPOINT_SPIRIT, entity_ids=[spirit.id], son=call.son.name, spirit=spirit.name, standing=standing, reason=args.reason
    )
    return result(SonResult.SPIRIT_APPOINTED, spirit=spirit.name, standing=standing)


async def answer_mystic(call: SonCall, args: AnswerMysticInput) -> str:
    mortal = await reached(call, args.mortal_id, MORTALS, SonResult.MYSTIC_REFUSED, "there is no such mortal")
    try:
        row = await control.make_mystic(call.tick, mortal.id, call.son.id)
    except ValidationFailedError as error:
        fail(SonResult.MYSTIC_REFUSED, why=reason_of(error))
    call.target(mortal.id)
    await call.chronicle(ChronicleKind.WORSHIP, lines.ANSWER_MYSTIC, entity_ids=[mortal.id], son=call.son.name, mortal=mortal.name, reason=args.reason)
    return result(SonResult.MYSTIC_ANSWERED, mortal=mortal.name, visions=row.visions, followers=row.followers)


async def ease_theodicy(call: SonCall, args: EaseTheodicyInput) -> str:
    crisis = await call.session.get(TheodicyCrisisRow, args.crisis_id)
    if crisis is None:
        fail(SonResult.THEODICY_REFUSED, why="there is no such crisis of faith")
    town = await reached(call, crisis.community_entity_id, TOWNS, SonResult.THEODICY_REFUSED, "its town is beyond you")
    try:
        await control.answer_crisis(call.tick, crisis.id, call.son.id)
    except ValidationFailedError as error:
        fail(SonResult.THEODICY_REFUSED, why=reason_of(error))
    call.target(town.id)
    await call.chronicle(ChronicleKind.MIRACLE, lines.EASE_THEODICY, entity_ids=[town.id], son=call.son.name, town=town.name, reason=args.reason)
    return result(SonResult.THEODICY_EASED, town=town.name)


async def teach_sacrament(call: SonCall, args: TeachSacramentInput) -> str:
    cult = await reached(call, args.cult_id, CULTS, SonResult.SACRAMENT_REFUSED, "there is no such church")
    try:
        row = await control.teach(call.tick, cult.id, args.kind, args.protection, call.tick.rules.sacraments.strength)
    except ValidationFailedError as error:
        fail(SonResult.SACRAMENT_REFUSED, why=reason_of(error))
    call.target(cult.id)
    await call.chronicle(
        ChronicleKind.WORSHIP, lines.TEACH_SACRAMENT, entity_ids=[cult.id], son=call.son.name, cult=cult.name, sacrament=args.kind.value, reason=args.reason
    )
    return result(SonResult.SACRAMENT_TAUGHT, cult=cult.name, sacrament=args.kind.value, protection=row.protection.value)


async def align_afterlife(call: SonCall, args: AlignAfterlifeInput) -> str:
    cult = await reached(call, args.cult_id, CULTS, SonResult.AFTERLIFE_REFUSED, "there is no such church")
    try:
        if await call.session.get(DoctrineAfterlifeRow, cult.id) is None:
            await control.teach_afterlife(call.tick, cult.id, None)
        row = await control.align(call.tick, cult.id, call.son.id, charge=True)
    except ValidationFailedError as error:
        fail(SonResult.AFTERLIFE_REFUSED, why=reason_of(error))
    call.target(cult.id)
    model = row.model.value.replace("_", " ")
    await call.chronicle(ChronicleKind.WORSHIP, lines.ALIGN_AFTERLIFE, entity_ids=[cult.id], son=call.son.name, cult=cult.name, model=model, reason=args.reason)
    return result(SonResult.AFTERLIFE_ALIGNED, cult=cult.name, model=model, cost=call.tick.rules.afterlife_belief.align_cost)


async def sway_diviner(call: SonCall, args: SwayDivinerInput) -> str:
    realm = await reached(call, args.realm_id, REALMS, SonResult.DIVINER_REFUSED, "there is no such realm")
    try:
        row = await control.read_omens(call.tick, realm.id, args.question, verdict=args.verdict, swayed_by=call.son.id, system_id=None)
    except ValidationFailedError as error:
        fail(SonResult.DIVINER_REFUSED, why=reason_of(error))
    call.target(realm.id)
    await call.chronicle(
        ChronicleKind.FATE, lines.SWAY_DIVINER, entity_ids=[realm.id], son=call.son.name, realm=realm.name, verdict=args.verdict.value, reason=args.reason
    )
    return result(SonResult.DIVINER_SWAYED, realm=realm.name, verdict=args.verdict.value, heeded="heeded it" if row.heeded else "paid it little mind")


async def grant_foresight(call: SonCall, args: GrantForesightInput) -> str:
    mortal = await reached(call, args.mortal_id, MORTALS, SonResult.FORESIGHT_REFUSED, "there is no such mortal")
    subject = await living_entity(call.session, args.subject_id)
    if subject is None:
        fail(SonResult.FORESIGHT_REFUSED, why="there is no such subject")
    predicate = ProphecyPredicate.DIES if subject.entity_type is EntityType.MORTAL else ProphecyPredicate.FALLS
    certainty = MIDDLE + call.tick.rules.prescience.god_sight
    try:
        row = await control.foretell(call.tick, mortal.id, predicate, subject.id, certainty=certainty, source=ForesightSource.GOD, proclaimed=True)
    except ValidationFailedError as error:
        fail(SonResult.FORESIGHT_REFUSED, why=reason_of(error))
    call.target(mortal.id)
    await call.chronicle(
        ChronicleKind.FATE,
        lines.GRANT_FORESIGHT,
        entity_ids=[mortal.id, subject.id],
        son=call.son.name,
        mortal=mortal.name,
        subject=subject.name,
        reason=args.reason,
    )
    return result(SonResult.FORESIGHT_GRANTED, mortal=mortal.name, subject=subject.name, certainty=row.certainty)


async def feed_on(call: SonCall, args: FeedOnInput) -> str:
    try:
        await control.set_feeding(call.tick, call.son.id, args.emotion, args.weight)
    except ValidationFailedError as error:
        fail(SonResult.FEEDING_REFUSED, why=reason_of(error))
    call.target(call.son.id)
    await call.chronicle(ChronicleKind.WORSHIP, lines.FEED_ON, entity_ids=[], son=call.son.name, emotion=args.emotion.value, reason=args.reason)
    return result(SonResult.FEEDING_SET, emotion=args.emotion.value, weight=args.weight)


def specs() -> list[ToolSpec[SonCall, Any]]:
    son = AgentKind.SON
    meta = ToolMeta(ActionKind.INFLUENCE, son_standard_action)
    return [
        ToolSpec(SonToolId.BIND_GENIUS_LOCUS, son, BindGeniusLocusInput, meta, bind_genius_locus),
        ToolSpec(SonToolId.JUDGE_PETITION, son, JudgePetitionInput, meta, judge_petition),
        ToolSpec(SonToolId.APPOINT_SPIRIT, son, AppointSpiritInput, meta, appoint_spirit),
        ToolSpec(SonToolId.ANSWER_MYSTIC, son, AnswerMysticInput, meta, answer_mystic),
        ToolSpec(SonToolId.EASE_THEODICY, son, EaseTheodicyInput, meta, ease_theodicy),
        ToolSpec(SonToolId.TEACH_SACRAMENT, son, TeachSacramentInput, meta, teach_sacrament),
        ToolSpec(SonToolId.ALIGN_AFTERLIFE, son, AlignAfterlifeInput, meta, align_afterlife),
        ToolSpec(SonToolId.SWAY_DIVINER, son, SwayDivinerInput, meta, sway_diviner),
        ToolSpec(SonToolId.GRANT_FORESIGHT, son, GrantForesightInput, meta, grant_foresight),
        ToolSpec(SonToolId.FEED_ON, son, FeedOnInput, meta, feed_on),
    ]
