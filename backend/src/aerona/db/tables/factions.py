from sqlalchemy import JSON, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import KEY_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.faction import FactionActionKind, FactionGoalKind, FactionKind, FactionRank, FactionScale
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN


class FactionProfileRow(Base):
    __tablename__ = "faction_profiles"
    __table_args__ = (
        between("cohesion", PERCENT_MIN, PERCENT_MAX),
        between("secrecy", PERCENT_MIN, PERCENT_MAX),
        between("reputation", PERCENT_MIN, PERCENT_MAX),
        between("loyalty", PERCENT_MIN, PERCENT_MAX),
        at_least("treasury", 0),
        at_least("pay", 0),
        at_least("unpaid_epochs", 0),
        Index("ix_faction_profiles_kind", "kind"),
    )

    faction_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    kind: Mapped[FactionKind] = mapped_column(enum_type(FactionKind, "kind"))
    scale: Mapped[FactionScale] = mapped_column(enum_type(FactionScale, "scale"), default=FactionScale.BAND)
    treasury: Mapped[int] = mapped_column(default=0)
    cohesion: Mapped[int] = mapped_column(default=60)
    secrecy: Mapped[int] = mapped_column(default=0)
    armed: Mapped[bool] = mapped_column(default=False)
    reputation: Mapped[int] = mapped_column(default=50)
    influence_over: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    cohort_share: Mapped[dict[str, float]] = mapped_column(JSON, default=dict)
    home_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"), index=True)
    leader_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    outlawed: Mapped[bool] = mapped_column(default=False)
    chartered_by_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    monopoly: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))
    employer_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"), index=True)
    contract_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    pay: Mapped[int] = mapped_column(default=0)
    loyalty: Mapped[int] = mapped_column(default=50)
    unpaid_epochs: Mapped[int] = mapped_column(default=0)
    founded_epoch: Mapped[int] = mapped_column(default=0)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class FactionGoalRow(Base):
    __tablename__ = "faction_goals"
    __table_args__ = (
        between("priority", PERCENT_MIN, PERCENT_MAX),
        between("progress", PERCENT_MIN, PERCENT_MAX),
        Index("ix_faction_goals_faction", "faction_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    faction_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    kind: Mapped[FactionGoalKind] = mapped_column(enum_type(FactionGoalKind, "kind"))
    target_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    target_key: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))
    priority: Mapped[int] = mapped_column(default=50)
    progress: Mapped[int] = mapped_column(default=0)
    since_epoch: Mapped[int] = mapped_column(default=0)
    achieved_epoch: Mapped[int | None]
    set_by_player: Mapped[bool] = mapped_column(default=False)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class FactionMembershipRow(Base):
    __tablename__ = "faction_memberships"
    __table_args__ = (Index("ix_faction_memberships_mortal", "mortal_entity_id"),)

    faction_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    mortal_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    rank: Mapped[FactionRank] = mapped_column(enum_type(FactionRank, "rank"), default=FactionRank.MEMBER)
    joined_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class FactionActionRow(Base):
    __tablename__ = "faction_actions"
    __table_args__ = (Index("ix_faction_actions_faction", "faction_entity_id", "epoch"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    faction_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    epoch: Mapped[int]
    kind: Mapped[FactionActionKind] = mapped_column(enum_type(FactionActionKind, "kind"))
    goal_id: Mapped[int | None] = mapped_column(ForeignKey("faction_goals.id", ondelete="SET NULL"))
    target_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    success: Mapped[bool] = mapped_column(default=True)
    amount: Mapped[int] = mapped_column(default=0)
    note: Mapped[str | None] = mapped_column(Text)
