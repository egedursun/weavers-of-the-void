from sqlalchemy import CheckConstraint, Float, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import KEY_MAX_LENGTH, NAME_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import at_least, enum_type
from aerona.domain.enums.body import DamageType
from aerona.domain.enums.modifier import ModifierOp
from aerona.domain.enums.records import FactUnit, InstrumentKind, StepAction, StepLocus, StepOutcome, StepState

ONE_FACT_VALUE = "(node_id IS NOT NULL) + (number IS NOT NULL) + (enum_value IS NOT NULL) + (name IS NOT NULL) = 1"


class IncidentFactRow(Base):
    __tablename__ = "incident_facts"
    __table_args__ = (
        at_least("position", 0),
        CheckConstraint(ONE_FACT_VALUE, name="one_value"),
        CheckConstraint("unit IS NULL OR number IS NOT NULL", name="unit_with_number"),
        CheckConstraint("(enum_name IS NULL) = (enum_value IS NULL)", name="enum_named"),
        Index("ix_incident_facts_incident_key", "incident_id", "key"),
        Index("ix_incident_facts_node", "node_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id", ondelete="CASCADE"))
    key: Mapped[str] = mapped_column(String(KEY_MAX_LENGTH))
    position: Mapped[int] = mapped_column(default=0)
    node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    number: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[FactUnit | None] = mapped_column(enum_type(FactUnit, "unit"))
    enum_name: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))
    enum_value: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))
    name: Mapped[str | None] = mapped_column(String(NAME_MAX_LENGTH))


class IncidentStepRow(Base):
    __tablename__ = "incident_steps"
    __table_args__ = (
        at_least("position", 0),
        CheckConstraint("round IS NULL OR round >= 0", name="round_not_negative"),
        CheckConstraint("unit IS NULL OR amount IS NOT NULL", name="unit_with_amount"),
        Index("ix_incident_steps_incident_position", "incident_id", "position"),
        Index("ix_incident_steps_actor", "actor_node_id"),
        Index("ix_incident_steps_target", "target_node_id"),
        Index("ix_incident_steps_moment", "year", "season", "day", "hour"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id", ondelete="CASCADE"))
    position: Mapped[int] = mapped_column(default=0)
    round: Mapped[int | None]
    parent_step_id: Mapped[int | None] = mapped_column(ForeignKey("incident_steps.id", ondelete="CASCADE"))
    year: Mapped[int | None]
    season: Mapped[int | None]
    day: Mapped[int | None]
    hour: Mapped[int | None]
    actor_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    target_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    action: Mapped[StepAction] = mapped_column(enum_type(StepAction, "action"))
    instrument_kind: Mapped[InstrumentKind] = mapped_column(enum_type(InstrumentKind, "instrument_kind"), default=InstrumentKind.NONE)
    instrument_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    instrument_key: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))
    locus_kind: Mapped[StepLocus] = mapped_column(enum_type(StepLocus, "locus_kind"), default=StepLocus.NONE)
    locus_key: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))
    locus_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    damage_type: Mapped[DamageType | None] = mapped_column(enum_type(DamageType, "damage_type"))
    amount: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[FactUnit | None] = mapped_column(enum_type(FactUnit, "unit"))
    outcome: Mapped[StepOutcome | None] = mapped_column(enum_type(StepOutcome, "outcome"))
    record_table: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))
    record_key: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))


class IncidentStepStateRow(Base):
    __tablename__ = "incident_step_states"
    __table_args__ = (Index("ix_incident_step_states_node", "node_id"),)

    step_id: Mapped[int] = mapped_column(ForeignKey("incident_steps.id", ondelete="CASCADE"), primary_key=True)
    node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    state: Mapped[StepState] = mapped_column(enum_type(StepState, "state"), primary_key=True)


class IncidentTermRow(Base):
    __tablename__ = "incident_terms"
    __table_args__ = (at_least("position", 0), Index("ix_incident_terms_incident", "incident_id", "fact_key"))

    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id", ondelete="CASCADE"))
    fact_key: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))
    position: Mapped[int] = mapped_column(default=0)
    term: Mapped[str] = mapped_column(String(KEY_MAX_LENGTH))
    source_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    source_incident_id: Mapped[int | None] = mapped_column(ForeignKey("incidents.id", ondelete="SET NULL"))
    op: Mapped[ModifierOp] = mapped_column(enum_type(ModifierOp, "op"), default=ModifierOp.ADD)
    amount: Mapped[float] = mapped_column(Float)
