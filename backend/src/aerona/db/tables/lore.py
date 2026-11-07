from typing import Any

from sqlalchemy import JSON, CheckConstraint, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, validates

from aerona.constants.schema import (
    FACT_OBJECT_MAX_LENGTH,
    FACT_PREDICATE_MAX_LENGTH,
    KEY_MAX_LENGTH,
    LEXEME_TEXT_MAX_LENGTH,
    LEXEME_WORD_MAX_LENGTH,
    NAME_MAX_LENGTH,
    TITLE_MAX_LENGTH,
)
from aerona.db.base import Base, CreatedAtMixin
from aerona.db.columns import at_least, enum_type
from aerona.db.types import PydanticJSON
from aerona.domain.enums.agent import MessageIntent, PrayerRequest
from aerona.domain.enums.chronicle import (
    ChronicleKind,
    FeedCategory,
    LegendaryQuestKind,
    LegendaryQuestOutcome,
    PartOfSpeech,
    ThreadLinkRole,
    ThreadStatus,
)
from aerona.domain.enums.communication import DispatchContent, DispatchState, EnvoyFate, Medium
from aerona.domain.enums.node import ActorKind
from aerona.domain.models.records import CouncilMinutes


def lexeme_key(word: str) -> str:
    return " ".join(word.casefold().split())


class ChronicleRow(CreatedAtMixin, Base):
    __tablename__ = "chronicle"
    __table_args__ = (
        at_least("epoch", 1),
        CheckConstraint("year IS NULL OR year >= 0", name="year_min"),
        Index("ix_chronicle_epoch", "epoch", "id"),
        Index("ix_chronicle_son", "son_id"),
        Index("ix_chronicle_kind_epoch", "kind", "epoch"),
        Index("ix_chronicle_world_epoch", "world_id", "epoch"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    epoch: Mapped[int]
    year: Mapped[int | None]
    kind: Mapped[ChronicleKind] = mapped_column(enum_type(ChronicleKind, "kind"))
    visible: Mapped[bool] = mapped_column(default=True)
    feed_category: Mapped[FeedCategory | None] = mapped_column(enum_type(FeedCategory, "feed_category"))
    template_key: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))
    son_id: Mapped[int | None] = mapped_column(ForeignKey("sons.id", ondelete="SET NULL"))
    world_id: Mapped[int | None] = mapped_column(ForeignKey("worlds.id", ondelete="SET NULL"))
    text: Mapped[str] = mapped_column(Text)
    hidden_as_duplicate: Mapped[bool] = mapped_column(default=False)


class ChronicleEntityRow(Base):
    __tablename__ = "chronicle_entities"
    __table_args__ = (UniqueConstraint("chronicle_id", "position", name="uq_chronicle_entities_position"),)

    chronicle_id: Mapped[int] = mapped_column(ForeignKey("chronicle.id", ondelete="CASCADE"), primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True, index=True)
    position: Mapped[int]


class EpochYearCursorRow(Base):
    __tablename__ = "epoch_year_cursors"

    epoch: Mapped[int] = mapped_column(primary_key=True)
    last_year: Mapped[int]


class HistorianViewRow(CreatedAtMixin, Base):
    __tablename__ = "historian_views"
    __table_args__ = (UniqueConstraint("epoch", "people_entity_id", name="uq_historian_views_epoch_people"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    epoch: Mapped[int] = mapped_column(index=True)
    people_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    historian: Mapped[str | None] = mapped_column(String(TITLE_MAX_LENGTH))
    text: Mapped[str] = mapped_column(Text)


class FolkBeliefRow(CreatedAtMixin, Base):
    __tablename__ = "folk_beliefs"

    people_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    god_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True, index=True)
    local_name: Mapped[str | None] = mapped_column(String(NAME_MAX_LENGTH))
    account: Mapped[str] = mapped_column(Text)
    misconception: Mapped[str | None] = mapped_column(Text)
    epoch: Mapped[int]


class CanonFactRow(Base):
    __tablename__ = "canon_facts"
    __table_args__ = (
        CheckConstraint("object_entity_id IS NOT NULL OR object_text IS NOT NULL", name="has_object"),
        Index("ix_canon_facts_subject", "subject_entity_id", "active"),
        Index("ix_canon_facts_object", "object_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    predicate: Mapped[str] = mapped_column(String(FACT_PREDICATE_MAX_LENGTH))
    object_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    object_text: Mapped[str | None] = mapped_column(String(FACT_OBJECT_MAX_LENGTH))
    epoch: Mapped[int]
    source_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    deterministic: Mapped[bool] = mapped_column(default=False)
    active: Mapped[bool] = mapped_column(default=True)


class ThreadRow(CreatedAtMixin, Base):
    __tablename__ = "threads"
    __table_args__ = (
        at_least("progress", 0),
        CheckConstraint("status <> 'closed' OR closed_epoch IS NOT NULL", name="closed_has_epoch"),
        Index("ix_threads_status", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    epoch: Mapped[int]
    text: Mapped[str] = mapped_column(Text)
    status: Mapped[ThreadStatus] = mapped_column(enum_type(ThreadStatus, "status"), default=ThreadStatus.OPEN)
    closing_text: Mapped[str | None] = mapped_column(Text)
    closed_epoch: Mapped[int | None]
    progress: Mapped[int] = mapped_column(default=0)


class ThreadLinkRow(Base):
    __tablename__ = "thread_links"

    thread_id: Mapped[int] = mapped_column(ForeignKey("threads.id", ondelete="CASCADE"), primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True, index=True)
    role: Mapped[ThreadLinkRole] = mapped_column(enum_type(ThreadLinkRole, "role"), primary_key=True)
    epoch: Mapped[int]


class LegendaryQuestRow(Base):
    __tablename__ = "legendary_quests"

    thread_id: Mapped[int] = mapped_column(ForeignKey("threads.id", ondelete="CASCADE"), primary_key=True)
    kind: Mapped[LegendaryQuestKind] = mapped_column(enum_type(LegendaryQuestKind, "kind"))
    target_star_id: Mapped[int | None] = mapped_column(ForeignKey("stars.id", ondelete="SET NULL"))
    target_route_id: Mapped[int | None] = mapped_column(ForeignKey("routes.id", ondelete="SET NULL"))
    target_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    opened_by: Mapped[ActorKind] = mapped_column(enum_type(ActorKind, "opened_by"))
    opened_epoch: Mapped[int]
    deadline_epoch: Mapped[int]
    prior_journey_ids: Mapped[list[int]] = mapped_column(PydanticJSON(list[int]), default=list)
    outcome: Mapped[LegendaryQuestOutcome | None] = mapped_column(enum_type(LegendaryQuestOutcome, "outcome"))


class LexemeRow(CreatedAtMixin, Base):
    __tablename__ = "lexemes"
    __table_args__ = (UniqueConstraint("language_entity_id", "word_key", name="uq_lexemes_language_word"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    language_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    word: Mapped[str] = mapped_column(String(LEXEME_WORD_MAX_LENGTH))
    word_key: Mapped[str] = mapped_column(String(LEXEME_WORD_MAX_LENGTH))
    meaning: Mapped[str] = mapped_column(String(LEXEME_TEXT_MAX_LENGTH))
    part_of_speech: Mapped[PartOfSpeech | None] = mapped_column(enum_type(PartOfSpeech, "part_of_speech"))
    etymology: Mapped[str | None] = mapped_column(String(LEXEME_TEXT_MAX_LENGTH))
    example: Mapped[str | None] = mapped_column(String(LEXEME_TEXT_MAX_LENGTH))
    added_by_kind: Mapped[ActorKind] = mapped_column(enum_type(ActorKind, "added_by_kind"))
    added_by_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    epoch: Mapped[int]

    @validates("word")
    def _sync_word_key(self, _key: str, value: str) -> str:
        self.word_key = lexeme_key(value)
        return value


class CouncilRow(CreatedAtMixin, Base):
    __tablename__ = "councils"

    id: Mapped[int] = mapped_column(primary_key=True)
    epoch: Mapped[int] = mapped_column(index=True)
    topic: Mapped[str] = mapped_column(Text)
    minutes: Mapped[CouncilMinutes] = mapped_column(PydanticJSON(CouncilMinutes))
    passed: Mapped[bool] = mapped_column(default=False)


class MessageRow(CreatedAtMixin, Base):
    __tablename__ = "messages"
    __table_args__ = (
        Index("ix_messages_recipient", "recipient_node_id", "answered"),
        Index("ix_messages_sender", "sender_node_id", "epoch"),
        CheckConstraint("request IS NULL OR intent = 'prayer'", name="request_on_prayer"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    epoch: Mapped[int]
    sender_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    recipient_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    intent: Mapped[MessageIntent] = mapped_column(enum_type(MessageIntent, "intent"))
    text: Mapped[str] = mapped_column(Text)
    request: Mapped[PrayerRequest | None] = mapped_column(enum_type(PrayerRequest, "request"))
    wish: Mapped[str | None] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(default=False)
    answered: Mapped[bool] = mapped_column(default=False)
    answered_epoch: Mapped[int | None]
    answer_essence: Mapped[int | None]
    medium: Mapped[Medium | None] = mapped_column(enum_type(Medium, "medium"))
    content: Mapped[DispatchContent | None] = mapped_column(enum_type(DispatchContent, "content"))
    state: Mapped[DispatchState | None] = mapped_column(enum_type(DispatchState, "state"))
    language_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    envoy_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    envoy_fate: Mapped[EnvoyFate | None] = mapped_column(enum_type(EnvoyFate, "envoy_fate"))
    intercepted_by_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    arrival_epoch: Mapped[int | None]
    forged: Mapped[bool] = mapped_column(default=False)
    misread: Mapped[bool] = mapped_column(default=False)
    enciphered: Mapped[bool] = mapped_column(default=False)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)

    @validates("intent")
    def _dreams_travel_by_dream(self, _key: str, value: MessageIntent) -> MessageIntent:
        if value is MessageIntent.DREAM:
            self.medium = Medium.DREAM
        return value


class FateRewardRow(CreatedAtMixin, Base):
    __tablename__ = "fate_rewards"
    __table_args__ = (at_least("fame", 0), Index("ix_fate_rewards_son_epoch", "son_id", "epoch"))

    id: Mapped[int] = mapped_column(primary_key=True)
    son_id: Mapped[int] = mapped_column(ForeignKey("sons.id", ondelete="CASCADE"))
    epoch: Mapped[int]
    fame: Mapped[int]
    xp: Mapped[int]
    reason: Mapped[str | None] = mapped_column(Text)
