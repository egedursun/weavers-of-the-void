from sqlalchemy import JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type, nullable_between
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.mortal import CareerPath, DeathCause, LifeStage, MarriageEnd, MarriageKind, StressBreak

PROFILE_PERCENTS = (
    "fertility",
    "health",
    "stress",
    "wealth",
    "renown",
    "honour",
    "infamy",
    "education",
    "loyalty_liege",
    "loyalty_community",
    "loyalty_god",
)
PROFILE_LOCKS = ("life", "health", "stress", "standing", "loyalty", "career", "education", "equipment", "kin")
EQUIPMENT_COLUMNS = ("wielded_main_id", "wielded_off_id", "armour_body_id", "armour_head_id", "mount_id", "focus_id")


class MortalProfileRow(Base):
    __tablename__ = "mortal_profiles"
    __table_args__ = (
        *(between(column, PERCENT_MIN, PERCENT_MAX) for column in PROFILE_PERCENTS),
        nullable_between("legitimacy", PERCENT_MIN, PERCENT_MAX),
        at_least("updated_epoch", 0),
        Index("ix_mortal_profiles_polity", "polity_id"),
    )

    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    life_stage: Mapped[LifeStage] = mapped_column(enum_type(LifeStage, "life_stage"), default=LifeStage.ADULT)
    fertility: Mapped[int] = mapped_column(default=0)
    health: Mapped[int] = mapped_column(default=PERCENT_MAX)
    stress: Mapped[int] = mapped_column(default=0)
    wealth: Mapped[int] = mapped_column(default=0)
    renown: Mapped[int] = mapped_column(default=0)
    honour: Mapped[int] = mapped_column(default=PERCENT_MAX // 2)
    infamy: Mapped[int] = mapped_column(default=0)
    legitimacy: Mapped[int | None]
    education: Mapped[int] = mapped_column(default=0)
    polity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    loyalty_liege: Mapped[int] = mapped_column(default=PERCENT_MAX // 2)
    loyalty_community: Mapped[int] = mapped_column(default=PERCENT_MAX // 2)
    loyalty_god: Mapped[int] = mapped_column(default=PERCENT_MAX // 2)
    career: Mapped[CareerPath | None] = mapped_column(enum_type(CareerPath, "career"))
    last_break: Mapped[StressBreak | None] = mapped_column(enum_type(StressBreak, "last_break"))
    last_break_epoch: Mapped[int | None]
    cause_of_death: Mapped[DeathCause | None] = mapped_column(enum_type(DeathCause, "cause_of_death"))
    death_place_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class MortalEquipmentRow(Base):
    __tablename__ = "mortal_equipment"

    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    wielded_main_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    wielded_off_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    armour_body_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    armour_head_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    mount_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    focus_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class MarriageRow(Base):
    __tablename__ = "marriages"
    __table_args__ = (
        at_least("start_epoch", 0),
        Index("ix_marriages_first", "first_id"),
        Index("ix_marriages_second", "second_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    first_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    second_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    kind: Mapped[MarriageKind] = mapped_column(enum_type(MarriageKind, "kind"), default=MarriageKind.MONOGAMOUS)
    treaty_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    start_epoch: Mapped[int]
    end_epoch: Mapped[int | None]
    cause_end: Mapped[MarriageEnd | None] = mapped_column(enum_type(MarriageEnd, "cause_end"))
    forced: Mapped[bool] = mapped_column(default=False)
