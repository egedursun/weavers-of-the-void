from sqlalchemy import JSON, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import NAME_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.gathering import (
    AttendanceReason,
    CollectionKind,
    CollectionRole,
    GatheringKind,
    GatheringOutcome,
    GatheringStatus,
    GuestRole,
    Milestone,
)
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN

GATHERING_FIELDS = ("kind", "status", "outcome", "cost", "food", "prestige", "epoch", "year", "season", "place_entity_id", "milestone", "note")
COLLECTION_FIELDS = ("name", "kind", "start_epoch", "end_epoch", "parent_id", "note")


class CollectionRow(Base):
    __tablename__ = "incident_collections"
    __table_args__ = (
        at_least("start_epoch", 0),
        Index("ix_incident_collections_kind", "kind", "start_epoch"),
        Index("ix_incident_collections_parent", "parent_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[CollectionKind] = mapped_column(enum_type(CollectionKind, "kind"))
    name: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH))
    world_id: Mapped[int | None] = mapped_column(ForeignKey("worlds.id", ondelete="SET NULL"), index=True)
    start_epoch: Mapped[int]
    end_epoch: Mapped[int | None]
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("incident_collections.id", ondelete="SET NULL"))
    source_key: Mapped[str | None] = mapped_column(String(NAME_MAX_LENGTH), index=True)
    note: Mapped[str | None] = mapped_column(Text)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class CollectionMemberRow(Base):
    __tablename__ = "collection_members"
    __table_args__ = (Index("ix_collection_members_node", "node_id"),)

    collection_id: Mapped[int] = mapped_column(ForeignKey("incident_collections.id", ondelete="CASCADE"), primary_key=True)
    node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    role: Mapped[CollectionRole] = mapped_column(enum_type(CollectionRole, "role"))
    since_epoch: Mapped[int] = mapped_column(default=0)


class CollectionIncidentRow(Base):
    __tablename__ = "collection_incidents"

    collection_id: Mapped[int] = mapped_column(ForeignKey("incident_collections.id", ondelete="CASCADE"), primary_key=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id", ondelete="CASCADE"), primary_key=True, index=True)


class CollectionPlaceRow(Base):
    __tablename__ = "collection_places"
    __table_args__ = (Index("ix_collection_places_place", "place_entity_id"),)

    collection_id: Mapped[int] = mapped_column(ForeignKey("incident_collections.id", ondelete="CASCADE"), primary_key=True)
    place_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)


class GatheringRow(Base):
    __tablename__ = "gatherings"
    __table_args__ = (
        at_least("epoch", 0),
        at_least("year", 0),
        at_least("season", 0),
        at_least("cost", 0),
        at_least("food", 0),
        between("prestige", PERCENT_MIN, PERCENT_MAX),
        Index("ix_gatherings_host", "host_node_id", "epoch"),
        Index("ix_gatherings_place", "place_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    host_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    kind: Mapped[GatheringKind] = mapped_column(enum_type(GatheringKind, "kind"))
    status: Mapped[GatheringStatus] = mapped_column(enum_type(GatheringStatus, "status"), default=GatheringStatus.PLANNED)
    outcome: Mapped[GatheringOutcome | None] = mapped_column(enum_type(GatheringOutcome, "outcome"))
    milestone: Mapped[Milestone | None] = mapped_column(enum_type(Milestone, "milestone"))
    place_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    world_id: Mapped[int | None] = mapped_column(ForeignKey("worlds.id", ondelete="SET NULL"))
    honoured_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    tradition_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    collection_id: Mapped[int | None] = mapped_column(ForeignKey("incident_collections.id", ondelete="SET NULL"))
    epoch: Mapped[int]
    year: Mapped[int | None]
    season: Mapped[int | None]
    cost: Mapped[int] = mapped_column(default=0)
    food: Mapped[int] = mapped_column(default=0)
    prestige: Mapped[int] = mapped_column(default=0)
    by_player: Mapped[bool] = mapped_column(default=False)
    note: Mapped[str | None] = mapped_column(Text)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class GatheringGuestRow(Base):
    __tablename__ = "gathering_guests"
    __table_args__ = (Index("ix_gathering_guests_node", "node_id"),)

    gathering_id: Mapped[int] = mapped_column(ForeignKey("gatherings.id", ondelete="CASCADE"), primary_key=True)
    node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    role: Mapped[GuestRole] = mapped_column(enum_type(GuestRole, "role"), default=GuestRole.GUEST)
    reason: Mapped[AttendanceReason] = mapped_column(enum_type(AttendanceReason, "reason"))
    invited: Mapped[bool] = mapped_column(default=True)
    attended: Mapped[bool | None]
    harmed: Mapped[bool] = mapped_column(default=False)
    locked: Mapped[bool] = mapped_column(default=False)
