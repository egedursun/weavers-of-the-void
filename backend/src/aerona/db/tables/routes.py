from sqlalchemy import CheckConstraint, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base, CreatedAtMixin
from aerona.db.columns import at_least, between, enum_type
from aerona.db.types import PydanticJSON
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.travel import HorizonStatus, JourneyIntent, JourneyStatus, RouteClosure, TravelMethod
from aerona.domain.models.records import JourneyEvent


class RouteRow(CreatedAtMixin, Base):
    __tablename__ = "routes"
    __table_args__ = (
        CheckConstraint("world_a_id <> world_b_id", name="distinct_worlds"),
        at_least("duration_epochs", 1),
        between("danger", PERCENT_MIN, PERCENT_MAX),
        Index("ix_routes_world_a", "world_a_id", "active"),
        Index("ix_routes_world_b", "world_b_id", "active"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    world_a_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"))
    world_b_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"))
    method: Mapped[TravelMethod] = mapped_column(enum_type(TravelMethod, "method"))
    duration_epochs: Mapped[int]
    danger: Mapped[int]
    known: Mapped[bool] = mapped_column(default=True)
    controller_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    vehicle_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    builder_son_id: Mapped[int | None] = mapped_column(ForeignKey("sons.id", ondelete="SET NULL"))
    bound_star_id: Mapped[int | None] = mapped_column(ForeignKey("stars.id", ondelete="SET NULL"))
    description: Mapped[str | None] = mapped_column(Text)
    created_epoch: Mapped[int]
    active: Mapped[bool] = mapped_column(default=True)
    closure: Mapped[RouteClosure | None] = mapped_column(enum_type(RouteClosure, "closure"))
    temp_open_until_epoch: Mapped[int | None]
    temp_closed_until_epoch: Mapped[int | None]
    closed_by_forgetting_world_id: Mapped[int | None] = mapped_column(ForeignKey("worlds.id", ondelete="SET NULL"))
    sacrifice_paid_epoch: Mapped[int | None]


class JourneyRow(Base):
    __tablename__ = "journeys"
    __table_args__ = (
        at_least("population", 0),
        at_least("epochs_left", 0),
        Index("ix_journeys_status", "status"),
        Index("ix_journeys_route", "route_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    traveller_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    route_id: Mapped[int] = mapped_column(ForeignKey("routes.id", ondelete="CASCADE"))
    vehicle_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    origin_world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"))
    destination_world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"))
    intent: Mapped[JourneyIntent] = mapped_column(enum_type(JourneyIntent, "intent"))
    population: Mapped[int] = mapped_column(default=0)
    epochs_left: Mapped[int]
    status: Mapped[JourneyStatus] = mapped_column(enum_type(JourneyStatus, "status"), default=JourneyStatus.UNDERWAY)
    events: Mapped[list[JourneyEvent]] = mapped_column(PydanticJSON(list[JourneyEvent]), default=list)
    memory_lost: Mapped[bool] = mapped_column(default=False)
    start_epoch: Mapped[int]
    end_epoch: Mapped[int | None]
    result_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))


class HorizonIntuitionRow(CreatedAtMixin, Base):
    __tablename__ = "horizon_intuitions"
    __table_args__ = (Index("ix_horizon_intuitions_status", "status"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    mortal_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    world_id: Mapped[int | None] = mapped_column(ForeignKey("worlds.id", ondelete="SET NULL"))
    epoch: Mapped[int]
    how: Mapped[str | None] = mapped_column(Text)
    method: Mapped[TravelMethod | None] = mapped_column(enum_type(TravelMethod, "method"))
    status: Mapped[HorizonStatus] = mapped_column(enum_type(HorizonStatus, "status"), default=HorizonStatus.PENDING)
    result_world_id: Mapped[int | None] = mapped_column(ForeignKey("worlds.id", ondelete="SET NULL"))
