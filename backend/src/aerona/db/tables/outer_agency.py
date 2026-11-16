from sqlalchemy import JSON, CheckConstraint, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import enum_type
from aerona.domain.enums.outer import IncursionStage, OuterGoal, OuterPlanState, OuterPrice, OuterRelation, OuterSealKind

PLAN_FIELDS = ("goal", "stage", "progress", "target_node_id", "state")
HERALD_FIELDS = ("outer_entity_id", "zeal")
INCURSION_FIELDS = ("stage", "strength", "rift_id", "region_entity_id")
PACT_FIELDS = ("price", "paid", "power_id")
RELATION_FIELDS = ("relation",)
SEAL_FIELDS = ("kind", "strength", "sealer_node_id")


class OuterPlanRow(Base):
    __tablename__ = "outer_plans"
    __table_args__ = (Index("ix_outer_plans_being", "outer_entity_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    outer_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    goal: Mapped[OuterGoal] = mapped_column(enum_type(OuterGoal, "goal"))
    stage: Mapped[int] = mapped_column(default=0)
    progress: Mapped[int] = mapped_column(default=0)
    target_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    state: Mapped[OuterPlanState] = mapped_column(enum_type(OuterPlanState, "state"), default=OuterPlanState.ACTIVE)
    started_epoch: Mapped[int] = mapped_column(default=0)
    sign_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class OuterHeraldRow(Base):
    __tablename__ = "outer_heralds"
    __table_args__ = (Index("ix_outer_heralds_being", "outer_entity_id"),)

    herald_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    outer_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    zeal: Mapped[int] = mapped_column(default=50)
    bound_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class OuterIncursionRow(Base):
    __tablename__ = "outer_incursions"
    __table_args__ = (Index("ix_outer_incursions_being", "outer_entity_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    outer_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    rift_id: Mapped[int | None] = mapped_column(ForeignKey("rifts.id", ondelete="SET NULL"))
    region_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    stage: Mapped[IncursionStage] = mapped_column(enum_type(IncursionStage, "stage"), default=IncursionStage.PROBING)
    strength: Mapped[int] = mapped_column(default=20)
    started_epoch: Mapped[int] = mapped_column(default=0)
    ended_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class OuterPactRow(Base):
    __tablename__ = "outer_pacts"
    __table_args__ = (Index("ix_outer_pacts_being", "outer_entity_id"), Index("ix_outer_pacts_holder", "holder_node_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    outer_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    holder_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    price: Mapped[OuterPrice] = mapped_column(enum_type(OuterPrice, "price"))
    paid: Mapped[bool] = mapped_column(default=False)
    power_id: Mapped[int | None] = mapped_column(ForeignKey("powers.id", ondelete="SET NULL"))
    struck_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class OuterRelationRow(Base):
    __tablename__ = "outer_relations"
    __table_args__ = (CheckConstraint("outer_entity_id <> other_entity_id", name="two_beings"), Index("ix_outer_relations_other", "other_entity_id"))

    outer_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    other_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    relation: Mapped[OuterRelation] = mapped_column(enum_type(OuterRelation, "relation"), default=OuterRelation.IGNORE)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class OuterSealRow(Base):
    __tablename__ = "outer_seals"
    __table_args__ = (Index("ix_outer_seals_being", "outer_entity_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    outer_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    sealer_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    kind: Mapped[OuterSealKind] = mapped_column(enum_type(OuterSealKind, "kind"), default=OuterSealKind.SEAL)
    strength: Mapped[int] = mapped_column(default=60)
    sealed_epoch: Mapped[int] = mapped_column(default=0)
    broken_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
