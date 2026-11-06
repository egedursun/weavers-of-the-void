from sqlalchemy import JSON, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import KEY_MAX_LENGTH
from aerona.db.base import Base, CreatedAtMixin
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN, RELATION_MAX, RELATION_MIN
from aerona.domain.enums.mind import (
    ActKind,
    Attribute,
    DreamKind,
    DreamReading,
    Emotion,
    EthicalStance,
    Facet,
    GriefStage,
    HonourModel,
    IdeaKind,
    IdeaSource,
    IdeaState,
    MemoryKind,
    NeedKind,
    PreferenceKind,
    PressureKind,
    SkillKind,
    SkillSource,
    ThoughtKind,
    TraitKind,
    TraitSource,
    ValueAxis,
    ValueHolder,
)

VALUE_MIN = -100
VALUE_MAX = 100
SKILL_MIN = 0
SKILL_MAX = 100
ATTRIBUTE_MIN = 0
ATTRIBUTE_MAX = 100
FACET_MIN = -50
FACET_MAX = 50
MIND_LOCKS = (
    "values",
    "traits",
    "skills",
    "memories",
    "needs",
    "role",
    "attributes",
    "facets",
    "ideas",
    "thoughts",
    "griefs",
    "dreams",
    "preferences",
    "ethics",
)


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
    variant_id: Mapped[int | None] = mapped_column(ForeignKey("kind_variants.id", ondelete="SET NULL"))


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
    variant_id: Mapped[int | None] = mapped_column(ForeignKey("kind_variants.id", ondelete="SET NULL"))


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


class AttributeRow(Base):
    __tablename__ = "mind_attributes"
    __table_args__ = (between("value", ATTRIBUTE_MIN, ATTRIBUTE_MAX),)

    node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    attribute: Mapped[Attribute] = mapped_column(enum_type(Attribute, "attribute"), primary_key=True)
    value: Mapped[int]


class FacetRow(Base):
    __tablename__ = "mind_facets"
    __table_args__ = (between("value", FACET_MIN, FACET_MAX),)

    node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    facet: Mapped[Facet] = mapped_column(enum_type(Facet, "facet"), primary_key=True)
    value: Mapped[int]


class IdeaRow(Base):
    __tablename__ = "incubating_ideas"
    __table_args__ = (
        between("progress", PERCENT_MIN, PERCENT_MAX),
        at_least("started_epoch", 0),
        UniqueConstraint("holder_node_id", "idea", name="uq_incubating_ideas_holder_idea"),
        Index("ix_incubating_ideas_state", "state"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    holder_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    idea: Mapped[IdeaKind] = mapped_column(enum_type(IdeaKind, "idea"))
    source: Mapped[IdeaSource] = mapped_column(enum_type(IdeaSource, "source"))
    source_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    progress: Mapped[int] = mapped_column(default=0)
    state: Mapped[IdeaState] = mapped_column(enum_type(IdeaState, "state"))
    started_epoch: Mapped[int]
    finished_epoch: Mapped[int | None]


class ThoughtRow(Base):
    __tablename__ = "thoughts"
    __table_args__ = (
        between("intensity", PERCENT_MIN, PERCENT_MAX),
        between("decay_pct", PERCENT_MIN, PERCENT_MAX),
        at_least("epoch", 0),
        Index("ix_thoughts_holder", "holder_node_id", "epoch"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    holder_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    kind: Mapped[ThoughtKind] = mapped_column(enum_type(ThoughtKind, "kind"))
    emotion: Mapped[Emotion] = mapped_column(enum_type(Emotion, "emotion"))
    subject_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    intensity: Mapped[int]
    epoch: Mapped[int]
    decay_pct: Mapped[int]
    memory_id: Mapped[int | None] = mapped_column(ForeignKey("memories.id", ondelete="SET NULL"))


class GriefRow(Base):
    __tablename__ = "griefs"
    __table_args__ = (
        between("strength", PERCENT_MIN, PERCENT_MAX),
        at_least("started_epoch", 0),
        at_least("length_epochs", 1),
        UniqueConstraint("mourner_node_id", "deceased_node_id", name="uq_griefs_mourner_deceased"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    mourner_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    deceased_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    stage: Mapped[GriefStage] = mapped_column(enum_type(GriefStage, "stage"))
    strength: Mapped[int]
    started_epoch: Mapped[int]
    stage_epoch: Mapped[int]
    length_epochs: Mapped[int]


class DreamRow(Base):
    __tablename__ = "dreams"
    __table_args__ = (between("intensity", PERCENT_MIN, PERCENT_MAX), at_least("epoch", 0), Index("ix_dreams_dreamer", "dreamer_node_id", "epoch"))

    id: Mapped[int] = mapped_column(primary_key=True)
    dreamer_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    kind: Mapped[DreamKind] = mapped_column(enum_type(DreamKind, "kind"))
    epoch: Mapped[int]
    intensity: Mapped[int]
    content: Mapped[list[int]] = mapped_column(JSON, default=list)
    thought_id: Mapped[int | None] = mapped_column(ForeignKey("thoughts.id", ondelete="SET NULL"))
    sender_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    partner_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    world_id: Mapped[int | None] = mapped_column(ForeignKey("worlds.id", ondelete="SET NULL"))
    message_id: Mapped[int | None] = mapped_column(ForeignKey("messages.id", ondelete="SET NULL"))
    reading: Mapped[DreamReading] = mapped_column(enum_type(DreamReading, "reading"), default=DreamReading.UNREAD)
    reader_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    reading_true: Mapped[bool | None]
    recurring: Mapped[bool] = mapped_column(default=False)


class PreferenceRow(Base):
    __tablename__ = "preferences"
    __table_args__ = (
        between("strength", RELATION_MIN, RELATION_MAX),
        UniqueConstraint("holder_node_id", "kind", "target", name="uq_preferences_holder_kind_target"),
        Index("ix_preferences_holder", "holder_node_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    holder_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    kind: Mapped[PreferenceKind] = mapped_column(enum_type(PreferenceKind, "kind"))
    target: Mapped[str] = mapped_column(String(KEY_MAX_LENGTH))
    target_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    strength: Mapped[int]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class CultureEthicRow(Base):
    __tablename__ = "culture_ethics"
    __table_args__ = (at_least("since_epoch", 0),)

    holder_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    act: Mapped[ActKind] = mapped_column(enum_type(ActKind, "act"), primary_key=True)
    stance: Mapped[EthicalStance] = mapped_column(enum_type(EthicalStance, "stance"))
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class CultureHonourRow(Base):
    __tablename__ = "culture_honour"

    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    model: Mapped[HonourModel] = mapped_column(enum_type(HonourModel, "model"))
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
