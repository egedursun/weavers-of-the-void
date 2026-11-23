from sqlalchemy import JSON, CheckConstraint, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, enum_type, nullable_between
from aerona.domain.enums.affliction import ChangeSign, CharmKind, PackageKind, Transmission
from aerona.domain.enums.body import BodyPlan
from aerona.domain.enums.material import MaterialKind


class AfflictionRow(Base):
    __tablename__ = "afflictions"
    __table_args__ = (
        at_least("stage", 0),
        at_least("since_epoch", 0),
        nullable_between("fortune_strength", 0, 100),
        nullable_between("charm_strength", 0, 100),
        CheckConstraint("fortune_sign IS NULL OR fortune_sign IN (-1, 1)", name="fortune_sign_one"),
        Index("ix_afflictions_bearer", "bearer_node_id"),
        Index("ix_afflictions_package", "package"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    bearer_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    package: Mapped[PackageKind] = mapped_column(enum_type(PackageKind, "package"))
    stage: Mapped[int] = mapped_column(default=0)
    since_epoch: Mapped[int]
    stage_since_epoch: Mapped[int]
    transmission: Mapped[Transmission] = mapped_column(enum_type(Transmission, "transmission"))
    source_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    cured_epoch: Mapped[int | None]
    applied: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    fortune_sign: Mapped[int | None]
    fortune_strength: Mapped[int | None]
    transform_plan: Mapped[BodyPlan | None] = mapped_column(enum_type(BodyPlan, "transform_plan"))
    transform_species_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    transform_substance: Mapped[MaterialKind | None] = mapped_column(enum_type(MaterialKind, "transform_substance"))
    transform_trigger: Mapped[ChangeSign | None] = mapped_column(enum_type(ChangeSign, "transform_trigger"))
    transform_mind_kept: Mapped[bool | None]
    transform_from_plan: Mapped[BodyPlan | None] = mapped_column(enum_type(BodyPlan, "transform_from_plan"))
    charm_target_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    charm_kind: Mapped[CharmKind | None] = mapped_column(enum_type(CharmKind, "charm_kind"))
    charm_strength: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
