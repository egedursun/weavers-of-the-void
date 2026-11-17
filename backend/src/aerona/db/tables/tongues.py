from sqlalchemy import JSON, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import KEY_MAX_LENGTH, NAME_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.chronicle import WritingSystem
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.tongues import (
    LanguagePolicy,
    MorphologyType,
    NumberSystem,
    ScriptChangeCause,
    SenseShift,
    SoundChangeCause,
    SoundChangeKind,
    SoundEnvironment,
    WordOrder,
)

SOUND_CHANGE_FIELDS = ("kind", "source", "target", "environment", "cause", "position", "epoch")
GRAMMAR_FIELDS = ("word_order", "morphology", "cases", "noun_classes", "evidentiality", "honorific_levels", "number_system")
SCRIPT_FIELDS = ("name", "system", "parent_script_id", "origin_language_id", "signs", "cause", "epoch")
DECIPHER_FIELDS = ("progress", "corpus", "bilingual", "errors", "scholar_entity_id", "started_epoch")
POLICY_FIELDS = ("strength",)
DIVINE_TONGUE_FIELDS = ("language_entity_id",)


class SoundChangeRow(Base):
    __tablename__ = "sound_changes"
    __table_args__ = (at_least("epoch", 0), at_least("position", 0), Index("ix_sound_changes_language", "language_entity_id", "position"))

    id: Mapped[int] = mapped_column(primary_key=True)
    language_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    kind: Mapped[SoundChangeKind] = mapped_column(enum_type(SoundChangeKind, "kind"))
    source: Mapped[str] = mapped_column(String(KEY_MAX_LENGTH))
    target: Mapped[str] = mapped_column(String(KEY_MAX_LENGTH), default="")
    environment: Mapped[SoundEnvironment] = mapped_column(enum_type(SoundEnvironment, "environment"), default=SoundEnvironment.ANYWHERE)
    cause: Mapped[SoundChangeCause] = mapped_column(enum_type(SoundChangeCause, "cause"), default=SoundChangeCause.DRIFT)
    position: Mapped[int] = mapped_column(default=0)
    epoch: Mapped[int] = mapped_column(default=0)
    incident_id: Mapped[int | None] = mapped_column(ForeignKey("incidents.id", ondelete="SET NULL"), index=True)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class LanguageGrammarRow(Base):
    __tablename__ = "language_grammar"
    __table_args__ = (
        between("cases", 0, 20),
        between("noun_classes", 0, 20),
        between("honorific_levels", 0, 6),
        at_least("updated_epoch", 0),
    )

    language_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    word_order: Mapped[WordOrder] = mapped_column(enum_type(WordOrder, "word_order"), default=WordOrder.SOV)
    morphology: Mapped[MorphologyType] = mapped_column(enum_type(MorphologyType, "morphology"), default=MorphologyType.AGGLUTINATIVE)
    cases: Mapped[int] = mapped_column(default=0)
    noun_classes: Mapped[int] = mapped_column(default=0)
    evidentiality: Mapped[bool] = mapped_column(default=False)
    honorific_levels: Mapped[int] = mapped_column(default=0)
    number_system: Mapped[NumberSystem] = mapped_column(enum_type(NumberSystem, "number_system"), default=NumberSystem.SINGULAR_PLURAL)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class MeaningShiftRow(Base):
    __tablename__ = "meaning_shifts"
    __table_args__ = (at_least("epoch", 0), Index("ix_meaning_shifts_lexeme", "lexeme_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    lexeme_id: Mapped[int] = mapped_column(ForeignKey("lexemes.id", ondelete="CASCADE"))
    shift: Mapped[SenseShift] = mapped_column(enum_type(SenseShift, "shift"))
    old_meaning: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH), default="")
    new_meaning: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH), default="")
    replaced_by_id: Mapped[int | None] = mapped_column(ForeignKey("lexemes.id", ondelete="SET NULL"))
    cause_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    epoch: Mapped[int] = mapped_column(default=0)


class ScriptRow(Base):
    __tablename__ = "scripts"
    __table_args__ = (at_least("signs", 0), at_least("epoch", 0), Index("ix_scripts_parent", "parent_script_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH))
    system: Mapped[WritingSystem] = mapped_column(enum_type(WritingSystem, "system"))
    parent_script_id: Mapped[int | None] = mapped_column(ForeignKey("scripts.id", ondelete="SET NULL"))
    origin_language_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    signs: Mapped[int] = mapped_column(default=0)
    cause: Mapped[ScriptChangeCause] = mapped_column(enum_type(ScriptChangeCause, "cause"), default=ScriptChangeCause.INVENTION)
    epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class DecipherWorkRow(Base):
    __tablename__ = "decipher_works"
    __table_args__ = (between("progress", PERCENT_MIN, PERCENT_MAX), at_least("corpus", 0), at_least("errors", 0), at_least("started_epoch", 0))

    language_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    progress: Mapped[int] = mapped_column(default=0)
    corpus: Mapped[int] = mapped_column(default=0)
    bilingual: Mapped[bool] = mapped_column(default=False)
    errors: Mapped[int] = mapped_column(default=0)
    scholar_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    started_epoch: Mapped[int] = mapped_column(default=0)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class LanguagePolicyRow(Base):
    __tablename__ = "language_policies"
    __table_args__ = (between("strength", PERCENT_MIN, PERCENT_MAX), at_least("since_epoch", 0), Index("ix_language_policies_language", "language_entity_id"))

    holder_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    language_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    policy: Mapped[LanguagePolicy] = mapped_column(enum_type(LanguagePolicy, "policy"), primary_key=True)
    strength: Mapped[int] = mapped_column(default=50)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class DivineTongueRow(Base):
    __tablename__ = "divine_tongues"
    __table_args__ = (at_least("since_epoch", 0),)

    god_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    language_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), unique=True)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
