from sqlalchemy import JSON, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.folk_knowledge import FolkDomain
from aerona.domain.enums.forecasting import ObservationMethod, WeatherAim, WeatherWorkMethod


class ObservationMethodRow(Base):
    __tablename__ = "observation_methods"
    __table_args__ = (
        UniqueConstraint("people_entity_id", "domain", "method", name="uq_observation_methods_people_domain_method"),
        between("accuracy", 0, 100),
        between("reach", 0, 100),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    people_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    domain: Mapped[FolkDomain] = mapped_column(enum_type(FolkDomain, "domain"))
    method: Mapped[ObservationMethod] = mapped_column(enum_type(ObservationMethod, "method"))
    accuracy: Mapped[int] = mapped_column(default=20)
    reach: Mapped[int] = mapped_column(default=20)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class WeatherWorkRow(Base):
    __tablename__ = "weather_works"
    __table_args__ = (between("strength", 0, 100), at_least("cost", 0), at_least("epochs_left", 0), Index("ix_weather_works_region", "region_entity_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    holder_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), index=True)
    region_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    downwind_region_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    method: Mapped[WeatherWorkMethod] = mapped_column(enum_type(WeatherWorkMethod, "method"))
    aim: Mapped[WeatherAim] = mapped_column(enum_type(WeatherAim, "aim"))
    strength: Mapped[int] = mapped_column(default=20)
    cost: Mapped[int] = mapped_column(default=20)
    epochs_left: Mapped[int] = mapped_column(default=1)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
