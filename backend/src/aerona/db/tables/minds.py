from sqlalchemy import JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.constructs import MindWill
from aerona.domain.enums.industry import EnergyKind
from aerona.domain.enums.minds import (
    ArchiveAccess,
    MadeMindsLaw,
    MadeMindSouls,
    MakingOutcome,
    MindAffect,
    MindMaking,
    MindOrigin,
    MindPurpose,
    MindSeat,
    MindUpkeep,
    SoulContinuity,
    StateMedium,
    WillCause,
)

SPEED_MAX = 1000


class MindProfileRow(Base):
    __tablename__ = "mind_profiles"
    __table_args__ = (
        between("capacity", 0, 100),
        between("speed_pct", 1, SPEED_MAX),
        between("stability", 0, 100),
        between("fidelity_pct", 0, 100),
        between("maker_bond", -100, 100),
        between("drift_pct", 0, 100),
        at_least("run_epochs", 0),
        at_least("updated_epoch", 0),
        Index("ix_mind_profiles_seat", "seat_node_id"),
    )

    node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    seat: Mapped[MindSeat] = mapped_column(enum_type(MindSeat, "seat"), default=MindSeat.NONE)
    seat_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    origin: Mapped[MindOrigin] = mapped_column(enum_type(MindOrigin, "origin"), default=MindOrigin.BORN)
    will: Mapped[MindWill] = mapped_column(enum_type(MindWill, "will"), default=MindWill.NONE)
    affect: Mapped[MindAffect] = mapped_column(enum_type(MindAffect, "affect"), default=MindAffect.NONE)
    purpose: Mapped[MindPurpose] = mapped_column(enum_type(MindPurpose, "purpose"), default=MindPurpose.FREE)
    capacity: Mapped[int] = mapped_column(default=50)
    speed_pct: Mapped[int] = mapped_column(default=100)
    stability: Mapped[int] = mapped_column(default=100)
    fidelity_pct: Mapped[int] = mapped_column(default=100)
    upkeep: Mapped[MindUpkeep] = mapped_column(enum_type(MindUpkeep, "upkeep"), default=MindUpkeep.NONE)
    upkeep_energy: Mapped[EnergyKind | None] = mapped_column(enum_type(EnergyKind, "upkeep_energy"))
    pausable: Mapped[bool] = mapped_column(default=False)
    copyable: Mapped[bool] = mapped_column(default=False)
    restorable: Mapped[bool] = mapped_column(default=False)
    mergeable: Mapped[bool] = mapped_column(default=False)
    transferable: Mapped[bool] = mapped_column(default=False)
    dormant: Mapped[bool] = mapped_column(default=False)
    perfect_recall: Mapped[bool] = mapped_column(default=False)
    made_by_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    maker_bond: Mapped[int] = mapped_column(default=0)
    drift_pct: Mapped[int] = mapped_column(default=0)
    souled: Mapped[bool] = mapped_column(default=False)
    run_epochs: Mapped[int] = mapped_column(default=0)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class MindSeatRow(Base):
    __tablename__ = "mind_seats"
    __table_args__ = (between("share_pct", 0, 100), Index("ix_mind_seats_mind", "mind_node_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    mind_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    part_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    share_pct: Mapped[int] = mapped_column(default=10)
    vital: Mapped[bool] = mapped_column(default=False)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class MindStateRow(Base):
    __tablename__ = "mind_states"
    __table_args__ = (
        between("fidelity_pct", 0, 100),
        at_least("taken_epoch", 0),
        at_least("copies", 1),
        Index("ix_mind_states_mind", "mind_node_id"),
        Index("ix_mind_states_holder", "holder_node_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    mind_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    taken_epoch: Mapped[int] = mapped_column(default=0)
    taken_year: Mapped[int | None]
    fidelity_pct: Mapped[int] = mapped_column(default=100)
    holder_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    medium_kind: Mapped[StateMedium] = mapped_column(enum_type(StateMedium, "medium_kind"), default=StateMedium.RECORD)
    sealed: Mapped[bool] = mapped_column(default=False)
    copies: Mapped[int] = mapped_column(default=1)
    owner_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class MindMakingRow(Base):
    __tablename__ = "mind_makings"
    __table_args__ = (between("quality", 0, 100), at_least("epoch", 0), Index("ix_mind_makings_mind", "mind_node_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    mind_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    maker_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    method: Mapped[MindMaking] = mapped_column(enum_type(MindMaking, "method"))
    quality: Mapped[int] = mapped_column(default=50)
    outcome: Mapped[MakingOutcome] = mapped_column(enum_type(MakingOutcome, "outcome"), default=MakingOutcome.AS_MEANT)
    epoch: Mapped[int] = mapped_column(default=0)


class MindWillChangeRow(Base):
    __tablename__ = "mind_will_changes"
    __table_args__ = (at_least("epoch", 0), Index("ix_mind_will_changes_mind", "mind_node_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    mind_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    from_will: Mapped[MindWill] = mapped_column(enum_type(MindWill, "from_will"))
    to_will: Mapped[MindWill] = mapped_column(enum_type(MindWill, "to_will"))
    cause: Mapped[WillCause] = mapped_column(enum_type(WillCause, "cause"))
    epoch: Mapped[int] = mapped_column(default=0)


class MindArchiveRow(Base):
    __tablename__ = "mind_archives"
    __table_args__ = (at_least("upkeep", 0), at_least("unpaid_epochs", 0))

    structure_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    holder_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    upkeep: Mapped[int] = mapped_column(default=2)
    access: Mapped[ArchiveAccess] = mapped_column(enum_type(ArchiveAccess, "access"), default=ArchiveAccess.CLOSED)
    unpaid_epochs: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class RemoteBodyRow(Base):
    __tablename__ = "remote_bodies"
    __table_args__ = (between("feedback_pct", 0, 100), at_least("since_epoch", 0))

    body_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    mind_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), index=True)
    feedback_pct: Mapped[int] = mapped_column(default=30)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class MindLawRow(Base):
    __tablename__ = "mind_laws"

    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"), primary_key=True)
    made_minds: Mapped[MadeMindsLaw] = mapped_column(enum_type(MadeMindsLaw, "made_minds"), default=MadeMindsLaw.WILL_MAY_EMERGE)
    made_mind_souls: Mapped[MadeMindSouls] = mapped_column(enum_type(MadeMindSouls, "made_mind_souls"), default=MadeMindSouls.GRANTED)
    soul_continuity: Mapped[SoulContinuity] = mapped_column(enum_type(SoulContinuity, "soul_continuity"), default=SoulContinuity.STAYS_WITH_FIRST)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
