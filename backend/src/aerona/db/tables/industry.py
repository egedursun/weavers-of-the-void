from sqlalchemy import JSON, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.industry import MethodKind, ProcessKind
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN

ENERGY_COLUMNS = ("muscle", "water", "wind", "heat", "magic", "divine")
POLLUTION_COLUMNS = ("air", "water", "soil")


class CommunityMethodRow(Base):
    __tablename__ = "community_methods"
    __table_args__ = (
        at_least("adopted_epoch", 0),
        at_least("displaced", 0),
        UniqueConstraint("community_node_id", "process", name="uq_community_methods_community_process"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    community_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), index=True)
    process: Mapped[ProcessKind] = mapped_column(enum_type(ProcessKind, "process"))
    method: Mapped[MethodKind] = mapped_column(enum_type(MethodKind, "method"))
    adopted_epoch: Mapped[int]
    displaced: Mapped[int] = mapped_column(default=0)
    obsolete_since: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class CommunityIndustryRow(Base):
    __tablename__ = "community_industry"
    __table_args__ = (
        *(at_least(column, 0) for column in ENERGY_COLUMNS),
        at_least("heat_need", 0),
        at_least("tools_worn", 0),
        at_least("spoiled", 0),
        at_least("preserved", 0),
        between("meal_quality", PERCENT_MIN, PERCENT_MAX),
        between("drink", PERCENT_MIN, PERCENT_MAX),
        between("market_access", PERCENT_MIN, PERCENT_MAX),
        between("light", PERCENT_MIN, PERCENT_MAX),
        at_least("black_market", 0),
        at_least("epoch", 0),
    )

    community_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    muscle: Mapped[int] = mapped_column(default=0)
    water: Mapped[int] = mapped_column(default=0)
    wind: Mapped[int] = mapped_column(default=0)
    heat: Mapped[int] = mapped_column(default=0)
    magic: Mapped[int] = mapped_column(default=0)
    divine: Mapped[int] = mapped_column(default=0)
    spent: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    short: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    heat_need: Mapped[int] = mapped_column(default=0)
    tools_worn: Mapped[int] = mapped_column(default=0)
    spoiled: Mapped[int] = mapped_column(default=0)
    preserved: Mapped[int] = mapped_column(default=0)
    meal_quality: Mapped[int] = mapped_column(default=50)
    drink: Mapped[int] = mapped_column(default=0, server_default="0")
    market_access: Mapped[int] = mapped_column(default=100, server_default="100")
    black_market: Mapped[int] = mapped_column(default=0, server_default="0")
    light: Mapped[int] = mapped_column(default=0, server_default="0")
    epoch: Mapped[int]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class RegionPollutionRow(Base):
    __tablename__ = "region_pollution"
    __table_args__ = (*(between(column, PERCENT_MIN, PERCENT_MAX) for column in POLLUTION_COLUMNS), at_least("epoch", 0))

    region_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    air: Mapped[int] = mapped_column(default=0)
    water: Mapped[int] = mapped_column(default=0)
    soil: Mapped[int] = mapped_column(default=0)
    polluters: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    epoch: Mapped[int]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
