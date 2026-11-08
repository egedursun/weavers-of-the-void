from sqlalchemy import JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.db.profile_guard import register_profile_table
from aerona.domain.enums.ecology import Biochemistry, Cultivation, GrowthCycle
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN


class PlantProfileRow(Base):
    __tablename__ = "plant_profiles"
    __table_args__ = (between("soil_need", PERCENT_MIN, PERCENT_MAX), at_least("growing_seasons", 1))

    species_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    growth_cycle: Mapped[GrowthCycle] = mapped_column(enum_type(GrowthCycle, "growth_cycle"), default=GrowthCycle.ANNUAL)
    growing_seasons: Mapped[int] = mapped_column(default=1)
    soil_need: Mapped[int] = mapped_column(default=30)
    cultivation: Mapped[Cultivation] = mapped_column(enum_type(Cultivation, "cultivation"), default=Cultivation.WILD)
    cultivar_of_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class RegionCropRow(Base):
    __tablename__ = "region_crops"
    __table_args__ = (between("share", PERCENT_MIN, PERCENT_MAX),)

    region_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    plant_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    share: Mapped[int] = mapped_column(default=20)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class CropPestRow(Base):
    __tablename__ = "crop_pests"

    plant_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    pest_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class WorldBiochemistryRow(Base):
    __tablename__ = "world_biochemistries"

    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"), primary_key=True)
    biochemistry: Mapped[Biochemistry] = mapped_column(enum_type(Biochemistry, "biochemistry"), primary_key=True)


register_profile_table(RegionCropRow.__tablename__, "region_entity_id")
register_profile_table(CropPestRow.__tablename__, "plant_entity_id")
