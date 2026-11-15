from sqlalchemy import JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.prehistory import DeepTimeState, PrehistoryKind, PrehistorySource, PrehistoryState

PREHISTORY_FIELDS = ("kind", "state", "epochs", "resolution")
PREHISTORY_EVENT_FIELDS = ("round", "magnitude", "mirrored")
DEEP_TIME_FIELDS = ("state",)
EPOCHS_MAX = 1000
RESOLUTION_MAX = 20
MAGNITUDE_MAX = 100


class PrehistoryRow(Base):
    __tablename__ = "prehistories"
    __table_args__ = (
        between("epochs", 0, EPOCHS_MAX),
        between("resolution", 1, RESOLUTION_MAX),
        at_least("rounds_done", 0),
        at_least("birth_epoch", 0),
        at_least("seconds", 0),
        at_least("slow_rounds", 0),
    )

    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"), primary_key=True)
    kind: Mapped[PrehistoryKind] = mapped_column(enum_type(PrehistoryKind, "kind"))
    state: Mapped[PrehistoryState] = mapped_column(enum_type(PrehistoryState, "state"), default=PrehistoryState.PLANNED)
    source: Mapped[PrehistorySource] = mapped_column(enum_type(PrehistorySource, "source"), default=PrehistorySource.SIMULATED)
    epochs: Mapped[int] = mapped_column(default=0)
    resolution: Mapped[int] = mapped_column(default=1)
    rounds_done: Mapped[int] = mapped_column(default=0)
    birth_epoch: Mapped[int] = mapped_column(default=0)
    seconds: Mapped[int] = mapped_column(default=0)
    slow_rounds: Mapped[int] = mapped_column(default=0)
    source_world_id: Mapped[int | None] = mapped_column(ForeignKey("worlds.id", ondelete="SET NULL"))
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class PrehistoryEventRow(Base):
    __tablename__ = "prehistory_events"
    __table_args__ = (
        at_least("round", 0),
        between("magnitude", 0, MAGNITUDE_MAX),
        Index("ix_prehistory_events_world", "world_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"))
    round: Mapped[int] = mapped_column(default=0)
    magnitude: Mapped[int] = mapped_column(default=0)
    source: Mapped[PrehistorySource] = mapped_column(enum_type(PrehistorySource, "source"))
    incident_id: Mapped[int | None] = mapped_column(ForeignKey("incidents.id", ondelete="SET NULL"))
    subject_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    source_world_id: Mapped[int | None] = mapped_column(ForeignKey("worlds.id", ondelete="SET NULL"))
    mirrored: Mapped[bool] = mapped_column(default=False)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class DeepTimeRunRow(Base):
    __tablename__ = "deep_time_runs"
    __table_args__ = (
        at_least("epochs", 1),
        at_least("ran", 0),
        at_least("from_epoch", 0),
        at_least("to_epoch", 0),
        at_least("sons_simulated", 0),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    epochs: Mapped[int] = mapped_column(default=1)
    ran: Mapped[int] = mapped_column(default=0)
    from_epoch: Mapped[int] = mapped_column(default=0)
    to_epoch: Mapped[int] = mapped_column(default=0)
    state: Mapped[DeepTimeState] = mapped_column(enum_type(DeepTimeState, "state"), default=DeepTimeState.RUNNING)
    sons_simulated: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class DeepTimeEventRow(Base):
    __tablename__ = "deep_time_events"
    __table_args__ = (
        at_least("epoch", 0),
        between("magnitude", 0, MAGNITUDE_MAX),
        Index("ix_deep_time_events_run", "run_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("deep_time_runs.id", ondelete="CASCADE"))
    incident_id: Mapped[int | None] = mapped_column(ForeignKey("incidents.id", ondelete="SET NULL"))
    epoch: Mapped[int] = mapped_column(default=0)
    magnitude: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
