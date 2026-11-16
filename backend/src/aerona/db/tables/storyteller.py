from sqlalchemy import JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.storyteller import StorytellerProfile, TensionBand

STORYTELLER_FIELDS = ("profile", "tension", "boost_pct", "spotlight_entity_id", "cycle_offset")
BOOST_SPAN = 100


class StorytellerRow(Base):
    __tablename__ = "storytellers"
    __table_args__ = (
        between("tension", PERCENT_MIN, PERCENT_MAX),
        between("boost_pct", -BOOST_SPAN, BOOST_SPAN),
        at_least("cycle_offset", 0),
    )

    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"), primary_key=True)
    profile: Mapped[StorytellerProfile] = mapped_column(enum_type(StorytellerProfile, "profile"), default=StorytellerProfile.CYCLIC)
    tension: Mapped[int] = mapped_column(default=0)
    target: Mapped[int] = mapped_column(default=0)
    band: Mapped[TensionBand] = mapped_column(enum_type(TensionBand, "band"), default=TensionBand.IN_BAND)
    boost_pct: Mapped[int] = mapped_column(default=0)
    cycle_offset: Mapped[int] = mapped_column(default=0)
    spotlight_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    recent_kinds: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    palette: Mapped[dict[str, int]] = mapped_column(JSON, default=dict, server_default="{}")
    target_points: Mapped[list[list[int]]] = mapped_column(JSON, default=list, server_default="[]")
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class TensionRecordRow(Base):
    __tablename__ = "tension_records"
    __table_args__ = (
        between("tension", PERCENT_MIN, PERCENT_MAX),
        Index("ix_tension_records_world", "world_id", "epoch"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"))
    epoch: Mapped[int]
    tension: Mapped[int]
    target: Mapped[int]
    boost_pct: Mapped[int]
    band: Mapped[TensionBand] = mapped_column(enum_type(TensionBand, "band"))
