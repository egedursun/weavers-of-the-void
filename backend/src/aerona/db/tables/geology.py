from sqlalchemy import JSON, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.geology import RockKind, UndergroundStratum


class RegionGeologyRow(Base):
    __tablename__ = "region_geology"
    __table_args__ = (
        between("thickness", 1, 100),
        at_least("depth_order", 0),
        UniqueConstraint("region_entity_id", "depth_order", name="one_layer_per_depth"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    region_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    depth_order: Mapped[int]
    rock: Mapped[RockKind] = mapped_column(enum_type(RockKind, "rock"))
    thickness: Mapped[int]
    veins: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    reached_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class RegionStratumRow(Base):
    __tablename__ = "region_underground"
    __table_args__ = (
        between("volume", 0, 1000),
        between("pressure", 0, 100),
        UniqueConstraint("region_entity_id", "stratum", name="one_stratum_per_region"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    region_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    stratum: Mapped[UndergroundStratum] = mapped_column(enum_type(UndergroundStratum, "stratum"))
    volume: Mapped[int] = mapped_column(default=0)
    pressure: Mapped[int] = mapped_column(default=0)
    reached_epoch: Mapped[int | None]
    breached_epoch: Mapped[int | None]
    tapped_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
