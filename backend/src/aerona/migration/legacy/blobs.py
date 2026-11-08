from typing import Any

from aerona.domain.enums.agent import CouncilVote
from aerona.domain.enums.creator import CreatorPassion
from aerona.domain.enums.meta import ScoreComponent
from aerona.domain.enums.son import ExistenceMode
from aerona.domain.enums.travel import JourneyEventKind
from aerona.domain.models.profiles import EntityDepth, Epic, EpicChapter, ExistenceProfile, GodDepth, GodName, Personality, Saying, TravelResource
from aerona.domain.models.records import CouncilBallot, CouncilMinutes, CouncilSpeech, JourneyEvent, ScoreBreakdown
from aerona.migration.legacy.values import as_dict, as_int, as_list, as_text
from aerona.migration.legacy.vocabulary import Vocabulary


def _texts(value: Any) -> tuple[str, ...]:
    return tuple(text for item in as_list(value) if (text := as_text(item)) is not None)


def _sayings(vocabulary: Vocabulary, shape: str, value: Any) -> tuple[Saying, ...]:
    sayings: list[Saying] = []
    for item in as_list(value):
        if isinstance(item, dict):
            text = as_text(vocabulary.field(shape, item, "saying_text"))
            if text is not None:
                sayings.append(Saying(form=as_text(vocabulary.field(shape, item, "saying_form")) or "", text=text))
        elif (text := as_text(item)) is not None:
            sayings.append(Saying(form="", text=text))
    return tuple(sayings)


def _epoch(value: Any, fallback: int) -> int:
    number = as_int(value)
    return number if number is not None and number >= 0 else fallback


def personality(vocabulary: Vocabulary, payload: Any) -> Personality | None:
    data = as_dict(payload)
    if not data:
        return None
    return Personality(**{field: as_text(vocabulary.field("personality", data, field)) or "" for field in Personality.model_fields})


def existence(vocabulary: Vocabulary, payload: Any) -> tuple[ExistenceProfile | None, str | None]:
    data = as_dict(payload)
    if not data:
        return None, None
    raw_mode = as_text(vocabulary.field("existence", data, "mode"))
    mode = vocabulary.decode_as("existence_mode", raw_mode, ExistenceMode)
    profile = ExistenceProfile(
        nature=as_text(vocabulary.field("existence", data, "nature")) or "",
        mode=mode,
        manifestation=as_text(vocabulary.field("existence", data, "manifestation")) or "",
        true_name=as_text(vocabulary.field("existence", data, "true_name")) or "",
    )
    return profile, raw_mode if raw_mode is not None and mode is None else None


def entity_depth(vocabulary: Vocabulary, payload: Any, fallback_epoch: int) -> EntityDepth | None:
    data = as_dict(payload)
    if not data:
        return None
    specifics = {str(key): text for key, value in as_dict(vocabulary.field("entity_depth", data, "specifics")).items() if (text := as_text(value))}
    return EntityDepth(
        history=as_text(vocabulary.field("entity_depth", data, "history")) or "",
        rumours=_texts(vocabulary.field("entity_depth", data, "rumours")),
        sayings=_sayings(vocabulary, "entity_depth", vocabulary.field("entity_depth", data, "sayings")),
        details=_texts(vocabulary.field("entity_depth", data, "details")),
        hidden_truth=as_text(vocabulary.field("entity_depth", data, "hidden_truth")) or "",
        specifics=specifics,
        epoch=_epoch(vocabulary.field("entity_depth", data, "epoch"), fallback_epoch),
    )


def god_depth(vocabulary: Vocabulary, payload: Any, fallback_epoch: int) -> GodDepth | None:
    data = as_dict(payload)
    if not data:
        return None
    names = []
    for item in as_list(vocabulary.field("god_depth", data, "names")):
        name = as_text(vocabulary.field("god_depth", item, "name")) if isinstance(item, dict) else as_text(item)
        if name is not None:
            names.append(
                GodName(
                    name=name,
                    used_by=as_text(vocabulary.field("god_depth", item, "used_by")) or "",
                    meaning=as_text(vocabulary.field("god_depth", item, "meaning")) or "",
                )
            )
    return GodDepth(
        history=as_text(vocabulary.field("god_depth", data, "history")) or "",
        names=tuple(names),
        secrets=_texts(vocabulary.field("god_depth", data, "secrets")),
        fears=_texts(vocabulary.field("god_depth", data, "fears")),
        taboos=_texts(vocabulary.field("god_depth", data, "taboos")),
        gifts=_texts(vocabulary.field("god_depth", data, "gifts")),
        desire=as_text(vocabulary.field("god_depth", data, "desire")) or "",
        sayings=_sayings(vocabulary, "god_depth", vocabulary.field("god_depth", data, "sayings")),
        rumours=_texts(vocabulary.field("god_depth", data, "rumours")),
        hidden_truth=as_text(vocabulary.field("god_depth", data, "hidden_truth")) or "",
        view_of_pantheon=as_text(vocabulary.field("god_depth", data, "view_of_pantheon")) or "",
        worship=as_text(vocabulary.field("god_depth", data, "worship")) or "",
        epoch=_epoch(vocabulary.field("god_depth", data, "epoch"), fallback_epoch),
    )


def epic(vocabulary: Vocabulary, payload: Any, fallback_epoch: int) -> Epic | None:
    data = as_dict(payload)
    if not data:
        return None
    title = as_text(vocabulary.field("epic", data, "title"))
    if title is None:
        return None
    chapters = []
    for item in as_list(vocabulary.field("epic", data, "chapters")):
        chapter_title = as_text(vocabulary.field("epic", item, "chapter_title"))
        chapter_text = as_text(vocabulary.field("epic", item, "chapter_text"))
        if chapter_title is None or chapter_text is None:
            continue
        start = _epoch(vocabulary.field("epic", item, "chapter_start"), 0)
        chapters.append(
            EpicChapter(
                title=chapter_title, text=chapter_text, epoch_start=start, epoch_end=max(start, _epoch(vocabulary.field("epic", item, "chapter_end"), start))
            )
        )
    return Epic(
        title=title,
        verse=as_text(vocabulary.field("epic", data, "verse")) or "",
        body=as_text(vocabulary.field("epic", data, "body")) or "",
        chapters=tuple(chapters),
        epoch=_epoch(vocabulary.field("epic", data, "epoch"), fallback_epoch),
    )


def travel_resource(vocabulary: Vocabulary, payload: Any) -> TravelResource | None:
    data = as_dict(payload)
    name = as_text(vocabulary.field("travel_resource", data, "name"))
    if name is None:
        return None
    return TravelResource(
        name=name,
        description=as_text(vocabulary.field("travel_resource", data, "description")) or "",
        rule=as_text(vocabulary.field("travel_resource", data, "rule")) or "",
        side_effect=as_text(vocabulary.field("travel_resource", data, "side_effect")) or "",
    )


def creator_passions(vocabulary: Vocabulary, payload: Any) -> tuple[list[CreatorPassion], bool, list[str]]:
    data = as_dict(payload)
    passions: list[CreatorPassion] = []
    unknown: list[str] = []
    for item in as_list(vocabulary.field("creator_passions", data, "passions")):
        passion = vocabulary.decode_as("creator_passion", item, CreatorPassion)
        if passion is None:
            unknown.append(str(item))
        elif passion not in passions:
            passions.append(passion)
    automatic = vocabulary.field("creator_passions", data, "automatic")
    return passions, True if automatic is None else bool(automatic), unknown


def council_minutes(vocabulary: Vocabulary, payload: Any, topic: str, son_ids: dict[int, int]) -> CouncilMinutes:
    data = as_dict(payload)
    speeches = []
    for item in as_list(vocabulary.field("council", data, "speeches")):
        legacy_son = as_int(vocabulary.field("council", item, "son_id"))
        words = as_text(vocabulary.field("council", item, "words"))
        if legacy_son is None or words is None:
            continue
        speeches.append(CouncilSpeech(son_id=son_ids.get(legacy_son, legacy_son), name=as_text(vocabulary.field("council", item, "name")) or "", words=words))
    ballots = []
    for item in as_list(vocabulary.field("council", data, "ballots")):
        legacy_son = as_int(vocabulary.field("council", item, "son_id"))
        vote = vocabulary.decode_as("council_vote", vocabulary.field("council", item, "vote"), CouncilVote)
        if legacy_son is None or vote is None:
            continue
        ballots.append(
            CouncilBallot(
                son_id=son_ids.get(legacy_son, legacy_son),
                name=as_text(vocabulary.field("council", item, "name")) or "",
                vote=vote,
                reason=as_text(vocabulary.field("council", item, "reason")) or "",
            )
        )
    caller = vocabulary.decode("council_caller", vocabulary.field("council", data, "convened_by")) or "creator"
    return CouncilMinutes(
        topic=as_text(vocabulary.field("council", data, "topic")) or topic,
        convened_by=caller,
        speeches=tuple(speeches),
        motion=as_text(vocabulary.field("council", data, "motion")) or "",
        ballots=tuple(ballots),
        passed=bool(vocabulary.field("council", data, "passed")),
        decision=as_text(vocabulary.field("council", data, "decision")) or "",
        notes=_texts(vocabulary.field("council", data, "notes")),
        summary=as_text(vocabulary.field("council", data, "summary")) or "",
    )


def journey_events(vocabulary: Vocabulary, payload: Any, fallback_epoch: int, classify: Any) -> list[JourneyEvent]:
    events = []
    for item in as_list(payload):
        text = as_text(vocabulary.field("journey_event", item, "event"))
        if text is None:
            continue
        kind: JourneyEventKind = classify(text)
        epoch = max(1, _epoch(vocabulary.field("journey_event", item, "epoch"), fallback_epoch))
        loss = max(0, as_int(vocabulary.field("journey_event", item, "loss")) or 0)
        events.append(JourneyEvent(epoch=epoch, kind=kind, text=text, loss=loss))
    return events


def score_breakdown(vocabulary: Vocabulary, payload: Any) -> tuple[ScoreBreakdown, list[str]]:
    parts: dict[ScoreComponent, int] = {}
    unknown: list[str] = []
    for key, value in as_dict(payload).items():
        component = vocabulary.decode_as("score_component", key, ScoreComponent)
        number = as_int(value)
        if component is None or number is None:
            unknown.append(str(key))
            continue
        parts[component] = number
    return ScoreBreakdown(parts=parts), unknown
