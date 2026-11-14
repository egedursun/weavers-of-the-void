from sqlalchemy import JSON, CheckConstraint, Float, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.body import BodyPlan
from aerona.domain.enums.demography import (
    Aesthetic,
    AgeBand,
    CohortCondition,
    FolkDiet,
    FuneralCustom,
    InheritanceCustom,
    Job,
    MarriageCustom,
    MartialStyle,
    Sex,
)
from aerona.domain.enums.ecology import Biochemistry, SizeClass
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.environment import TemperatureBand
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.nature import Thermoregulation
from aerona.domain.enums.physics import AirNeed
from aerona.domain.enums.society import SocialClass


class CohortRow(Base):
    __tablename__ = "community_cohorts"
    __table_args__ = (at_least("count", 0), at_least("generation_epoch", 0), Index("ix_community_cohorts_community", "community_entity_id"))

    community_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    age_band: Mapped[AgeBand] = mapped_column(enum_type(AgeBand, "age_band"), primary_key=True)
    sex: Mapped[Sex] = mapped_column(enum_type(Sex, "sex"), primary_key=True)
    social_class: Mapped[SocialClass] = mapped_column(enum_type(SocialClass, "social_class"), primary_key=True)
    condition: Mapped[CohortCondition] = mapped_column(enum_type(CohortCondition, "condition"), primary_key=True)
    count: Mapped[int] = mapped_column(default=0)
    generation_epoch: Mapped[int] = mapped_column(default=0)


class LabourRow(Base):
    __tablename__ = "community_labour"
    __table_args__ = (at_least("workers", 0), between("output_pct", 0, 1000))

    community_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    job: Mapped[Job] = mapped_column(enum_type(Job, "job"), primary_key=True)
    workers: Mapped[int] = mapped_column(default=0)
    output_pct: Mapped[int] = mapped_column(default=100)
    epoch: Mapped[int] = mapped_column(default=0)
    held: Mapped[bool] = mapped_column(default=False)


class PeopleBiologyRow(Base):
    __tablename__ = "people_biology"
    __table_args__ = (
        at_least("maturity_years", 1),
        at_least("adult_years", 1),
        at_least("elder_years", 1),
        between("fertility_pct", PERCENT_MIN, PERCENT_MAX * 5),
        CheckConstraint("gravity_low > 0 AND gravity_high >= gravity_low", name="gravity_band"),
    )

    people_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    maturity_years: Mapped[int]
    adult_years: Mapped[int]
    elder_years: Mapped[int]
    fertility_pct: Mapped[int]
    acclimatised: Mapped[TemperatureBand] = mapped_column(enum_type(TemperatureBand, "acclimatised"))
    traits: Mapped[list[str]] = mapped_column(JSON, default=list)
    staple: Mapped[CommodityKind] = mapped_column(enum_type(CommodityKind, "staple"))
    immunities: Mapped[list[int]] = mapped_column(JSON, default=list)
    body_plan: Mapped[BodyPlan] = mapped_column(enum_type(BodyPlan, "body_plan"), default=BodyPlan.HUMANOID)
    size_class: Mapped[SizeClass] = mapped_column(enum_type(SizeClass, "size_class"), default=SizeClass.MEDIUM)
    diet: Mapped[FolkDiet] = mapped_column(enum_type(FolkDiet, "diet"), default=FolkDiet.OMNIVORE)
    biochemistry: Mapped[Biochemistry] = mapped_column(enum_type(Biochemistry, "biochemistry"), default=Biochemistry.CARBON_WATER)
    air: Mapped[AirNeed] = mapped_column(enum_type(AirNeed, "air"), default=AirNeed.OXYGEN)
    thermoregulation: Mapped[Thermoregulation] = mapped_column(enum_type(Thermoregulation, "thermoregulation"), default=Thermoregulation.ENDOTHERM)
    gravity_low: Mapped[float] = mapped_column(Float, default=0.5)
    gravity_high: Mapped[float] = mapped_column(Float, default=1.6)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class PeopleCultureRow(Base):
    __tablename__ = "people_culture"
    __table_args__ = (
        between("cohesion", PERCENT_MIN, PERCENT_MAX),
        between("literacy", PERCENT_MIN, PERCENT_MAX),
        between("urbanisation", PERCENT_MIN, PERCENT_MAX),
    )

    people_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    cohesion: Mapped[int]
    literacy: Mapped[int]
    urbanisation: Mapped[int]
    liturgical_language_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    trade_language_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    staples: Mapped[list[str]] = mapped_column(JSON, default=list)
    aesthetic: Mapped[Aesthetic] = mapped_column(enum_type(Aesthetic, "aesthetic"))
    martial_style: Mapped[MartialStyle] = mapped_column(enum_type(MartialStyle, "martial_style"))
    funeral_rite_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    funeral_rite: Mapped[FuneralCustom] = mapped_column(enum_type(FuneralCustom, "funeral_rite"), default=FuneralCustom.BURIAL)
    martial_record: Mapped[dict[str, list[int]]] = mapped_column(JSON, default=dict)
    martial_epoch: Mapped[int] = mapped_column(default=0)
    marriage: Mapped[MarriageCustom] = mapped_column(enum_type(MarriageCustom, "marriage"))
    endogamous: Mapped[bool] = mapped_column(default=False)
    inheritance: Mapped[InheritanceCustom] = mapped_column(enum_type(InheritanceCustom, "inheritance"))
    slavery_lawful: Mapped[bool] = mapped_column(default=False)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
