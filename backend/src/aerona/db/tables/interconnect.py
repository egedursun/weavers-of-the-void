from sqlalchemy import CheckConstraint, Float, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import KEY_MAX_LENGTH
from aerona.db.base import Base, CreatedAtMixin
from aerona.db.columns import at_least, enum_type, nullable_between
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.modifier import IncidentRole, ModifierOp, ModifierSource


class ModifierRow(CreatedAtMixin, Base):
    __tablename__ = "modifiers"
    __table_args__ = (
        at_least("start_epoch", 0),
        CheckConstraint("end_epoch IS NULL OR end_epoch >= start_epoch", name="ends_after_start"),
        nullable_between("decay_pct", PERCENT_MIN, PERCENT_MAX),
        Index("ix_modifiers_target_key", "target_node_id", "target_key"),
        Index("ix_modifiers_source", "source_kind", "source_node_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    target_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    target_key: Mapped[str] = mapped_column(String(KEY_MAX_LENGTH))
    op: Mapped[ModifierOp] = mapped_column(enum_type(ModifierOp, "op"))
    magnitude: Mapped[float] = mapped_column(Float)
    source_kind: Mapped[ModifierSource] = mapped_column(enum_type(ModifierSource, "source_kind"))
    source_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    stacking_group: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))
    start_epoch: Mapped[int]
    end_epoch: Mapped[int | None]
    decay_pct: Mapped[int | None]
    reason_key: Mapped[str] = mapped_column(String(KEY_MAX_LENGTH))


class IncidentRow(CreatedAtMixin, Base):
    __tablename__ = "incidents"
    __table_args__ = (
        at_least("epoch", 1),
        at_least("magnitude", 0),
        Index("ix_incidents_epoch_kind", "epoch", "kind"),
        Index("ix_incidents_cause", "cause_incident_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(KEY_MAX_LENGTH))
    epoch: Mapped[int]
    year: Mapped[int | None]
    world_id: Mapped[int | None] = mapped_column(ForeignKey("worlds.id", ondelete="SET NULL"))
    place_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    cause_incident_id: Mapped[int | None] = mapped_column(ForeignKey("incidents.id", ondelete="SET NULL"))
    chronicle_id: Mapped[int | None] = mapped_column(ForeignKey("chronicle.id", ondelete="SET NULL"), unique=True)
    magnitude: Mapped[int] = mapped_column(default=0)


class IncidentParticipantRow(Base):
    __tablename__ = "incident_participants"

    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id", ondelete="CASCADE"), primary_key=True)
    node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True, index=True)
    role: Mapped[IncidentRole] = mapped_column(enum_type(IncidentRole, "role"), primary_key=True)
    position: Mapped[int] = mapped_column(default=0)
