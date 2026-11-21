from sqlalchemy import JSON, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import NAME_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.governance import (
    CliqueAim,
    GoverningBody,
    HeadSelection,
    InsolvencyPath,
    InsolvencyStage,
    MergerKind,
    MergerStage,
    OrgStrategy,
    VoteBasis,
)
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN


class OrgGovernanceRow(Base):
    __tablename__ = "org_governance"
    __table_args__ = (
        between("quorum_pct", PERCENT_MIN, PERCENT_MAX),
        between("trust", PERCENT_MIN, PERCENT_MAX),
        at_least("term_epochs", 1),
        at_least("since_epoch", 0),
    )

    org_node_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    decision_body: Mapped[GoverningBody] = mapped_column(enum_type(GoverningBody, "decision_body"), default=GoverningBody.HEAD)
    head_selection: Mapped[HeadSelection] = mapped_column(enum_type(HeadSelection, "head_selection"), default=HeadSelection.APPOINTED_BY_OWNER)
    head_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    term_epochs: Mapped[int] = mapped_column(default=2)
    term_ends_epoch: Mapped[int | None]
    vote_basis: Mapped[VoteBasis] = mapped_column(enum_type(VoteBasis, "vote_basis"), default=VoteBasis.ONE_MEMBER_ONE_VOTE)
    quorum_pct: Mapped[int] = mapped_column(default=50)
    strategy: Mapped[OrgStrategy] = mapped_column(enum_type(OrgStrategy, "strategy"), default=OrgStrategy.HOLD)
    trust: Mapped[int] = mapped_column(default=60)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class OrgSeatRow(Base):
    __tablename__ = "org_seats"
    __table_args__ = (
        UniqueConstraint("org_node_id", "member_node_id", name="uq_org_seats_member"),
        between("vote_weight", PERCENT_MIN, PERCENT_MAX),
        at_least("since_epoch", 0),
        Index("ix_org_seats_member", "member_node_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    org_node_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    member_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    since_epoch: Mapped[int] = mapped_column(default=0)
    vote_weight: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class OrgCliqueRow(Base):
    __tablename__ = "org_cliques"
    __table_args__ = (
        between("strength", PERCENT_MIN, PERCENT_MAX),
        at_least("since_epoch", 0),
        Index("ix_org_cliques_org", "org_node_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    org_node_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH))
    leader_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    members: Mapped[list[int]] = mapped_column(JSON, default=list)
    aim: Mapped[CliqueAim] = mapped_column(enum_type(CliqueAim, "aim"), default=CliqueAim.STRATEGY)
    aim_strategy: Mapped[OrgStrategy | None] = mapped_column(enum_type(OrgStrategy, "aim_strategy"))
    aim_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    strength: Mapped[int] = mapped_column(default=10)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class OrgMergerRow(Base):
    __tablename__ = "org_mergers"
    __table_args__ = (
        at_least("price", 0),
        between("share_offer_pct", PERCENT_MIN, PERCENT_MAX),
        at_least("started_epoch", 0),
        Index("ix_org_mergers_acquirer", "acquirer_node_id"),
        Index("ix_org_mergers_target", "target_node_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    acquirer_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    target_node_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    kind: Mapped[MergerKind] = mapped_column(enum_type(MergerKind, "kind"), default=MergerKind.MERGER)
    price: Mapped[int] = mapped_column(default=0)
    share_offer_pct: Mapped[int] = mapped_column(default=0)
    stage: Mapped[MergerStage] = mapped_column(enum_type(MergerStage, "stage"), default=MergerStage.BID)
    friendly_buyer_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    started_epoch: Mapped[int] = mapped_column(default=0)
    ended_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class OrgResearchRow(Base):
    __tablename__ = "org_research"
    __table_args__ = (
        at_least("budget", 0),
        at_least("staff", 0),
        between("progress", PERCENT_MIN, PERCENT_MAX),
        between("secrecy", PERCENT_MIN, PERCENT_MAX),
        at_least("started_epoch", 0),
        Index("ix_org_research_org", "org_node_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    org_node_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    technique: Mapped[Technique | None] = mapped_column(enum_type(Technique, "technique"))
    design_id: Mapped[int | None] = mapped_column(ForeignKey("designs.id", ondelete="SET NULL"))
    budget: Mapped[int] = mapped_column(default=0)
    staff: Mapped[int] = mapped_column(default=1)
    progress: Mapped[int] = mapped_column(default=0)
    secrecy: Mapped[int] = mapped_column(default=50)
    started_epoch: Mapped[int] = mapped_column(default=0)
    done_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class InsolvencyCaseRow(Base):
    __tablename__ = "insolvency_cases"
    __table_args__ = (
        at_least("owed", 0),
        at_least("assets", 0),
        between("recovered_pct", PERCENT_MIN, PERCENT_MAX),
        at_least("started_epoch", 0),
        Index("ix_insolvency_cases_debtor", "debtor_node_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    debtor_node_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    creditors: Mapped[list[int]] = mapped_column(JSON, default=list)
    owed: Mapped[int] = mapped_column(default=0)
    assets: Mapped[int] = mapped_column(default=0)
    path: Mapped[InsolvencyPath] = mapped_column(enum_type(InsolvencyPath, "path"), default=InsolvencyPath.LIQUIDATION)
    court_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    stage: Mapped[InsolvencyStage] = mapped_column(enum_type(InsolvencyStage, "stage"), default=InsolvencyStage.FILED)
    recovered_pct: Mapped[int] = mapped_column(default=0)
    started_epoch: Mapped[int] = mapped_column(default=0)
    ended_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
