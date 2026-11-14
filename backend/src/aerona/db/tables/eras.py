from sqlalchemy import JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.eras import ProgrammeStage
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN

PROGRAMME_FIELDS = ("technique", "progress", "stage", "visibility", "sabotaged", "finished_epoch")


class TechProgrammeRow(Base):
    __tablename__ = "tech_programmes"
    __table_args__ = (
        between("progress", PERCENT_MIN, PERCENT_MAX),
        between("visibility", PERCENT_MIN, PERCENT_MAX),
        at_least("sabotaged", 0),
        at_least("started_epoch", 0),
        Index("ix_tech_programmes_polity", "polity_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    polity_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    technique: Mapped[Technique] = mapped_column(enum_type(Technique, "technique"))
    progress: Mapped[int] = mapped_column(default=0)
    stage: Mapped[ProgrammeStage] = mapped_column(enum_type(ProgrammeStage, "stage"), default=ProgrammeStage.PLANNING)
    visibility: Mapped[int] = mapped_column(default=10)
    sabotaged: Mapped[int] = mapped_column(default=0)
    started_epoch: Mapped[int] = mapped_column(default=0)
    finished_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
