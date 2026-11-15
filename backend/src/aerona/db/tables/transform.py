from typing import Any

from sqlalchemy import JSON, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import NAME_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.transform import ProspectStance, StarModifierSource, TransformKind, TransformState, TransformTrigger

TRANSFORMATION_FIELDS = ("trigger", "subject_name", "result_name")
PROSPECT_FIELDS = ("progress", "stance", "trigger", "warned_epoch", "due_epoch")
STAR_MODIFIER_FIELDS = ("source", "luminosity_pct", "age_epochs", "decay")
LUMINOSITY_SHIFT_MAX = 90


class TransformationRow(Base):
    __tablename__ = "transformations"
    __table_args__ = (
        at_least("epoch", 0),
        Index("ix_transformations_subject", "subject_node_id"),
        Index("ix_transformations_result", "result_node_id"),
        Index("ix_transformations_epoch", "epoch"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[TransformKind] = mapped_column(enum_type(TransformKind, "kind"))
    epoch: Mapped[int] = mapped_column(default=0)
    trigger: Mapped[TransformTrigger] = mapped_column(enum_type(TransformTrigger, "trigger"), default=TransformTrigger.ENGINE)
    state: Mapped[TransformState] = mapped_column(enum_type(TransformState, "state"), default=TransformState.DONE)
    subject_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    result_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    subject_name: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH), default="")
    result_name: Mapped[str | None] = mapped_column(String(NAME_MAX_LENGTH))
    incident_id: Mapped[int | None] = mapped_column(ForeignKey("incidents.id", ondelete="SET NULL"))
    undo: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class TransformProspectRow(Base):
    __tablename__ = "transform_prospects"
    __table_args__ = (
        UniqueConstraint("kind", "subject_node_id", name="uq_transform_prospects_kind_subject"),
        between("progress", 0, 100),
        at_least("updated_epoch", 0),
        Index("ix_transform_prospects_subject", "subject_node_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[TransformKind] = mapped_column(enum_type(TransformKind, "kind"))
    subject_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    progress: Mapped[int] = mapped_column(default=0)
    stance: Mapped[ProspectStance] = mapped_column(enum_type(ProspectStance, "stance"), default=ProspectStance.OPEN)
    trigger: Mapped[TransformTrigger] = mapped_column(enum_type(TransformTrigger, "trigger"), default=TransformTrigger.ENGINE)
    warned_epoch: Mapped[int | None]
    due_epoch: Mapped[int | None]
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class StarModifierRow(Base):
    __tablename__ = "star_modifiers"
    __table_args__ = (
        between("luminosity_pct", -LUMINOSITY_SHIFT_MAX, LUMINOSITY_SHIFT_MAX),
        at_least("age_epochs", 0),
        between("decay", 0, 100),
        at_least("epoch", 0),
        Index("ix_star_modifiers_star", "star_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    star_id: Mapped[int] = mapped_column(ForeignKey("stars.id", ondelete="CASCADE"))
    source: Mapped[StarModifierSource] = mapped_column(enum_type(StarModifierSource, "source"))
    luminosity_pct: Mapped[int] = mapped_column(default=0)
    age_epochs: Mapped[int] = mapped_column(default=0)
    aged: Mapped[bool] = mapped_column(default=False)
    decay: Mapped[int] = mapped_column(default=0)
    epoch: Mapped[int] = mapped_column(default=0)
    cause_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
