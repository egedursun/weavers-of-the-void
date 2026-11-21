from sqlalchemy import JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.interworld import CampaignStage, MigrationCause, MigrationReception
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN


class InterworldCampaignRow(Base):
    __tablename__ = "interworld_campaigns"
    __table_args__ = (
        between("supply", PERCENT_MIN, PERCENT_MAX),
        at_least("carriers", 0),
        at_least("capacity", 0),
        at_least("transit_left", 0),
        at_least("supply_hops", 0),
        at_least("forces", 0),
        Index("ix_interworld_campaigns_attacker", "attacker_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    attacker_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    defender_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"), index=True)
    from_world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"))
    target_world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"), index=True)
    route_id: Mapped[int | None] = mapped_column(ForeignKey("routes.id", ondelete="SET NULL"))
    army_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    stage: Mapped[CampaignStage] = mapped_column(enum_type(CampaignStage, "stage"), default=CampaignStage.GATHERING)
    carriers: Mapped[int] = mapped_column(default=0)
    capacity: Mapped[int] = mapped_column(default=0)
    forces: Mapped[int] = mapped_column(default=0)
    transit_left: Mapped[int] = mapped_column(default=0)
    supply_hops: Mapped[int] = mapped_column(default=0)
    supply: Mapped[int] = mapped_column(default=100)
    begun_epoch: Mapped[int] = mapped_column(default=0)
    ended_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class OrbitalControlRow(Base):
    __tablename__ = "orbital_control"
    __table_args__ = (between("strength", PERCENT_MIN, PERCENT_MAX), Index("ix_orbital_control_world", "world_id", unique=True))

    id: Mapped[int] = mapped_column(primary_key=True)
    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"))
    holder_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    strength: Mapped[int] = mapped_column(default=50)
    contested_by_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class InterworldMigrationRow(Base):
    __tablename__ = "interworld_migrations"
    __table_args__ = (
        at_least("per_epoch", 0),
        at_least("moved", 0),
        at_least("arrived", 0),
        at_least("waiting", 0),
        Index("ix_interworld_migrations_community", "community_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    community_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    from_world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"))
    to_world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"), index=True)
    route_id: Mapped[int | None] = mapped_column(ForeignKey("routes.id", ondelete="SET NULL"))
    cause: Mapped[MigrationCause] = mapped_column(enum_type(MigrationCause, "cause"), default=MigrationCause.LAND_HUNGER)
    reception: Mapped[MigrationReception] = mapped_column(enum_type(MigrationReception, "reception"), default=MigrationReception.WELCOME)
    per_epoch: Mapped[int] = mapped_column(default=0)
    moved: Mapped[int] = mapped_column(default=0)
    arrived: Mapped[int] = mapped_column(default=0)
    waiting: Mapped[int] = mapped_column(default=0)
    journey_ids: Mapped[list[int]] = mapped_column(JSON, default=list)
    begun_epoch: Mapped[int] = mapped_column(default=0)
    ended_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
