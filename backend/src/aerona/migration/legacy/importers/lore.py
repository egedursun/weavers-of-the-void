from aerona.catalog.quests import LEGACY_LEGENDARY
from aerona.constants.schema import FACT_OBJECT_MAX_LENGTH, FACT_PREDICATE_MAX_LENGTH, LEXEME_TEXT_MAX_LENGTH, LEXEME_WORD_MAX_LENGTH, NAME_MAX_LENGTH
from aerona.db.tables.entities import NetworkReviewRow
from aerona.db.tables.lore import CanonFactRow, CouncilRow, FolkBeliefRow, LegendaryQuestRow, LexemeRow, MessageRow, ThreadLinkRow, ThreadRow, lexeme_key
from aerona.domain.enums.agent import MessageIntent, PrayerRequest
from aerona.domain.enums.chronicle import PartOfSpeech, ThreadLinkRole, ThreadStatus
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.quests import QuestTargetKind
from aerona.engine.primitives.canon_facts import Predicate
from aerona.migration.legacy import blobs
from aerona.migration.legacy.context import MigrationContext
from aerona.migration.legacy.idmap import LegacyKind
from aerona.migration.legacy.importers.cosmos import DEFAULTED, UNKNOWN_VALUE
from aerona.migration.legacy.timestamps import legacy_time
from aerona.migration.legacy.values import as_dict, as_int, as_list, truncated

PREDICATES = {
    "located_in": Predicate.LOCATED_IN,
    "creator": Predicate.CREATOR,
    "language": Predicate.LANGUAGE,
    "worships": Predicate.WORSHIPS,
    "descends": Predicate.DESCENDS,
}
CREATOR_SON_ID = 0


async def import_facts(context: MigrationContext) -> None:
    for row in context.source.iterate("canon_facts", ("id",)):
        reference = f"fact:{row.integer('id')}"
        subject = context.entity(row.integer("subject_id"))
        object_id = context.entity(row.integer("object_id"))
        object_text = truncated(context.report, reference, "object", row.text("object_text"), FACT_OBJECT_MAX_LENGTH)
        raw = row.text("predicate")
        if subject is None or raw is None or (object_id is None and object_text is None):
            context.report.place_failed("canon fact", reference, "subject, predicate or object is missing")
            continue
        symbolic = context.vocabulary.canon_predicates.get(raw.strip())
        predicate = PREDICATES[symbolic] if symbolic is not None else truncated(context.report, reference, "predicate", raw, FACT_PREDICATE_MAX_LENGTH) or raw
        if symbolic is not None:
            context.report.convert(f"facts_typed_{symbolic}")
        context.add(
            CanonFactRow(
                subject_entity_id=subject,
                predicate=predicate,
                object_entity_id=object_id,
                object_text=object_text,
                epoch=max(0, row.integer("epoch") or 0),
                source_entity_id=context.entity(row.integer("source_id")),
                deterministic=symbolic is not None,
                active=row.flag("active"),
            )
        )
        await context.flush_if_full()
    await context.flush()


async def import_lexicon(context: MigrationContext) -> None:
    seen: set[tuple[int, str]] = set()
    for row in context.source.iterate("lexicon", ("id",)):
        reference = f"word:{row.integer('id')}"
        language = context.entity(row.integer("language_id"))
        facts = context.facts(language)
        word = truncated(context.report, reference, "word", row.text("word"), LEXEME_WORD_MAX_LENGTH)
        meaning = truncated(context.report, reference, "meaning", row.text("meaning"), LEXEME_TEXT_MAX_LENGTH)
        if language is None or facts is None or facts.entity_type is not EntityType.LANGUAGE or word is None or meaning is None:
            context.report.place_failed("word", reference, "language, word or meaning is missing")
            continue
        key = (language, lexeme_key(word))
        if key in seen:
            context.report.convert("duplicate_words_skipped")
            continue
        seen.add(key)
        raw_pos = row.text("part_of_speech")
        part = context.vocabulary.decode_as("part_of_speech", raw_pos, PartOfSpeech)
        if raw_pos is not None and part is None:
            context.report.warn(UNKNOWN_VALUE, reference, f"part of speech {raw_pos!r} dropped")
        code = row.text("added_by_kind")
        actor = context.vocabulary.decode_as("actor_kind", code, ActorKind) or ActorKind.SYSTEM
        lexeme = LexemeRow(
            language_entity_id=language,
            word=word,
            meaning=meaning,
            part_of_speech=part,
            etymology=truncated(context.report, reference, "etymology", row.text("etymology"), LEXEME_TEXT_MAX_LENGTH),
            example=truncated(context.report, reference, "example", row.text("example"), LEXEME_TEXT_MAX_LENGTH),
            added_by_kind=actor,
            added_by_node_id=context.node(code, row.integer("added_by_id")),
            epoch=max(0, row.integer("epoch") or 0),
        )
        stamp = legacy_time(row.raw("created_at"))
        if stamp is not None:
            lexeme.created_at = stamp
        context.add(lexeme)
        await context.flush_if_full()
    await context.flush()


def _quest(context: MigrationContext, thread_id: int, epoch: int, payload: object) -> None:
    data = as_dict(payload)
    if not data:
        return
    vocabulary = context.vocabulary
    raw_kind = vocabulary.field("quest", data, "kind")
    legacy = vocabulary.decode("legendary_quest_kind", raw_kind)
    pair = LEGACY_LEGENDARY.get(legacy) if legacy is not None else None
    if pair is None:
        context.report.place_failed("legendary quest", f"thread:{thread_id}", f"unknown quest kind {raw_kind!r}")
        return
    target = as_int(vocabulary.field("quest", data, "target"))
    opener = vocabulary.decode_as("quest_opener", vocabulary.field("quest", data, "opened_by"), ActorKind) or ActorKind.FATE
    opened = as_int(vocabulary.field("quest", data, "opened")) or epoch
    deadline = as_int(vocabulary.field("quest", data, "deadline")) or opened
    aim, target_kind = pair
    quest = LegendaryQuestRow(thread_id=thread_id, aim=aim, target_kind=target_kind, opened_by=opener, opened_epoch=opened, deadline_epoch=deadline, locked=[])
    if target_kind is QuestTargetKind.STAR:
        quest.target_star_id = context.ids.get(LegacyKind.STAR, target)
    elif target_kind is QuestTargetKind.ROUTE:
        quest.target_route_id = context.ids.get(LegacyKind.ROUTE, target)
    else:
        quest.target_entity_id = context.entity(target)
    context.add(quest)
    context.report.convert("legendary_quests")


async def import_threads(context: MigrationContext) -> None:
    created: list[tuple[int, ThreadRow, object, list[object]]] = []
    for row in context.source.iterate("threads", ("id",)):
        legacy_id = row.integer("id") or 0
        text = row.text("text")
        if text is None:
            context.report.place_failed("thread", f"thread:{legacy_id}", "empty text")
            continue
        epoch = max(0, row.integer("epoch") or 0)
        status = context.vocabulary.decode_as("thread_status", row.text("status"), ThreadStatus) or ThreadStatus.OPEN
        closed_epoch = row.integer("closed_epoch")
        if status is ThreadStatus.CLOSED and closed_epoch is None:
            closed_epoch = epoch
            context.report.warn(DEFAULTED, f"thread:{legacy_id}", f"closing epoch set to {epoch}")
        thread = ThreadRow(
            epoch=epoch,
            text=text,
            status=status,
            closing_text=row.text("closing_text"),
            closed_epoch=closed_epoch,
            progress=max(0, row.integer("progress") or 0),
        )
        created.append((legacy_id, thread, row.json("quest"), as_list(row.json("related"))))
    context.session.add_all([thread for _, thread, _, _ in created])
    await context.session.flush()
    links: set[tuple[int, int, ThreadLinkRole]] = set()
    for legacy_id, thread, quest, related in created:
        context.ids.put(LegacyKind.THREAD, legacy_id, thread.id)
        _quest(context, thread.id, thread.epoch, quest)
        for value in related:
            entity = context.entity(as_int(value))
            if entity is None:
                context.report.convert("thread_links_to_missing_entities")
                continue
            if (thread.id, entity, ThreadLinkRole.RELATED) not in links:
                links.add((thread.id, entity, ThreadLinkRole.RELATED))
                context.add(ThreadLinkRow(thread_id=thread.id, entity_id=entity, role=ThreadLinkRole.RELATED, epoch=thread.epoch))
    for legacy_entity, reading in context.readings.items():
        entity = context.entity(legacy_entity)
        facts = context.facts(entity)
        for legacy_thread in reading.threads:
            thread_id = context.ids.get(LegacyKind.THREAD, legacy_thread)
            if entity is None or facts is None or thread_id is None:
                context.report.place_failed("thread advance", f"entity:{legacy_entity}", f"thread {legacy_thread} is missing")
                continue
            if (thread_id, entity, ThreadLinkRole.ADVANCED) not in links:
                links.add((thread_id, entity, ThreadLinkRole.ADVANCED))
                context.add(ThreadLinkRow(thread_id=thread_id, entity_id=entity, role=ThreadLinkRole.ADVANCED, epoch=facts.birth_epoch))
                context.report.convert("thread_advances")
    await context.flush()


async def import_messages(context: MigrationContext) -> None:
    for row in context.source.iterate("messages", ("id",)):
        reference = f"message:{row.integer('id')}"
        sender = context.node(row.text("sender_kind"), row.integer("sender_id"))
        recipient = context.node(row.text("recipient_kind"), row.integer("recipient_id"))
        text = row.text("text")
        if sender is None or recipient is None or text is None:
            context.report.place_failed("message", reference, "sender, recipient or text is missing")
            continue
        raw_intent = row.text("intent")
        intent = context.vocabulary.decode_as("message_intent", raw_intent, MessageIntent)
        if intent is None:
            context.report.warn(UNKNOWN_VALUE, reference, f"intent {raw_intent!r} read as chat")
            intent = MessageIntent.CHAT
        request, wish = None, None
        raw_request = row.text("request")
        if intent is MessageIntent.PRAYER and raw_request is not None:
            request = context.vocabulary.decode_as("prayer_request", raw_request, PrayerRequest)
            if request is None:
                request, wish = PrayerRequest.WISH, raw_request
        elif raw_request is not None:
            context.report.warn(UNKNOWN_VALUE, reference, "a request on a message that is not a prayer was dropped")
        message = MessageRow(
            epoch=max(0, row.integer("epoch") or 0),
            sender_node_id=sender,
            recipient_node_id=recipient,
            intent=intent,
            text=text,
            request=request,
            wish=wish,
            is_read=row.flag("read"),
            answered=row.flag("answered"),
        )
        stamp = legacy_time(row.raw("created_at"))
        if stamp is not None:
            message.created_at = stamp
        context.add(message)
    await context.flush()


async def import_councils(context: MigrationContext) -> None:
    sons = {legacy: new for legacy in context.ids.legacy_ids(LegacyKind.SON) if (new := context.son(legacy)) is not None}
    for row in context.source.iterate("councils", ("id",)):
        topic = row.text("topic") or ""
        council = CouncilRow(
            epoch=max(0, row.integer("epoch") or 0),
            topic=topic,
            minutes=blobs.council_minutes(context.vocabulary, row.json("minutes"), topic, sons),
            passed=row.flag("passed"),
        )
        stamp = legacy_time(row.raw("created_at"))
        if stamp is not None:
            council.created_at = stamp
        context.add(council)
    await context.flush()


async def import_folk_beliefs(context: MigrationContext) -> None:
    seen: set[tuple[int, int]] = set()
    for row in context.source.iterate("folk_beliefs"):
        legacy_son = row.integer("son_id")
        people = context.entity(row.integer("people_id"))
        god = context.ids.creator() if legacy_son == CREATOR_SON_ID else context.son(legacy_son)
        account = row.text("account")
        reference = f"folk_belief:{row.integer('people_id')}-{legacy_son}"
        if people is None or god is None or account is None or (people, god) in seen:
            context.report.place_failed("folk belief", reference, "people or god missing")
            continue
        seen.add((people, god))
        context.add(
            FolkBeliefRow(
                people_entity_id=people,
                god_node_id=god,
                local_name=truncated(context.report, reference, "local name", row.text("local_name"), NAME_MAX_LENGTH),
                account=account,
                misconception=row.text("misconception"),
                epoch=max(0, row.integer("epoch") or 0),
            )
        )
    await context.flush()


async def import_network_reviews(context: MigrationContext) -> None:
    for row in context.source.iterate("network_reviews"):
        entity = context.entity(row.integer("entity_id"))
        if entity is not None:
            context.add(NetworkReviewRow(entity_id=entity, epoch=max(0, row.integer("epoch") or 0)))
    await context.flush()
