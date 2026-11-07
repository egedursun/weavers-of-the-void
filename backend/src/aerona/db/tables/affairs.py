from sqlalchemy import JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.settlement import DistrictKind
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.statecraft import CourtPosition, MandateKind, MandateState, NobleWant, ResolutionKind, ResolutionState, TaxKind

RATE_MAX = 50


class ElectionRow(Base):
    __tablename__ = "elections"
    __table_args__ = (between("turnout", PERCENT_MIN, PERCENT_MAX), at_least("seats", 0), Index("ix_elections_polity", "polity_entity_id", "epoch"))

    id: Mapped[int] = mapped_column(primary_key=True)
    polity_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    epoch: Mapped[int] = mapped_column(default=0)
    seats: Mapped[int] = mapped_column(default=0)
    turnout: Mapped[int] = mapped_column(default=0)
    winner_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    results: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)


class CouncilSeatRow(Base):
    __tablename__ = "council_seats"
    __table_args__ = (at_least("seats", 0), between("votes", PERCENT_MIN, PERCENT_MAX))

    polity_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    holder_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True, index=True)
    seats: Mapped[int] = mapped_column(default=0)
    votes: Mapped[int] = mapped_column(default=0)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[bool] = mapped_column(default=False)


class TaxPolicyRow(Base):
    __tablename__ = "tax_policies"
    __table_args__ = (between("rate", 0, RATE_MAX), between("efficiency", PERCENT_MIN, PERCENT_MAX), at_least("take", 0))

    polity_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    kind: Mapped[TaxKind] = mapped_column(enum_type(TaxKind, "kind"), primary_key=True)
    rate: Mapped[int] = mapped_column(default=5)
    farmed: Mapped[bool] = mapped_column(default=False)
    efficiency: Mapped[int] = mapped_column(default=50)
    take: Mapped[int] = mapped_column(default=0)
    epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class MandateRow(Base):
    __tablename__ = "mandates"
    __table_args__ = (at_least("amount", 0), at_least("issued_epoch", 0), Index("ix_mandates_polity", "polity_entity_id", "state"))

    id: Mapped[int] = mapped_column(primary_key=True)
    polity_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    issuer_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    kind: Mapped[MandateKind] = mapped_column(enum_type(MandateKind, "kind"))
    settlement_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"), index=True)
    commodity: Mapped[CommodityKind | None] = mapped_column(enum_type(CommodityKind, "commodity"))
    district: Mapped[DistrictKind | None] = mapped_column(enum_type(DistrictKind, "district"))
    amount: Mapped[int] = mapped_column(default=0)
    issued_epoch: Mapped[int] = mapped_column(default=0)
    until_epoch: Mapped[int] = mapped_column(default=0)
    state: Mapped[MandateState] = mapped_column(enum_type(MandateState, "state"), default=MandateState.ACTIVE)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class NobleDemandRow(Base):
    __tablename__ = "noble_demands"
    __table_args__ = (at_least("since_epoch", 0),)

    mortal_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    want: Mapped[NobleWant] = mapped_column(enum_type(NobleWant, "want"), primary_key=True)
    since_epoch: Mapped[int] = mapped_column(default=0)
    met: Mapped[bool] = mapped_column(default=False)
    locked: Mapped[bool] = mapped_column(default=False)


class PolicyApprovalRow(Base):
    __tablename__ = "policy_approval"
    __table_args__ = (between("approval", -PERCENT_MAX, PERCENT_MAX),)

    polity_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    social_class: Mapped[SocialClass] = mapped_column(enum_type(SocialClass, "social_class"), primary_key=True)
    approval: Mapped[int] = mapped_column(default=0)
    parts: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ResolutionRow(Base):
    __tablename__ = "resolutions"
    __table_args__ = (
        at_least("votes_for", 0),
        at_least("votes_against", 0),
        at_least("proposed_epoch", 0),
        Index("ix_resolutions_assembly", "assembly_entity_id", "state"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    assembly_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    kind: Mapped[ResolutionKind] = mapped_column(enum_type(ResolutionKind, "kind"))
    target_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"), index=True)
    votes_for: Mapped[int] = mapped_column(default=0)
    votes_against: Mapped[int] = mapped_column(default=0)
    state: Mapped[ResolutionState] = mapped_column(enum_type(ResolutionState, "state"), default=ResolutionState.PROPOSED)
    proposed_epoch: Mapped[int] = mapped_column(default=0)
    until_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ResolutionVoteRow(Base):
    __tablename__ = "resolution_votes"
    __table_args__ = (at_least("weight", 0),)

    resolution_id: Mapped[int] = mapped_column(ForeignKey("resolutions.id", ondelete="CASCADE"), primary_key=True)
    member_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True, index=True)
    aye: Mapped[bool] = mapped_column(default=False)
    weight: Mapped[int] = mapped_column(default=1)
    locked: Mapped[bool] = mapped_column(default=False)


class CourtRow(Base):
    __tablename__ = "courts"
    __table_args__ = (between("grandeur", PERCENT_MIN, PERCENT_MAX), at_least("courtiers", 0))

    polity_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    grandeur: Mapped[int] = mapped_column(default=0)
    courtiers: Mapped[int] = mapped_column(default=0)
    parts: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class CourtPositionRow(Base):
    __tablename__ = "court_positions"
    __table_args__ = (at_least("since_epoch", 0),)

    polity_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    position: Mapped[CourtPosition] = mapped_column(enum_type(CourtPosition, "position"), primary_key=True)
    holder_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"), index=True)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[bool] = mapped_column(default=False)
