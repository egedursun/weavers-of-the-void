from types import MappingProxyType

from sqlalchemy import CheckConstraint, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import NAME_MAX_LENGTH, TITLE_MAX_LENGTH
from aerona.db.base import Base, CreatedAtMixin
from aerona.db.columns import at_least, between, enum_type
from aerona.db.tables.node import NodeRow
from aerona.db.tables.stat_columns import StatColumns, stat_checks
from aerona.db.types import PydanticJSON
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.foreign_god import ForeignGodPowerEffect, ForeignGodStatus
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN, RELATION_MAX, RELATION_MIN
from aerona.domain.enums.node import NodeKind
from aerona.domain.enums.war import GodConflictOutcome
from aerona.domain.models.profiles import ExistenceProfile, GodDepth, Personality


class ForeignGodRow(StatColumns, NodeRow):
    __tablename__ = "foreign_gods"
    __table_args__ = (
        *stat_checks(),
        between("power", PERCENT_MIN, PERCENT_MAX),
        between("stance", RELATION_MIN, RELATION_MAX),
        at_least("faith", 0),
        at_least("awakening_pressure", 0),
        CheckConstraint("status <> 'dead' OR death_epoch IS NOT NULL", name="dead_has_epoch"),
        Index("ix_foreign_gods_world_status", "world_id", "status"),
    )
    __mapper_args__ = MappingProxyType({"polymorphic_identity": NodeKind.FOREIGN_GOD})

    id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    title: Mapped[str | None] = mapped_column(String(TITLE_MAX_LENGTH))
    domain_primary: Mapped[Domain] = mapped_column(enum_type(Domain, "domain_primary"))
    domain_secondary: Mapped[Domain | None] = mapped_column(enum_type(Domain, "domain_secondary"))
    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"))
    power: Mapped[int]
    faith: Mapped[int] = mapped_column(default=0)
    stance: Mapped[int] = mapped_column(default=0)
    status: Mapped[ForeignGodStatus] = mapped_column(enum_type(ForeignGodStatus, "status"), default=ForeignGodStatus.AWAKE)
    contacted: Mapped[bool] = mapped_column(default=False)
    description: Mapped[str | None] = mapped_column(Text)
    image_prompt: Mapped[str | None] = mapped_column(Text)
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
    personality: Mapped[Personality | None] = mapped_column(PydanticJSON(Personality))
    existence_profile: Mapped[ExistenceProfile | None] = mapped_column(PydanticJSON(ExistenceProfile))
    depth: Mapped[GodDepth | None] = mapped_column(PydanticJSON(GodDepth))
    awakening_pressure: Mapped[int] = mapped_column(default=0)
    awakening_average: Mapped[float | None] = mapped_column(Float)
    created_epoch: Mapped[int]
    defeated_epoch: Mapped[int | None]
    death_epoch: Mapped[int | None]


class ForeignGodPowerRow(Base):
    __tablename__ = "foreign_god_powers"

    god_id: Mapped[int] = mapped_column(ForeignKey("foreign_gods.id", ondelete="CASCADE"), primary_key=True)
    slot: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH))
    effect: Mapped[ForeignGodPowerEffect] = mapped_column(enum_type(ForeignGodPowerEffect, "effect"))
    description: Mapped[str] = mapped_column(Text)


class GodConflictRow(CreatedAtMixin, Base):
    __tablename__ = "god_conflicts"
    __table_args__ = (CheckConstraint("attacker_node_id <> defender_node_id", name="distinct_sides"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    epoch: Mapped[int] = mapped_column(index=True)
    attacker_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), index=True)
    defender_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), index=True)
    outcome: Mapped[GodConflictOutcome] = mapped_column(enum_type(GodConflictOutcome, "outcome"))
    attacker_score: Mapped[int]
    defender_score: Mapped[int]
    duel: Mapped[bool] = mapped_column(default=False)


class OuterBargainRow(CreatedAtMixin, Base):
    __tablename__ = "outer_bargains"

    outer_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    son_id: Mapped[int] = mapped_column(ForeignKey("sons.id", ondelete="CASCADE"), primary_key=True)
    epoch: Mapped[int]
    terms: Mapped[str | None] = mapped_column(Text)
