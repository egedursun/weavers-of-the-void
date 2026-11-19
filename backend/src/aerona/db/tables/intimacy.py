from sqlalchemy import JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.intimacy import (
    BirthAttendant,
    BirthComplication,
    BirthPlace,
    ChildLegitimacy,
    CycleCustom,
    KinScope,
    LegitimacyPath,
    NormEnforcer,
    NormSanction,
    NormStance,
    ParentUnion,
    PostnatalCustom,
    RelationContext,
    RestraintOccasion,
    RestraintRole,
)
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN

GESTATION_MAX = 240


class IntimacyNormRow(Base):
    __tablename__ = "intimacy_norms"

    people_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    context: Mapped[RelationContext] = mapped_column(enum_type(RelationContext, "context"), primary_key=True)
    stance: Mapped[NormStance] = mapped_column(enum_type(NormStance, "stance"), default=NormStance.TOLERATED)
    enforcer: Mapped[NormEnforcer] = mapped_column(enum_type(NormEnforcer, "enforcer"), default=NormEnforcer.NONE)
    sanction: Mapped[NormSanction] = mapped_column(enum_type(NormSanction, "sanction"), default=NormSanction.NONE)
    kin_scope: Mapped[KinScope | None] = mapped_column(enum_type(KinScope, "kin_scope"))
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class RestraintCustomRow(Base):
    __tablename__ = "restraint_customs"
    __table_args__ = (between("strength", PERCENT_MIN, PERCENT_MAX), Index("ix_restraint_customs_people", "people_entity_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    people_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    role: Mapped[RestraintRole] = mapped_column(enum_type(RestraintRole, "role"))
    occasion: Mapped[RestraintOccasion] = mapped_column(enum_type(RestraintOccasion, "occasion"), default=RestraintOccasion.ALWAYS)
    strength: Mapped[int] = mapped_column(default=50)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ReproductiveCourseRow(Base):
    __tablename__ = "reproductive_courses"
    __table_args__ = (between("gestation_months", 1, GESTATION_MAX), between("risk", PERCENT_MIN, PERCENT_MAX), at_least("rest_months", 0))

    people_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    cycle_custom: Mapped[CycleCustom] = mapped_column(enum_type(CycleCustom, "cycle_custom"), default=CycleCustom.NONE)
    gestation_months: Mapped[int] = mapped_column(default=9)
    risk: Mapped[int] = mapped_column(default=50)
    chief_complication: Mapped[BirthComplication] = mapped_column(enum_type(BirthComplication, "chief_complication"), default=BirthComplication.NONE)
    postnatal: Mapped[PostnatalCustom] = mapped_column(enum_type(PostnatalCustom, "postnatal"), default=PostnatalCustom.NONE)
    rest_months: Mapped[int] = mapped_column(default=0)
    attendant: Mapped[BirthAttendant] = mapped_column(enum_type(BirthAttendant, "attendant"), default=BirthAttendant.KIN)
    birth_place: Mapped[BirthPlace] = mapped_column(enum_type(BirthPlace, "birth_place"), default=BirthPlace.ANYWHERE)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class LegitimacyRuleRow(Base):
    __tablename__ = "legitimacy_rules"
    __table_args__ = (between("cost", PERCENT_MIN, PERCENT_MAX),)

    people_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    parent_union: Mapped[ParentUnion] = mapped_column(enum_type(ParentUnion, "parent_union"), primary_key=True)
    standing: Mapped[ChildLegitimacy] = mapped_column(enum_type(ChildLegitimacy, "standing"), default=ChildLegitimacy.FULL)
    path: Mapped[LegitimacyPath] = mapped_column(enum_type(LegitimacyPath, "path"), default=LegitimacyPath.NONE)
    cost: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ChildRecognitionRow(Base):
    __tablename__ = "child_recognitions"
    __table_args__ = (at_least("recognized_epoch", 0),)

    child_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    path: Mapped[LegitimacyPath] = mapped_column(enum_type(LegitimacyPath, "path"), default=LegitimacyPath.RECOGNITION)
    sponsor_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    recognized_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
