from sqlalchemy import JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.networks import NetworkAccess, NetworkCarrier, NetworkRole, OutageCause

TECH_MAX = 10


class NetworkProfileRow(Base):
    __tablename__ = "network_profiles"
    __table_args__ = (
        between("capacity", 0, 100),
        at_least("delay_days", 0),
        between("security", 0, 100),
        between("reliability", 0, 100),
        between("curation", 0, 100),
        between("censorship", 0, 100),
        between("tech_level", 0, TECH_MAX),
        at_least("down_until_epoch", 0),
    )

    network_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    carrier: Mapped[NetworkCarrier] = mapped_column(enum_type(NetworkCarrier, "carrier"), default=NetworkCarrier.RELAY)
    access: Mapped[NetworkAccess] = mapped_column(enum_type(NetworkAccess, "access"), default=NetworkAccess.MEMBERS)
    carries_messages: Mapped[bool] = mapped_column(default=True)
    carries_records: Mapped[bool] = mapped_column(default=False)
    carries_control: Mapped[bool] = mapped_column(default=False)
    carries_money: Mapped[bool] = mapped_column(default=False)
    carries_minds: Mapped[bool] = mapped_column(default=False)
    carries_opinion: Mapped[bool] = mapped_column(default=False)
    capacity: Mapped[int] = mapped_column(default=20)
    delay_days: Mapped[int] = mapped_column(default=10)
    security: Mapped[int] = mapped_column(default=30)
    reliability: Mapped[int] = mapped_column(default=70)
    curation: Mapped[int] = mapped_column(default=0)
    censorship: Mapped[int] = mapped_column(default=0)
    owner_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    tech_level: Mapped[int] = mapped_column(default=1)
    down_until_epoch: Mapped[int] = mapped_column(default=0)
    founded_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class NetworkNodeRow(Base):
    __tablename__ = "network_nodes"
    __table_args__ = (
        between("dependency_pct", 0, 100),
        between("security", 0, 100),
        Index("ix_network_nodes_member", "member_node_id"),
        Index("ix_network_nodes_network", "network_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    network_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    member_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    role: Mapped[NetworkRole] = mapped_column(enum_type(NetworkRole, "role"), default=NetworkRole.STATION)
    dependency_pct: Mapped[int] = mapped_column(default=0)
    security: Mapped[int] = mapped_column(default=30)
    joined_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class NetworkGatewayRow(Base):
    __tablename__ = "network_gateways"
    __table_args__ = (at_least("toll", 0), between("filter_pct", 0, 100))

    id: Mapped[int] = mapped_column(primary_key=True)
    first_network_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    second_network_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    toll: Mapped[int] = mapped_column(default=0)
    filter_pct: Mapped[int] = mapped_column(default=0)
    owner_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class NetworkOutageRow(Base):
    __tablename__ = "network_outages"
    __table_args__ = (at_least("epoch", 0), at_least("epochs", 1), between("severity", 0, 100))

    id: Mapped[int] = mapped_column(primary_key=True)
    network_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    cause: Mapped[OutageCause] = mapped_column(enum_type(OutageCause, "cause"))
    epoch: Mapped[int] = mapped_column(default=0)
    epochs: Mapped[int] = mapped_column(default=1)
    severity: Mapped[int] = mapped_column(default=50)
