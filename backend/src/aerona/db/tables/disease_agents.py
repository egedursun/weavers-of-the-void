from sqlalchemy import JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import between, enum_type
from aerona.domain.enums.disease_agents import CureClass, DiseaseAgent


class DiseaseAgentRow(Base):
    __tablename__ = "disease_agents"
    __table_args__ = (
        between("survival_water", 0, 100),
        between("survival_soil", 0, 100),
        between("survival_objects", 0, 100),
        between("survival_cold", 0, 100),
        between("overuse", 0, 100),
    )

    disease_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    agent: Mapped[DiseaseAgent] = mapped_column(enum_type(DiseaseAgent, "agent"), default=DiseaseAgent.UNKNOWN)
    survival_water: Mapped[int] = mapped_column(default=30)
    survival_soil: Mapped[int] = mapped_column(default=30)
    survival_objects: Mapped[int] = mapped_column(default=30)
    survival_cold: Mapped[int] = mapped_column(default=50)
    reservoir_species_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    overused_cure: Mapped[CureClass | None] = mapped_column(enum_type(CureClass, "overused_cure"))
    overuse: Mapped[int] = mapped_column(default=0)
    identified: Mapped[bool] = mapped_column(default=False)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
