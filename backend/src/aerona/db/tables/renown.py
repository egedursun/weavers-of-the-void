from sqlalchemy import JSON, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import KEY_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.mind import ActKind, SkillKind
from aerona.domain.enums.renown import ClaimKind, ClaimStatus, LoreKind, LorePrice, ReputationAxis


class ReputationRow(Base):
    __tablename__ = "reputations"
    __table_args__ = (
        between("value", PERCENT_MIN, PERCENT_MAX),
        at_least("heard_epoch", 0),
        UniqueConstraint("subject_node_id", "community_node_id", "axis", "skill", name="uq_reputations_subject_community_axis"),
        Index("ix_reputations_community", "community_node_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    community_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    axis: Mapped[ReputationAxis] = mapped_column(enum_type(ReputationAxis, "axis"))
    skill: Mapped[SkillKind | None] = mapped_column(enum_type(SkillKind, "skill"))
    value: Mapped[int] = mapped_column(default=0)
    heard_epoch: Mapped[int]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class RulerCurrencyRow(Base):
    __tablename__ = "ruler_currencies"
    __table_args__ = (
        between("prestige", PERCENT_MIN, PERCENT_MAX),
        between("piety", PERCENT_MIN, PERCENT_MAX),
        between("dread", PERCENT_MIN, PERCENT_MAX),
        between("tyranny", PERCENT_MIN, PERCENT_MAX),
        at_least("updated_epoch", 0),
    )

    subject_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    prestige: Mapped[int] = mapped_column(default=0)
    piety: Mapped[int] = mapped_column(default=0)
    dread: Mapped[int] = mapped_column(default=0)
    tyranny: Mapped[int] = mapped_column(default=0)
    silenced_until: Mapped[int | None]
    updated_epoch: Mapped[int]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class DeedRow(Base):
    __tablename__ = "deeds"
    __table_args__ = (
        between("magnitude", PERCENT_MIN, PERCENT_MAX),
        at_least("epoch", 0),
        Index("ix_deeds_doer", "doer_node_id"),
        Index("ix_deeds_incident", "incident_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    doer_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    incident_id: Mapped[int | None] = mapped_column(ForeignKey("incidents.id", ondelete="SET NULL"))
    act: Mapped[ActKind | None] = mapped_column(enum_type(ActKind, "act"))
    axis: Mapped[ReputationAxis] = mapped_column(enum_type(ReputationAxis, "axis"))
    skill: Mapped[SkillKind | None] = mapped_column(enum_type(SkillKind, "skill"))
    place_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    magnitude: Mapped[int]
    witnesses: Mapped[int] = mapped_column(default=0)
    token: Mapped[bool] = mapped_column(default=False)
    epoch: Mapped[int]
    note: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class DeedClaimRow(Base):
    __tablename__ = "deed_claims"
    __table_args__ = (
        at_least("epoch", 0),
        UniqueConstraint("deed_id", "claimant_node_id", name="uq_deed_claims_deed_claimant"),
        Index("ix_deed_claims_claimant", "claimant_node_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    deed_id: Mapped[int] = mapped_column(ForeignKey("deeds.id", ondelete="CASCADE"))
    claimant_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    kind: Mapped[ClaimKind] = mapped_column(enum_type(ClaimKind, "kind"))
    status: Mapped[ClaimStatus] = mapped_column(enum_type(ClaimStatus, "status"), default=ClaimStatus.STANDING)
    credited: Mapped[int] = mapped_column(default=0)
    epoch: Mapped[int]
    settled_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class LoreTradeRow(Base):
    __tablename__ = "lore_trades"
    __table_args__ = (
        at_least("epoch", 0),
        at_least("value", 0),
        Index("ix_lore_trades_buyer", "buyer_node_id"),
        Index("ix_lore_trades_seller", "seller_node_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    seller_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    buyer_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    kind: Mapped[LoreKind] = mapped_column(enum_type(LoreKind, "kind"))
    key: Mapped[str] = mapped_column(String(KEY_MAX_LENGTH))
    subject_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    value: Mapped[int]
    price: Mapped[LorePrice] = mapped_column(enum_type(LorePrice, "price"))
    epoch: Mapped[int]
