from sqlalchemy import JSON, CheckConstraint, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import NAME_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import between, enum_type
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.mind import RelationComponent
from aerona.domain.enums.regime import SelectorateKind
from aerona.domain.enums.travel import EncounterEffect, RouteEnvironment

COMPONENT_FIELDS = ("value",)
CONSTITUTION_FIELDS = ("ideology_entity_id", "selectorate", "offices", "rights")
ENCOUNTER_FIELDS = ("environment", "effect", "name", "weight", "loss_pct")


class RelationComponentRow(Base):
    __tablename__ = "relation_components"
    __table_args__ = (
        CheckConstraint("entity_a_id < entity_b_id", name="ordered_pair"),
        CheckConstraint("value BETWEEN -100 AND 100", name="value_range"),
        Index("ix_relation_components_b", "entity_b_id"),
    )

    entity_a_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    entity_b_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    component: Mapped[RelationComponent] = mapped_column(enum_type(RelationComponent, "component"), primary_key=True)
    value: Mapped[int] = mapped_column(default=0)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ConstitutionRow(Base):
    __tablename__ = "constitutions"
    __table_args__ = (between("rights", PERCENT_MIN, PERCENT_MAX), CheckConstraint("offices >= 0", name="offices_count"))

    polity_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    ideology_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"), index=True)
    selectorate: Mapped[SelectorateKind] = mapped_column(enum_type(SelectorateKind, "selectorate"))
    offices: Mapped[int] = mapped_column(default=3)
    rights: Mapped[int] = mapped_column(default=50)
    written_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class JourneyEncounterRow(Base):
    __tablename__ = "journey_encounters"
    __table_args__ = (
        between("weight", PERCENT_MIN, PERCENT_MAX),
        between("loss_pct", PERCENT_MIN, PERCENT_MAX),
        Index("ix_journey_encounters_env", "environment"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    world_id: Mapped[int | None] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"), index=True)
    environment: Mapped[RouteEnvironment] = mapped_column(enum_type(RouteEnvironment, "environment"))
    effect: Mapped[EncounterEffect] = mapped_column(enum_type(EncounterEffect, "effect"))
    name: Mapped[str | None] = mapped_column(String(NAME_MAX_LENGTH))
    weight: Mapped[int] = mapped_column(default=50)
    loss_pct: Mapped[int] = mapped_column(default=10)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
