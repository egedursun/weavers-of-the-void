from sqlalchemy import JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.childhood import CarryWay, InfantCarer, InfantFeeding, PedagogyTheory, SleepArrangement
from aerona.domain.enums.kin import KinRole
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN

AGE_MAX = 100
STANDING_AGES = ("naming_age", "personhood_age", "work_age", "responsibility_age", "marriage_age")
TECHNIQUE_WEIGHTS = (
    "example",
    "instruction",
    "praise",
    "shame",
    "punishment",
    "ritual_ordeal",
    "storytelling",
    "play",
    "apprenticeship",
    "schooling",
    "peer_group",
    "age_set",
)
AIMS = ("aim_independence", "aim_obedience", "aim_aggression", "aim_restraint", "aim_cooperation", "aim_piety", "aim_craft")


class InfantCareRow(Base):
    __tablename__ = "infant_care"
    __table_args__ = (between("weaning_age", 0, AGE_MAX),)

    people_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    feeding: Mapped[InfantFeeding] = mapped_column(enum_type(InfantFeeding, "feeding"), default=InfantFeeding.BY_BIRTH_PARENT)
    weaning_age: Mapped[int] = mapped_column(default=2)
    carry: Mapped[CarryWay] = mapped_column(enum_type(CarryWay, "carry"), default=CarryWay.CARRIED)
    sleeping: Mapped[SleepArrangement] = mapped_column(enum_type(SleepArrangement, "sleeping"), default=SleepArrangement.WITH_PARENT)
    carer: Mapped[InfantCarer] = mapped_column(enum_type(InfantCarer, "carer"), default=InfantCarer.KIN)
    carer_role: Mapped[KinRole | None] = mapped_column(enum_type(KinRole, "carer_role"))
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ChildStandingRow(Base):
    __tablename__ = "child_standing"
    __table_args__ = (*(between(age, 0, AGE_MAX) for age in STANDING_AGES), between("labour_share", PERCENT_MIN, PERCENT_MAX))

    people_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    naming_age: Mapped[int] = mapped_column(default=0)
    personhood_age: Mapped[int] = mapped_column(default=1)
    work_age: Mapped[int] = mapped_column(default=8)
    responsibility_age: Mapped[int] = mapped_column(default=12)
    marriage_age: Mapped[int] = mapped_column(default=16)
    labour_share: Mapped[int] = mapped_column(default=20)
    protected: Mapped[bool] = mapped_column(default=False)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class SocializationRow(Base):
    __tablename__ = "socialization"
    __table_args__ = tuple(between(name, PERCENT_MIN, PERCENT_MAX) for name in (*TECHNIQUE_WEIGHTS, *AIMS))

    people_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    example: Mapped[int] = mapped_column(default=20)
    instruction: Mapped[int] = mapped_column(default=15)
    praise: Mapped[int] = mapped_column(default=10)
    shame: Mapped[int] = mapped_column(default=5)
    punishment: Mapped[int] = mapped_column(default=5)
    ritual_ordeal: Mapped[int] = mapped_column(default=0)
    storytelling: Mapped[int] = mapped_column(default=10)
    play: Mapped[int] = mapped_column(default=15)
    apprenticeship: Mapped[int] = mapped_column(default=10)
    schooling: Mapped[int] = mapped_column(default=0)
    peer_group: Mapped[int] = mapped_column(default=10)
    age_set: Mapped[int] = mapped_column(default=0)
    aim_independence: Mapped[int] = mapped_column(default=50)
    aim_obedience: Mapped[int] = mapped_column(default=50)
    aim_aggression: Mapped[int] = mapped_column(default=30)
    aim_restraint: Mapped[int] = mapped_column(default=50)
    aim_cooperation: Mapped[int] = mapped_column(default=50)
    aim_piety: Mapped[int] = mapped_column(default=40)
    aim_craft: Mapped[int] = mapped_column(default=40)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class PedagogyRow(Base):
    __tablename__ = "pedagogy"
    __table_args__ = (between("depth", PERCENT_MIN, PERCENT_MAX), at_least("founded_epoch", 0), Index("ix_pedagogy_holder", "holder_node_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    holder_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    theory: Mapped[PedagogyTheory] = mapped_column(enum_type(PedagogyTheory, "theory"), default=PedagogyTheory.ROTE)
    depth: Mapped[int] = mapped_column(default=50)
    founder_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    founded_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
