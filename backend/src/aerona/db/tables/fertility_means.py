from sqlalchemy import JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import between, enum_type
from aerona.domain.enums.fertility_means import FertilityMeans, MeansSource
from aerona.domain.enums.intimacy import NormStance
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN


class FertilityMeansRow(Base):
    __tablename__ = "fertility_means"
    __table_args__ = (
        between("reliability", PERCENT_MIN, PERCENT_MAX),
        between("risk", PERCENT_MIN, PERCENT_MAX),
        between("use_pct", PERCENT_MIN, PERCENT_MAX),
    )

    people_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    means: Mapped[FertilityMeans] = mapped_column(enum_type(FertilityMeans, "means"), primary_key=True)
    source: Mapped[MeansSource] = mapped_column(enum_type(MeansSource, "source"), default=MeansSource.FOLK)
    reliability: Mapped[int] = mapped_column(default=50)
    risk: Mapped[int] = mapped_column(default=5)
    stance: Mapped[NormStance] = mapped_column(enum_type(NormStance, "stance"), default=NormStance.TOLERATED)
    use_pct: Mapped[int] = mapped_column(default=10)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class FertilityUseRow(Base):
    __tablename__ = "fertility_uses"
    __table_args__ = (Index("ix_fertility_uses_user", "user_entity_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    people_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    means: Mapped[FertilityMeans] = mapped_column(enum_type(FertilityMeans, "means"))
    hidden: Mapped[bool] = mapped_column(default=False)
    exposed: Mapped[bool] = mapped_column(default=False)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
