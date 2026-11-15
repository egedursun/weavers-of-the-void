from types import MappingProxyType

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import NAME_MAX_LENGTH, TITLE_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.db.tables.node import NodeRow
from aerona.db.tables.stat_columns import PassionColumns, StatColumns, passion_checks, stat_checks
from aerona.db.types import PydanticJSON
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.limits import MAX_STARS, MIN_STARS, PERCENT_MAX, PERCENT_MIN, POWER_SLOTS, RELATION_MAX, RELATION_MIN
from aerona.domain.enums.node import NodeKind
from aerona.domain.enums.rarity import Rarity
from aerona.domain.enums.son import PowerEffect, ReputationLabel, SonDeathCause, SonStatus, Stat
from aerona.domain.models.profiles import Epic, ExistenceProfile, Personality


class SonRow(StatColumns, PassionColumns, NodeRow):
    __tablename__ = "sons"
    __table_args__ = (
        *stat_checks(),
        *passion_checks(),
        between("stars", MIN_STARS, MAX_STARS),
        between("existence", PERCENT_MIN, PERCENT_MAX),
        at_least("hp", 0),
        at_least("essence", 0),
        at_least("faith", 0),
        at_least("fame", 0),
        at_least("xp", 0),
        at_least("level", 1),
        at_least("fading_epochs", 0),
        CheckConstraint("turn_rank IS NULL OR turn_rank >= 1", name="turn_rank_min"),
        at_least("sleep_epochs_left", 0),
        CheckConstraint("parent_son_id IS NULL OR parent_son_id <> id", name="not_own_parent"),
        CheckConstraint("status <> 'dead' OR death_epoch IS NOT NULL", name="dead_has_epoch"),
        CheckConstraint("domain_primary <> domain_secondary", name="distinct_domains"),
        Index("ix_sons_status", "status"),
    )
    __mapper_args__ = MappingProxyType({"polymorphic_identity": NodeKind.SON})

    id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    title: Mapped[str] = mapped_column(String(TITLE_MAX_LENGTH))
    rarity: Mapped[Rarity] = mapped_column(enum_type(Rarity, "rarity"))
    stars: Mapped[int] = mapped_column(default=MIN_STARS)
    domain_primary: Mapped[Domain] = mapped_column(enum_type(Domain, "domain_primary"))
    domain_secondary: Mapped[Domain] = mapped_column(enum_type(Domain, "domain_secondary"))
    strength: Mapped[int]
    endurance: Mapped[int]
    agility: Mapped[int]
    wisdom: Mapped[int]
    cunning: Mapped[int]
    will: Mapped[int]
    creativity: Mapped[int]
    charisma: Mapped[int]
    might: Mapped[int]
    sanity: Mapped[int | None]
    loyalty: Mapped[int]
    ambition: Mapped[int]
    wrath: Mapped[int]
    mercy: Mapped[int]
    personality: Mapped[Personality] = mapped_column(PydanticJSON(Personality))
    existence_profile: Mapped[ExistenceProfile | None] = mapped_column(PydanticJSON(ExistenceProfile))
    existence: Mapped[int]
    fading_epochs: Mapped[int] = mapped_column(default=0)
    hp: Mapped[int]
    essence: Mapped[int]
    faith: Mapped[int] = mapped_column(default=0)
    fame: Mapped[int] = mapped_column(default=0)
    xp: Mapped[int] = mapped_column(default=0)
    level: Mapped[int] = mapped_column(default=1)
    status: Mapped[SonStatus] = mapped_column(enum_type(SonStatus, "status"), default=SonStatus.ACTIVE)
    sleep_epochs_left: Mapped[int] = mapped_column(default=0)
    chained: Mapped[bool] = mapped_column(default=False)
    rebel: Mapped[bool] = mapped_column(default=False)
    outer_bargain_forbidden: Mapped[bool] = mapped_column(default=False)
    standing_order: Mapped[str | None] = mapped_column(Text)
    order_absolute: Mapped[bool] = mapped_column(default=False)
    plan: Mapped[str | None] = mapped_column(Text)
    plan_epoch: Mapped[int | None]
    epic: Mapped[Epic | None] = mapped_column(PydanticJSON(Epic))
    anchor_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL", use_alter=True))
    corpse_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL", use_alter=True))
    body_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL", use_alter=True))
    parent_son_id: Mapped[int | None] = mapped_column(ForeignKey("sons.id", ondelete="SET NULL"), index=True)
    co_parent_son_id: Mapped[int | None] = mapped_column(ForeignKey("sons.id", ondelete="SET NULL"))
    current_world_id: Mapped[int | None] = mapped_column(ForeignKey("worlds.id", ondelete="SET NULL"), index=True)
    manually_assigned_epoch: Mapped[int | None]
    birth_epoch: Mapped[int]
    death_epoch: Mapped[int | None]
    death_cause: Mapped[SonDeathCause | None] = mapped_column(enum_type(SonDeathCause, "death_cause"))
    last_acted_epoch: Mapped[int] = mapped_column(default=0)
    turn_rank: Mapped[int | None]
    reputation_love: Mapped[int | None]
    reputation_fear: Mapped[int | None]
    reputation_forgotten: Mapped[int | None]
    reputation_unanswered: Mapped[int | None]
    reputation_last_contact_epoch: Mapped[int | None]
    reputation_label: Mapped[ReputationLabel | None] = mapped_column(enum_type(ReputationLabel, "reputation_label"))
    reputation_epoch: Mapped[int | None]
    manual_love: Mapped[int] = mapped_column(default=0)
    manual_fear: Mapped[int] = mapped_column(default=0)
    manual_forgotten: Mapped[int] = mapped_column(default=0)
    trace_love: Mapped[int] = mapped_column(default=0)
    trace_fear: Mapped[int] = mapped_column(default=0)
    image_prompt: Mapped[str | None] = mapped_column(Text)

    @property
    def domains(self) -> tuple[Domain, Domain]:
        return (self.domain_primary, self.domain_secondary)

    @property
    def alive(self) -> bool:
        return self.status is not SonStatus.DEAD


class SonPowerRow(Base):
    __tablename__ = "son_powers"
    __table_args__ = (
        between("slot", 0, POWER_SLOTS - 1),
        CheckConstraint("param_entity_type IS NULL OR param_stat IS NULL", name="single_param"),
    )

    son_id: Mapped[int] = mapped_column(ForeignKey("sons.id", ondelete="CASCADE"), primary_key=True)
    slot: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH))
    description: Mapped[str] = mapped_column(Text)
    effect: Mapped[PowerEffect] = mapped_column(enum_type(PowerEffect, "effect"), index=True)
    param_entity_type: Mapped[EntityType | None] = mapped_column(enum_type(EntityType, "param_entity_type"))
    param_stat: Mapped[Stat | None] = mapped_column(enum_type(Stat, "param_stat"))


class SonRelationRow(Base):
    __tablename__ = "son_relations"
    __table_args__ = (
        CheckConstraint("son_a_id < son_b_id", name="ordered_pair"),
        between("value", RELATION_MIN, RELATION_MAX),
        UniqueConstraint("son_b_id", "son_a_id", name="uq_son_relations_reverse"),
    )

    son_a_id: Mapped[int] = mapped_column(ForeignKey("sons.id", ondelete="CASCADE"), primary_key=True)
    son_b_id: Mapped[int] = mapped_column(ForeignKey("sons.id", ondelete="CASCADE"), primary_key=True)
    value: Mapped[int] = mapped_column(default=0)
    note: Mapped[str | None] = mapped_column(Text)
