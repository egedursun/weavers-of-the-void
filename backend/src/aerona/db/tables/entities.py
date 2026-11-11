from types import MappingProxyType

from sqlalchemy import CheckConstraint, Float, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import KEY_MAX_LENGTH, PRIVATE_NOTE_MAX_LENGTH, SUBTYPE_MAX_LENGTH, TITLE_MAX_LENGTH
from aerona.db.base import Base, CreatedAtMixin
from aerona.db.columns import at_least, enum_type, max_length, nullable_between
from aerona.db.tables.node import NodeRow
from aerona.db.types import PydanticJSON
from aerona.domain.enums.agent import Verdict
from aerona.domain.enums.chronicle import WritingSystem
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import (
    ArchiveOverride,
    CivilizationTier,
    EngineKind,
    EntityFlag,
    EntityOrigin,
    EntityStatus,
    EntityType,
    LegendCategory,
    MortalRole,
    ProphecyReading,
)
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.node import NodeKind
from aerona.domain.enums.society import CreatureTrait, KnowledgeBranch, NaturalLaw, ResourceMechanic, SocialClass
from aerona.domain.enums.tongues import LanguageModality, LanguageStage
from aerona.domain.models.entity_stats import EntityStats
from aerona.domain.models.phonology import LanguageSignature, Phonology
from aerona.domain.models.profiles import EntityDepth

CIVILIZATION_TIER_MAX = max(CivilizationTier)


class EntityRow(NodeRow):
    __tablename__ = "entities"
    __table_args__ = (
        at_least("power_level", 1),
        at_least("last_acted_epoch", 0),
        at_least("fold_count", 0),
        nullable_between("sanity", PERCENT_MIN, PERCENT_MAX),
        nullable_between("civ_tier", CivilizationTier.TRIBE, CIVILIZATION_TIER_MAX),
        nullable_between("civ_tier_previous", CivilizationTier.TRIBE, CIVILIZATION_TIER_MAX),
        max_length("private_note", PRIVATE_NOTE_MAX_LENGTH),
        CheckConstraint("location_id IS NULL OR location_id <> id", name="not_own_location"),
        CheckConstraint("maker_entity_id IS NULL OR maker_entity_id <> id", name="not_own_maker"),
        CheckConstraint("status NOT IN ('dead', 'destroyed') OR end_epoch IS NOT NULL", name="ended_has_epoch"),
        CheckConstraint("knowledge_branch IS NULL OR entity_type = 'knowledge'", name="branch_on_knowledge"),
        CheckConstraint("natural_law IS NULL OR entity_type = 'natural_law'", name="law_on_natural_law"),
        CheckConstraint("resource_mechanic IS NULL OR entity_type = 'resource'", name="mechanic_on_resource"),
        CheckConstraint("prophecy_reading IS NULL OR entity_type = 'prophecy'", name="reading_on_prophecy"),
        CheckConstraint("legend_category IS NULL OR entity_type = 'legend'", name="category_on_legend"),
        CheckConstraint("mortal_role IS NULL OR entity_type = 'mortal'", name="role_on_mortal"),
        CheckConstraint("death_event_entity_id IS NULL OR entity_type = 'mortal'", name="death_event_on_mortal"),
        CheckConstraint("sacred_to_son_id IS NULL OR resource_mechanic = 'sacred'", name="sacred_owner_on_sacred"),
        CheckConstraint("origin <> 'mortal' OR maker_entity_id IS NOT NULL", name="mortal_origin_has_maker"),
        Index("ix_entities_type_status", "entity_type", "status"),
        Index("ix_entities_world_type_status", "world_id", "entity_type", "status"),
        Index("ix_entities_engine_kind_status", "engine_kind", "status"),
        Index("ix_entities_pending", "pending_name", sqlite_where=text("pending_name = 1")),
    )
    __mapper_args__ = MappingProxyType({"polymorphic_identity": NodeKind.ENTITY})

    id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    title: Mapped[str | None] = mapped_column(String(TITLE_MAX_LENGTH))
    entity_type: Mapped[EntityType] = mapped_column(enum_type(EntityType, "entity_type"))
    subtype: Mapped[str | None] = mapped_column(String(SUBTYPE_MAX_LENGTH))
    engine_kind: Mapped[EngineKind | None] = mapped_column(enum_type(EngineKind, "engine_kind"))
    mortal_role: Mapped[MortalRole | None] = mapped_column(enum_type(MortalRole, "mortal_role"))
    description: Mapped[str] = mapped_column(Text)
    stats: Mapped[EntityStats] = mapped_column(PydanticJSON(EntityStats))
    power_level: Mapped[int]
    domain: Mapped[Domain | None] = mapped_column(enum_type(Domain, "domain"))
    origin: Mapped[EntityOrigin] = mapped_column(enum_type(EntityOrigin, "origin"))
    creator_son_id: Mapped[int | None] = mapped_column(ForeignKey("sons.id", ondelete="SET NULL"), index=True)
    maker_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"), index=True)
    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="RESTRICT"), index=True)
    location_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"), index=True)
    status: Mapped[EntityStatus] = mapped_column(enum_type(EntityStatus, "status"), default=EntityStatus.CANON)
    pending_name: Mapped[bool] = mapped_column(default=False)
    naming_attempts: Mapped[int] = mapped_column(default=0)
    fate_note: Mapped[str | None] = mapped_column(Text)
    depth: Mapped[EntityDepth | None] = mapped_column(PydanticJSON(EntityDepth))
    birth_epoch: Mapped[int]
    end_epoch: Mapped[int | None]
    last_acted_epoch: Mapped[int] = mapped_column(default=0)
    importance: Mapped[int | None] = mapped_column(index=True)
    archive_override: Mapped[ArchiveOverride | None] = mapped_column(enum_type(ArchiveOverride, "archive_override"))
    favorite: Mapped[bool] = mapped_column(default=False)
    private_note: Mapped[str | None] = mapped_column(Text)
    map_x: Mapped[float | None] = mapped_column(Float)
    map_y: Mapped[float | None] = mapped_column(Float)
    image_prompt: Mapped[str | None] = mapped_column(Text)
    civ_tier: Mapped[int | None]
    civ_tier_epoch: Mapped[int | None]
    civ_tier_previous: Mapped[int | None]
    sanity: Mapped[int | None]
    knowledge_branch: Mapped[KnowledgeBranch | None] = mapped_column(enum_type(KnowledgeBranch, "knowledge_branch"))
    natural_law: Mapped[NaturalLaw | None] = mapped_column(enum_type(NaturalLaw, "natural_law"))
    resource_mechanic: Mapped[ResourceMechanic | None] = mapped_column(enum_type(ResourceMechanic, "resource_mechanic"))
    sacred_to_son_id: Mapped[int | None] = mapped_column(ForeignKey("sons.id", ondelete="SET NULL"))
    prophecy_reading: Mapped[ProphecyReading | None] = mapped_column(enum_type(ProphecyReading, "prophecy_reading"))
    legend_category: Mapped[LegendCategory | None] = mapped_column(enum_type(LegendCategory, "legend_category"))
    social_class: Mapped[SocialClass | None] = mapped_column(enum_type(SocialClass, "social_class"))
    affiliated_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    death_event_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    is_underworld: Mapped[bool] = mapped_column(default=False)
    is_water: Mapped[bool] = mapped_column(default=False)
    fold_count: Mapped[int] = mapped_column(default=0)

    @property
    def living(self) -> bool:
        return self.status is EntityStatus.CANON


class EntityTagRow(Base):
    __tablename__ = "entity_tags"

    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    tag: Mapped[str] = mapped_column(String(KEY_MAX_LENGTH), primary_key=True, index=True)


class EntityFlagRow(Base):
    __tablename__ = "entity_flags"
    __table_args__ = (Index("ix_entity_flags_flag", "flag"),)

    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    flag: Mapped[EntityFlag] = mapped_column(enum_type(EntityFlag, "flag"), primary_key=True)
    epoch: Mapped[int | None]


class EntityTraitRow(Base):
    __tablename__ = "entity_traits"
    __table_args__ = (Index("ix_entity_traits_trait", "trait"),)

    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    trait: Mapped[CreatureTrait] = mapped_column(enum_type(CreatureTrait, "trait"), primary_key=True)


class LanguageProfileRow(Base):
    __tablename__ = "language_profiles"

    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    phonology: Mapped[Phonology] = mapped_column(PydanticJSON(Phonology))
    writing_system: Mapped[WritingSystem | None] = mapped_column(enum_type(WritingSystem, "writing_system"))
    script_epoch: Mapped[int | None]
    parent_language_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    seed: Mapped[str] = mapped_column(String(KEY_MAX_LENGTH))
    signature: Mapped[LanguageSignature | None] = mapped_column(PydanticJSON(LanguageSignature))
    alphabet: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))
    script_id: Mapped[int | None] = mapped_column(ForeignKey("scripts.id", ondelete="SET NULL"))
    modality: Mapped[LanguageModality] = mapped_column(enum_type(LanguageModality, "modality"), default=LanguageModality.VOCAL, server_default="vocal")
    stage: Mapped[LanguageStage] = mapped_column(enum_type(LanguageStage, "stage"), default=LanguageStage.NATURAL, server_default="natural")


class CreationVerdictRow(CreatedAtMixin, Base):
    __tablename__ = "creation_verdicts"
    __table_args__ = (Index("ix_creation_verdicts_epoch_verdict", "epoch", "verdict"),)

    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    epoch: Mapped[int]
    verdict: Mapped[Verdict] = mapped_column(enum_type(Verdict, "verdict"), default=Verdict.UNJUDGED)
    rationale: Mapped[str | None] = mapped_column(Text)
    judged_epoch: Mapped[int | None]


class CreationMotifRow(Base):
    __tablename__ = "creation_motifs"
    __table_args__ = (Index("ix_creation_motifs_motif_epoch", "motif", "epoch"),)

    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    motif: Mapped[str] = mapped_column(String(KEY_MAX_LENGTH), primary_key=True)
    world_id: Mapped[int | None] = mapped_column(ForeignKey("worlds.id", ondelete="SET NULL"))
    epoch: Mapped[int]


class NetworkReviewRow(Base):
    __tablename__ = "network_reviews"

    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    epoch: Mapped[int]
