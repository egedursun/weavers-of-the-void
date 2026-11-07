from sqlalchemy import JSON, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import KEY_MAX_LENGTH, NAME_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.intrigue import BeliefSource, FavourOrigin, HookDemand, HookSource, HookStrength, IdentityReason, IntrigueSecret, PlotKind, SchemePhase
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN

SECRET_FIELDS = ("severity", "known_by", "exposed_epoch")
SCHEME_FIELDS = ("phase", "power", "secrecy", "progress", "agents", "discovered_by")


class SecretRow(Base):
    __tablename__ = "secrets"
    __table_args__ = (between("severity", PERCENT_MIN, PERCENT_MAX), at_least("created_epoch", 0), Index("ix_secrets_holder", "holder_node_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    holder_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    kind: Mapped[IntrigueSecret] = mapped_column(enum_type(IntrigueSecret, "kind"))
    about_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    severity: Mapped[int] = mapped_column(default=40)
    known_by: Mapped[list[int]] = mapped_column(JSON, default=list)
    source: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))
    created_epoch: Mapped[int] = mapped_column(default=0)
    exposed_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class HookRow(Base):
    __tablename__ = "hooks"
    __table_args__ = (at_least("created_epoch", 0), Index("ix_hooks_holder", "holder_node_id"), Index("ix_hooks_target", "target_node_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    holder_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    target_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    strength: Mapped[HookStrength] = mapped_column(enum_type(HookStrength, "strength"))
    source: Mapped[HookSource] = mapped_column(enum_type(HookSource, "source"))
    secret_id: Mapped[int | None] = mapped_column(ForeignKey("secrets.id", ondelete="SET NULL"))
    created_epoch: Mapped[int] = mapped_column(default=0)
    used_epoch: Mapped[int | None]
    last_demand: Mapped[HookDemand | None] = mapped_column(enum_type(HookDemand, "last_demand"))
    locked: Mapped[bool] = mapped_column(default=False)


class FavourRow(Base):
    __tablename__ = "favours"
    __table_args__ = (between("magnitude", PERCENT_MIN, PERCENT_MAX), at_least("created_epoch", 0), Index("ix_favours_owed_to", "owed_to_node_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    owed_by_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), index=True)
    owed_to_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    magnitude: Mapped[int] = mapped_column(default=20)
    origin: Mapped[FavourOrigin] = mapped_column(enum_type(FavourOrigin, "origin"))
    created_epoch: Mapped[int] = mapped_column(default=0)
    called_epoch: Mapped[int | None]
    honoured: Mapped[bool | None]
    locked: Mapped[bool] = mapped_column(default=False)


class IdentityRow(Base):
    __tablename__ = "identities"
    __table_args__ = (between("exposure", PERCENT_MIN, PERCENT_MAX), at_least("since_epoch", 0))

    mortal_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    false_name: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH))
    cover_role: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))
    community_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    reason: Mapped[IdentityReason] = mapped_column(enum_type(IdentityReason, "reason"))
    exposure: Mapped[int] = mapped_column(default=0)
    since_epoch: Mapped[int] = mapped_column(default=0)
    exposed_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class SchemeRow(Base):
    __tablename__ = "schemes"
    __table_args__ = (
        between("secrecy", PERCENT_MIN, PERCENT_MAX),
        between("progress", PERCENT_MIN, PERCENT_MAX),
        at_least("power", 0),
        at_least("started_epoch", 0),
        Index("ix_schemes_owner", "owner_node_id"),
        Index("ix_schemes_target", "target_node_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    kind: Mapped[PlotKind] = mapped_column(enum_type(PlotKind, "kind"))
    target_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    agents: Mapped[list[int]] = mapped_column(JSON, default=list)
    power: Mapped[int] = mapped_column(default=0)
    secrecy: Mapped[int] = mapped_column(default=50)
    progress: Mapped[int] = mapped_column(default=0)
    phase: Mapped[SchemePhase] = mapped_column(enum_type(SchemePhase, "phase"), default=SchemePhase.RECRUIT)
    discovered_by: Mapped[list[int]] = mapped_column(JSON, default=list)
    started_epoch: Mapped[int] = mapped_column(default=0)
    ended_epoch: Mapped[int | None]
    outcome: Mapped[str | None] = mapped_column(Text)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class TrueNameRow(Base):
    __tablename__ = "true_names"
    __table_args__ = (at_least("since_epoch", 0),)

    bearer_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    name: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH))
    language_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    known_by: Mapped[list[int]] = mapped_column(JSON, default=list)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class BeliefRow(Base):
    __tablename__ = "beliefs"
    __table_args__ = (
        between("confidence", PERCENT_MIN, PERCENT_MAX),
        at_least("as_of_epoch", 0),
        Index("ix_beliefs_holder_subject", "holder_node_id", "subject_node_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    holder_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    subject_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    attribute: Mapped[str] = mapped_column(String(KEY_MAX_LENGTH))
    value: Mapped[int]
    confidence: Mapped[int] = mapped_column(default=100)
    as_of_epoch: Mapped[int] = mapped_column(default=0)
    source: Mapped[BeliefSource] = mapped_column(enum_type(BeliefSource, "source"))
    false: Mapped[bool] = mapped_column(default=False)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
