from sqlalchemy import JSON, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import NAME_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.demography import Job
from aerona.domain.enums.labour import ContractStatus, DisputeAct, DisputeOutcome, LabourDemand, LegalStanding, WorkerBodyForm
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN

WAGE_MAX = 400
HOURS_MAX = 168


class WorkerBodyRow(Base):
    __tablename__ = "worker_bodies"
    __table_args__ = (
        at_least("members", 0),
        at_least("dues", 0),
        at_least("fund", 0),
        between("solidarity", PERCENT_MIN, PERCENT_MAX),
        at_least("founded_epoch", 0),
    )

    faction_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    form: Mapped[WorkerBodyForm] = mapped_column(enum_type(WorkerBodyForm, "form"), default=WorkerBodyForm.MUTUAL_AID)
    trades: Mapped[list[str]] = mapped_column(JSON, default=list)
    works: Mapped[list[int]] = mapped_column(JSON, default=list)
    members: Mapped[int] = mapped_column(default=0)
    dues: Mapped[int] = mapped_column(default=1)
    fund: Mapped[int] = mapped_column(default=0)
    solidarity: Mapped[int] = mapped_column(default=50)
    standing: Mapped[LegalStanding] = mapped_column(enum_type(LegalStanding, "standing"), default=LegalStanding.TOLERATED)
    founded_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class LabourContractRow(Base):
    __tablename__ = "labour_contracts"
    __table_args__ = (
        between("wage", 0, WAGE_MAX),
        between("hours", 0, HOURS_MAX),
        between("safety", PERCENT_MIN, PERCENT_MAX),
        between("rest", PERCENT_MIN, PERCENT_MAX),
        between("keep", PERCENT_MIN, PERCENT_MAX),
        at_least("term_epochs", 1),
        at_least("started_epoch", 0),
        Index("ix_labour_contracts_hirer", "hirer_node_id"),
        Index("ix_labour_contracts_body", "body_node_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    hirer_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    body_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    worker_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    settlement_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    trade: Mapped[Job] = mapped_column(enum_type(Job, "trade"), default=Job.CRAFTING)
    wage: Mapped[int] = mapped_column(default=100)
    hours: Mapped[int] = mapped_column(default=60)
    safety: Mapped[int] = mapped_column(default=40)
    rest: Mapped[int] = mapped_column(default=40)
    keep: Mapped[int] = mapped_column(default=40)
    term_epochs: Mapped[int] = mapped_column(default=2)
    started_epoch: Mapped[int] = mapped_column(default=0)
    status: Mapped[ContractStatus] = mapped_column(enum_type(ContractStatus, "status"), default=ContractStatus.PROPOSED)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class LabourDisputeRow(Base):
    __tablename__ = "labour_disputes"
    __table_args__ = (
        at_least("workers_out", 0),
        at_least("body_losses", 0),
        at_least("hirer_losses", 0),
        at_least("injured", 0),
        at_least("started_epoch", 0),
        Index("ix_labour_disputes_body", "body_node_id"),
        Index("ix_labour_disputes_hirer", "hirer_node_id"),
        Index("ix_labour_disputes_settlement", "settlement_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH), default="")
    body_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    hirer_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    settlement_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    trade: Mapped[Job] = mapped_column(enum_type(Job, "trade"), default=Job.CRAFTING)
    demand: Mapped[LabourDemand] = mapped_column(enum_type(LabourDemand, "demand"), default=LabourDemand.WAGE)
    act: Mapped[DisputeAct] = mapped_column(enum_type(DisputeAct, "act"), default=DisputeAct.STRIKE)
    workers_out: Mapped[int] = mapped_column(default=0)
    body_losses: Mapped[int] = mapped_column(default=0)
    hirer_losses: Mapped[int] = mapped_column(default=0)
    injured: Mapped[int] = mapped_column(default=0)
    strikebreakers: Mapped[bool] = mapped_column(default=False)
    mediator_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    outcome: Mapped[DisputeOutcome] = mapped_column(enum_type(DisputeOutcome, "outcome"), default=DisputeOutcome.ONGOING)
    started_epoch: Mapped[int] = mapped_column(default=0)
    ended_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
