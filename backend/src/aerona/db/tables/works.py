from sqlalchemy import JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.works import EnterpriseForm, EnterpriseManagement, LabourRegime, WorksKind, WorksStatus

STAGES_MAX = 20


class PublicWorksRow(Base):
    __tablename__ = "public_works"
    __table_args__ = (
        between("stages", 1, STAGES_MAX),
        between("stage", 0, STAGES_MAX),
        between("progress", PERCENT_MIN, PERCENT_MAX),
        between("quality", PERCENT_MIN, PERCENT_MAX),
        between("condition", PERCENT_MIN, PERCENT_MAX),
        at_least("budget", 0),
        at_least("begun_epoch", 0),
        Index("ix_public_works_polity", "polity_entity_id"),
        Index("ix_public_works_place", "place_node_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    polity_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    place_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    kind: Mapped[WorksKind] = mapped_column(enum_type(WorksKind, "kind"), default=WorksKind.ROAD)
    labour: Mapped[LabourRegime] = mapped_column(enum_type(LabourRegime, "labour"), default=LabourRegime.PAID)
    stages: Mapped[int] = mapped_column(default=3)
    stage: Mapped[int] = mapped_column(default=0)
    progress: Mapped[int] = mapped_column(default=0)
    budget: Mapped[int] = mapped_column(default=0)
    quality: Mapped[int] = mapped_column(default=60)
    condition: Mapped[int] = mapped_column(default=100)
    status: Mapped[WorksStatus] = mapped_column(enum_type(WorksStatus, "status"), default=WorksStatus.BUILDING)
    begun_epoch: Mapped[int] = mapped_column(default=0)
    finished_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class PublicWorkStageRow(Base):
    __tablename__ = "public_work_stages"
    __table_args__ = (
        between("stage", 1, STAGES_MAX),
        between("quality", PERCENT_MIN, PERCENT_MAX),
        at_least("spent", 0),
        at_least("done_epoch", 0),
        Index("ix_public_work_stages_works", "works_id", "stage"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    works_id: Mapped[int] = mapped_column(ForeignKey("public_works.id", ondelete="CASCADE"))
    polity_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    stage: Mapped[int] = mapped_column(default=1)
    labour: Mapped[LabourRegime] = mapped_column(enum_type(LabourRegime, "labour"), default=LabourRegime.PAID)
    spent: Mapped[int] = mapped_column(default=0)
    quality: Mapped[int] = mapped_column(default=60)
    done_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class StateEnterpriseRow(Base):
    __tablename__ = "state_enterprises"
    __table_args__ = (
        at_least("output", 0),
        at_least("revenue", 0),
        between("corruption", PERCENT_MIN, PERCENT_MAX),
        at_least("founded_epoch", 0),
        Index("ix_state_enterprises_polity", "polity_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    polity_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    sector: Mapped[CommodityKind | None] = mapped_column(enum_type(CommodityKind, "sector"))
    form: Mapped[EnterpriseForm] = mapped_column(enum_type(EnterpriseForm, "form"), default=EnterpriseForm.ROYAL_WORKS)
    management: Mapped[EnterpriseManagement] = mapped_column(enum_type(EnterpriseManagement, "management"), default=EnterpriseManagement.OFFICIAL)
    manager_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    output: Mapped[int] = mapped_column(default=10)
    revenue: Mapped[int] = mapped_column(default=0)
    corruption: Mapped[int] = mapped_column(default=20)
    founded_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
