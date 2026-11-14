from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import KEY_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.region import DangerOrigin, DangerSource, MemoryOrigin, RegionMemoryKind, TerrainHazard


class RegionDangerRow(Base):
    __tablename__ = "region_dangers"
    __table_args__ = (
        between("strength", PERCENT_MIN, PERCENT_MAX),
        UniqueConstraint("region_entity_id", "source", name="one_danger_per_source"),
        Index("ix_region_dangers_world", "world_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"))
    region_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    source: Mapped[DangerSource] = mapped_column(enum_type(DangerSource, "source"))
    strength: Mapped[int] = mapped_column(default=0)
    origin: Mapped[DangerOrigin] = mapped_column(enum_type(DangerOrigin, "origin"), default=DangerOrigin.DERIVED)
    source_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    son_id: Mapped[int | None] = mapped_column(ForeignKey("sons.id", ondelete="SET NULL"))
    held: Mapped[bool] = mapped_column(default=False)
    since_epoch: Mapped[int] = mapped_column(default=0)
    updated_epoch: Mapped[int] = mapped_column(default=0)


class RegionMemoryRow(Base):
    __tablename__ = "region_memories"
    __table_args__ = (
        between("magnitude", PERCENT_MIN, PERCENT_MAX),
        at_least("epoch", 0),
        UniqueConstraint("region_entity_id", "source_key", name="one_memory_per_source"),
        Index("ix_region_memories_world", "world_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"))
    region_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    kind: Mapped[RegionMemoryKind] = mapped_column(enum_type(RegionMemoryKind, "kind"))
    magnitude: Mapped[int] = mapped_column(default=0)
    epoch: Mapped[int] = mapped_column(default=0)
    source_key: Mapped[str] = mapped_column(String(KEY_MAX_LENGTH))
    subject_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    incident_id: Mapped[int | None] = mapped_column(ForeignKey("incidents.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(Text, default="")
    origin: Mapped[MemoryOrigin] = mapped_column(enum_type(MemoryOrigin, "origin"), default=MemoryOrigin.DERIVED)
    held: Mapped[bool] = mapped_column(default=False)


class PolityMapKnowledgeRow(Base):
    __tablename__ = "polity_map_knowledge"
    __table_args__ = (between("level", PERCENT_MIN, PERCENT_MAX), Index("ix_polity_map_knowledge_region", "region_entity_id"))

    polity_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    region_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    level: Mapped[int] = mapped_column(default=0)
    held: Mapped[bool] = mapped_column(default=False)
    updated_epoch: Mapped[int] = mapped_column(default=0)


class RegionHazardRow(Base):
    __tablename__ = "region_hazards"
    __table_args__ = (at_least("deaths", 0), at_least("injured", 0), Index("ix_region_hazards_region", "region_entity_id", "epoch"))

    id: Mapped[int] = mapped_column(primary_key=True)
    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"))
    region_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    hazard: Mapped[TerrainHazard] = mapped_column(enum_type(TerrainHazard, "hazard"))
    epoch: Mapped[int]
    year: Mapped[int | None]
    season_name: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))
    deaths: Mapped[int] = mapped_column(default=0)
    injured: Mapped[int] = mapped_column(default=0)
    soldiers_lost: Mapped[int] = mapped_column(default=0)
    incident_id: Mapped[int | None] = mapped_column(ForeignKey("incidents.id", ondelete="SET NULL"))
