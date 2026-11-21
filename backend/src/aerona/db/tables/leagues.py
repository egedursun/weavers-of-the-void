from sqlalchemy import JSON, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.leagues import LeagueDecisionKind, LeagueDecisionOutcome, LeagueOrgan, LeagueStanding, LeagueVoteBasis
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN


class PolityLeagueRow(Base):
    __tablename__ = "polity_leagues"
    __table_args__ = (
        between("dues_pct", PERCENT_MIN, PERCENT_MAX),
        between("depth", PERCENT_MIN, PERCENT_MAX),
        between("common_tariff_pct", PERCENT_MIN, PERCENT_MAX),
        at_least("treasury", 0),
        at_least("founded_epoch", 0),
    )

    league_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    aims: Mapped[list[str]] = mapped_column(JSON, default=list)
    seat_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    dues_pct: Mapped[int] = mapped_column(default=3)
    vote_basis: Mapped[LeagueVoteBasis] = mapped_column(enum_type(LeagueVoteBasis, "vote_basis"), default=LeagueVoteBasis.ONE_MEMBER_ONE_VOTE)
    organs: Mapped[list[str]] = mapped_column(JSON, default=list)
    treasury: Mapped[int] = mapped_column(default=0)
    depth: Mapped[int] = mapped_column(default=20)
    common_tariff_pct: Mapped[int] = mapped_column(default=0)
    authority_id: Mapped[int | None] = mapped_column(ForeignKey("monetary_authorities.id", ondelete="SET NULL"))
    charter_treaty_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    founded_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class LeagueMemberRow(Base):
    __tablename__ = "league_members"
    __table_args__ = (
        UniqueConstraint("league_entity_id", "polity_entity_id", name="uq_league_members_pair"),
        at_least("dues_paid", 0),
        at_least("joined_epoch", 0),
        Index("ix_league_members_polity", "polity_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    league_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    polity_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    standing: Mapped[LeagueStanding] = mapped_column(enum_type(LeagueStanding, "standing"), default=LeagueStanding.MEMBER)
    dues_paid: Mapped[int] = mapped_column(default=0)
    veto: Mapped[bool] = mapped_column(default=False)
    joined_epoch: Mapped[int] = mapped_column(default=0)
    defiance: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class LeagueDecisionRow(Base):
    __tablename__ = "league_decisions"
    __table_args__ = (
        at_least("votes_for", 0),
        at_least("votes_against", 0),
        between("rate_pct", PERCENT_MIN, PERCENT_MAX),
        at_least("epoch", 0),
        Index("ix_league_decisions_league", "league_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    league_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    organ: Mapped[LeagueOrgan] = mapped_column(enum_type(LeagueOrgan, "organ"), default=LeagueOrgan.ASSEMBLY)
    kind: Mapped[LeagueDecisionKind] = mapped_column(enum_type(LeagueDecisionKind, "kind"), default=LeagueDecisionKind.BUDGET)
    subject_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    proposer_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    rate_pct: Mapped[int] = mapped_column(default=0)
    votes_for: Mapped[int] = mapped_column(default=0)
    votes_against: Mapped[int] = mapped_column(default=0)
    outcome: Mapped[LeagueDecisionOutcome] = mapped_column(enum_type(LeagueDecisionOutcome, "outcome"), default=LeagueDecisionOutcome.PENDING)
    epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
