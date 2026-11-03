from sqlalchemy import JSON, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import KEY_MAX_LENGTH
from aerona.db.base import Base, CreatedAtMixin
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN, RELATION_MAX, RELATION_MIN
from aerona.domain.enums.mind import (
    MemoryKind,
    NeedKind,
    PressureKind,
    SkillKind,
    SkillSource,
    TraitKind,
    TraitSource,
    ValueAxis,
    ValueHolder,
)

VALUE_MIN = -100
VALUE_MAX = 100
SKILL_MIN = 0
SKILL_MAX = 100
MIND_LOCKS = ("values", "traits", "skills", "memories", "needs", "role")


class MindRow(Base):
    __tablename__ = "minds"
    __table_args__ = (at_least("updated_epoch", 0),)

    node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    holder: Mapped[ValueHolder] = mapped_column(enum_type(ValueHolder, "holder"))
    updated_epoch: Mapped[int] = mapped_column(default=0)
    career_ended_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class CultureValueRow(Base):
    __tablename__ = "culture_values"
    __table_args__ = (between("value", VALUE_MIN, VALUE_MAX),)

    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    axis: Mapped[ValueAxis] = mapped_column(enum_type(ValueAxis, "axis"), primary_key=True)
    value: Mapped[int]


class PersonalityValueRow(Base):
    __tablename__ = "personality_values"
    __table_args__ = (between("value", VALUE_MIN, VALUE_MAX),)

    node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    axis: Mapped[ValueAxis] = mapped_column(enum_type(ValueAxis, "axis"), primary_key=True)
    value: Mapped[int]


class TraitRow(Base):
    __tablename__ = "traits"
    __table_args__ = (at_least("epoch", 0), Index("ix_traits_trait", "trait"))

    node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    trait: Mapped[TraitKind] = mapped_column(enum_type(TraitKind, "trait"), primary_key=True)
    source: Mapped[TraitSource] = mapped_column(enum_type(TraitSource, "source"))
    epoch: Mapped[int]
    source_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))


class SkillRow(Base):
    __tablename__ = "skills"
    __table_args__ = (
        between("level", SKILL_MIN, SKILL_MAX),
        between("peak", SKILL_MIN, SKILL_MAX),
        at_least("xp", 0),
        UniqueConstraint("holder_node_id", "skill", "subject_node_id", name="uq_skills_holder_skill_subject"),
        Index("ix_skills_skill_level", "skill", "level"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    holder_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    skill: Mapped[SkillKind] = mapped_column(enum_type(SkillKind, "skill"))
    subject_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    level: Mapped[int]
    xp: Mapped[int] = mapped_column(default=0)
    peak: Mapped[int]
    last_used_epoch: Mapped[int]
    source: Mapped[SkillSource] = mapped_column(enum_type(SkillSource, "source"))


class MemoryRow(CreatedAtMixin, Base):
    __tablename__ = "memories"
    __table_args__ = (
        between("magnitude", RELATION_MIN, RELATION_MAX),
        between("decay_pct", PERCENT_MIN, PERCENT_MAX),
        at_least("epoch", 0),
        Index("ix_memories_holder_subject", "holder_node_id", "subject_node_id"),
        Index("ix_memories_subject", "subject_node_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    holder_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    subject_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    kind: Mapped[MemoryKind] = mapped_column(enum_type(MemoryKind, "kind"))
    magnitude: Mapped[int]
    decay_pct: Mapped[int]
    epoch: Mapped[int]
    note: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))
    event_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    incident_id: Mapped[int | None] = mapped_column(ForeignKey("incidents.id", ondelete="SET NULL"))
    inherited_from_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))


class NeedRow(Base):
    __tablename__ = "needs"
    __table_args__ = (between("value", PERCENT_MIN, PERCENT_MAX),)

    node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    need: Mapped[NeedKind] = mapped_column(enum_type(NeedKind, "need"), primary_key=True)
    value: Mapped[int]


class PressureRow(Base):
    __tablename__ = "pressures"
    __table_args__ = (between("value", PERCENT_MIN, PERCENT_MAX),)

    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    pressure: Mapped[PressureKind] = mapped_column(enum_type(PressureKind, "pressure"), primary_key=True)
    value: Mapped[int]
