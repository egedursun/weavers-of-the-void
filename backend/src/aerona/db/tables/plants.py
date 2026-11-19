from sqlalchemy import JSON, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.plants import PlantForm, PlantPart, PlantReproduction


class PlantAnatomyRow(Base):
    __tablename__ = "plant_anatomy"
    __table_args__ = (at_least("lifespan_years", 1), between("growth_months", 1, 12), at_least("first_harvest_years", 0))

    species_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    form: Mapped[PlantForm] = mapped_column(enum_type(PlantForm, "form"))
    reproduction: Mapped[PlantReproduction] = mapped_column(enum_type(PlantReproduction, "reproduction"))
    lifespan_years: Mapped[int] = mapped_column(default=1)
    growth_months: Mapped[int] = mapped_column(default=6)
    first_harvest_years: Mapped[int] = mapped_column(default=0)
    domesticated: Mapped[bool] = mapped_column(default=False)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class PlantPartRow(Base):
    __tablename__ = "plant_parts"
    __table_args__ = (UniqueConstraint("species_entity_id", "part", name="uq_plant_parts_species_part"), between("share", 0, 100))

    id: Mapped[int] = mapped_column(primary_key=True)
    species_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    part: Mapped[PlantPart] = mapped_column(enum_type(PlantPart, "part"))
    commodity: Mapped[CommodityKind | None] = mapped_column(enum_type(CommodityKind, "commodity"))
    share: Mapped[int] = mapped_column(default=30)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
