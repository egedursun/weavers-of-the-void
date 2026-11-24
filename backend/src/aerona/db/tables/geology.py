from sqlalchemy import JSON, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import NAME_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.environment import TerrainKind
from aerona.domain.enums.geology import DeepPassageOrigin, DeepPassageState, RockKind, UndergroundStratum


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
        between("extent", 1, 100),
        between("light", 0, 100),
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
    name: Mapped[str | None] = mapped_column(String(NAME_MAX_LENGTH))
    terrain: Mapped[TerrainKind] = mapped_column(
        enum_type(TerrainKind, "terrain"), default=TerrainKind.UNDERGROUND, server_default=TerrainKind.UNDERGROUND.value
    )
    extent: Mapped[int] = mapped_column(default=100, server_default="100")
    light: Mapped[int] = mapped_column(default=0, server_default="0")
    realm_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    by_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class DeepPassageRow(Base):
    __tablename__ = "deep_passages"
    __table_args__ = (
        between("width", 1, 100),
        between("progress", 0, 100),
        UniqueConstraint("first_region_entity_id", "first_stratum", "second_region_entity_id", "second_stratum", name="one_passage_per_ends"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"), index=True)
    first_region_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    first_stratum: Mapped[UndergroundStratum | None] = mapped_column(enum_type(UndergroundStratum, "first_stratum"))
    second_region_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    second_stratum: Mapped[UndergroundStratum | None] = mapped_column(enum_type(UndergroundStratum, "second_stratum"))
    state: Mapped[DeepPassageState] = mapped_column(enum_type(DeepPassageState, "state"), default=DeepPassageState.OPEN)
    origin: Mapped[DeepPassageOrigin] = mapped_column(enum_type(DeepPassageOrigin, "origin"), default=DeepPassageOrigin.NATURAL)
    width: Mapped[int] = mapped_column(default=50)
    progress: Mapped[int] = mapped_column(default=100)
    opened: Mapped[bool] = mapped_column(default=True)
    place_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    dug_by_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    by_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    created_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class PolityDeepKnowledgeRow(Base):
    __tablename__ = "polity_deep_knowledge"
    __table_args__ = (between("level", 0, 100),)

    polity_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    cell_id: Mapped[int] = mapped_column(ForeignKey("region_underground.id", ondelete="CASCADE"), primary_key=True)
    level: Mapped[int] = mapped_column(default=0)
    held: Mapped[bool] = mapped_column(default=False)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
