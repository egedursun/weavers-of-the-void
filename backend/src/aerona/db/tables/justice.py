from sqlalchemy import JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.justice import CaseStage, Deposition, ProposalEvent, ProposalStance, ProposalState, TrialKind, Verdict
from aerona.domain.enums.law_depth import CourtLevel
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.mortal import CrimeKind, PunishmentKind
from aerona.domain.enums.polity import LawKind, LegitimacyBasis


class LawProposalRow(Base):
    __tablename__ = "law_proposals"
    __table_args__ = (
        between("progress", PERCENT_MIN, PERCENT_MAX),
        between("support", PERCENT_MIN, PERCENT_MAX),
        between("opposition", PERCENT_MIN, PERCENT_MAX),
        at_least("stalled_epochs", 0),
        at_least("proposed_epoch", 0),
        Index("ix_law_proposals_polity", "polity_entity_id", "state"),
        Index("ix_law_proposals_champion", "champion_node_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    polity_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    kind: Mapped[LawKind] = mapped_column(enum_type(LawKind, "kind"))
    params: Mapped[dict[str, int | str | bool]] = mapped_column(JSON, default=dict)
    champion_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    law_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    basis: Mapped[LegitimacyBasis] = mapped_column(enum_type(LegitimacyBasis, "basis"), default=LegitimacyBasis.COUNCIL)
    progress: Mapped[int] = mapped_column(default=0)
    support: Mapped[int] = mapped_column(default=0)
    opposition: Mapped[int] = mapped_column(default=0)
    stalled_epochs: Mapped[int] = mapped_column(default=0)
    state: Mapped[ProposalState] = mapped_column(enum_type(ProposalState, "state"), default=ProposalState.DEBATING)
    last_event: Mapped[ProposalEvent | None] = mapped_column(enum_type(ProposalEvent, "last_event"))
    amended: Mapped[bool] = mapped_column(default=False)
    proposed_epoch: Mapped[int] = mapped_column(default=0)
    resolved_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ProposalStanceRow(Base):
    __tablename__ = "proposal_stances"
    __table_args__ = (between("weight", PERCENT_MIN, PERCENT_MAX),)

    proposal_id: Mapped[int] = mapped_column(ForeignKey("law_proposals.id", ondelete="CASCADE"), primary_key=True)
    node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True, index=True)
    stance: Mapped[ProposalStance] = mapped_column(enum_type(ProposalStance, "stance"))
    weight: Mapped[int] = mapped_column(default=0)
    hooked: Mapped[bool] = mapped_column(default=False)
    locked: Mapped[bool] = mapped_column(default=False)


class CrimeCaseRow(Base):
    __tablename__ = "crime_cases"
    __table_args__ = (
        between("evidence", PERCENT_MIN, PERCENT_MAX),
        at_least("opened_epoch", 0),
        Index("ix_crime_cases_settlement", "settlement_entity_id", "stage"),
        Index("ix_crime_cases_accused", "accused_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    settlement_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    polity_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"), index=True)
    crime: Mapped[CrimeKind] = mapped_column(enum_type(CrimeKind, "crime"))
    culprit_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"), index=True)
    accused_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    investigator_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"), index=True)
    judge_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"), index=True)
    stage: Mapped[CaseStage] = mapped_column(enum_type(CaseStage, "stage"), default=CaseStage.INVESTIGATION)
    trial: Mapped[TrialKind | None] = mapped_column(enum_type(TrialKind, "trial"))
    evidence: Mapped[int] = mapped_column(default=0)
    tortured: Mapped[bool] = mapped_column(default=False)
    forged: Mapped[bool] = mapped_column(default=False)
    verdict: Mapped[Verdict | None] = mapped_column(enum_type(Verdict, "verdict"))
    wrongful: Mapped[bool] = mapped_column(default=False)
    penalty: Mapped[PunishmentKind | None] = mapped_column(enum_type(PunishmentKind, "penalty"))
    immune: Mapped[bool] = mapped_column(default=False, server_default="0")
    opened_epoch: Mapped[int] = mapped_column(default=0)
    closed_epoch: Mapped[int | None]
    advocate_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    court: Mapped[CourtLevel] = mapped_column(enum_type(CourtLevel, "court"), default=CourtLevel.LOCAL, server_default="local")
    oracle_answer: Mapped[Verdict | None] = mapped_column(enum_type(Verdict, "oracle_answer"))
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class CaseWitnessRow(Base):
    __tablename__ = "case_witnesses"
    __table_args__ = (between("reliability", PERCENT_MIN, PERCENT_MAX),)

    case_id: Mapped[int] = mapped_column(ForeignKey("crime_cases.id", ondelete="CASCADE"), primary_key=True)
    witness_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True, index=True)
    testimony: Mapped[Deposition] = mapped_column(enum_type(Deposition, "testimony"))
    reliability: Mapped[int] = mapped_column(default=50)
    locked: Mapped[bool] = mapped_column(default=False)
