from sqlalchemy import JSON, Float, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import KEY_MAX_LENGTH, NAME_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import at_least, enum_type
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import RumourDistortion, StepAction, StepOutcome


class RumourDistortionRow(Base):
    __tablename__ = "rumour_distortions"
    __table_args__ = (
        at_least("position", 0),
        at_least("epoch", 0),
        Index("ix_rumour_distortions_rumour", "rumour_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    rumour_id: Mapped[int] = mapped_column(ForeignKey("rumours.id", ondelete="CASCADE"))
    position: Mapped[int] = mapped_column(default=0)
    distortion: Mapped[RumourDistortion] = mapped_column(enum_type(RumourDistortion, "distortion"))
    role: Mapped[IncidentRole | None] = mapped_column(enum_type(IncidentRole, "role"))
    fact_key: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))
    step_id: Mapped[int | None] = mapped_column(ForeignKey("incident_steps.id", ondelete="SET NULL"))
    told_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    told_number: Mapped[float | None] = mapped_column(Float)
    told_enum_value: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))
    told_year: Mapped[int | None]
    told_incident_id: Mapped[int | None] = mapped_column(ForeignKey("incidents.id", ondelete="SET NULL"))
    told_action: Mapped[StepAction | None] = mapped_column(enum_type(StepAction, "told_action"))
    told_outcome: Mapped[StepOutcome | None] = mapped_column(enum_type(StepOutcome, "told_outcome"))
    epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class IncidentNameRow(Base):
    __tablename__ = "incident_names"
    __table_args__ = (at_least("epoch", 0),)

    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id", ondelete="CASCADE"), primary_key=True)
    name: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH))
    language_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
