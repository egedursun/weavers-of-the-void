from sqlalchemy import JSON, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import NAME_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.customs import (
    AgeGrade,
    CoopPurpose,
    EvidenceKind,
    GradeDuty,
    Intoxicant,
    IntoxicantUse,
    MarkKind,
    MarkMeaning,
    Membership,
    NameForm,
    NamingPattern,
    Naturalisation,
    ReliefKind,
    RevivalGoal,
    RevivalStage,
    RevivalWay,
)
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.mortal import LifeStage
from aerona.domain.enums.society import SocialClass

REVIVAL_FIELDS = ("way", "stage", "goal", "strength", "prophet_node_id", "ended_epoch")
INTOXICANT_FIELDS = ("use", "acceptance")
MARK_CUSTOM_FIELDS = ("meaning",)
GRADE_DUTY_FIELDS = ("grade",)
MARK_FIELDS = ("kind", "meaning", "placed_epoch")
TIME_FIELDS = ("work", "rest", "worship", "leisure", "travel", "service", "learning", "care", "art", "housework", "sleep", "civic", "training")
NAMING_FIELDS = ("pattern", "secret_names", "taboo_epochs", "rename_on_initiation", "rename_on_marriage", "rename_on_vow", "posthumous_names")
NAME_FORM_FIELDS = ("name", "given_epoch")
AGE_SET_FIELDS = ("name", "initiated_from", "initiated_to", "grade", "promoted_epoch")
TAVERN_FIELDS = ("keeper_node_id", "patrons", "brawls", "lodging", "rumours")
WELFARE_FIELDS = ("patron_node_id", "inmates", "upkeep")
COMMUTE_FIELDS = ("distance", "labour_lost", "worker_camp")
AGE_MEMBER_FIELDS = ("age_set_id",)
COOP_FIELDS = ("purpose", "pool", "members")
EVIDENCE_FIELDS = ("kind", "points_to_node_id", "reliability", "forged", "found_epoch")
CATEGORY_FIELDS: tuple[str, ...] = ()
MEMBER_FIELDS = ("polity_entity_id", "category", "path")
BORDER_FIELDS = ("fee", "delay", "enforcement", "corruption")
RELIEF_FIELDS = ("kind", "budget", "reach")
MEASURE_FIELDS = ("standard", "adopted_epoch", "fraud")


class RevivalRow(Base):
    __tablename__ = "revivals"
    __table_args__ = (between("strength", PERCENT_MIN, PERCENT_MAX), at_least("started_epoch", 0), Index("ix_revivals_people", "people_entity_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    people_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    dominant_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    way: Mapped[RevivalWay] = mapped_column(enum_type(RevivalWay, "way"))
    stage: Mapped[RevivalStage] = mapped_column(enum_type(RevivalStage, "stage"), default=RevivalStage.STRESS)
    goal: Mapped[RevivalGoal] = mapped_column(enum_type(RevivalGoal, "goal"))
    strength: Mapped[int] = mapped_column(default=30)
    prophet_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    started_epoch: Mapped[int] = mapped_column(default=0)
    ended_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class IntoxicantCustomRow(Base):
    __tablename__ = "intoxicant_customs"
    __table_args__ = (between("acceptance", PERCENT_MIN, PERCENT_MAX),)

    people_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    intoxicant: Mapped[Intoxicant] = mapped_column(enum_type(Intoxicant, "intoxicant"), primary_key=True)
    use: Mapped[IntoxicantUse] = mapped_column(enum_type(IntoxicantUse, "use"), default=IntoxicantUse.FEAST)
    acceptance: Mapped[int] = mapped_column(default=50)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class MarkCustomRow(Base):
    __tablename__ = "mark_customs"

    people_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    kind: Mapped[MarkKind] = mapped_column(enum_type(MarkKind, "kind"), primary_key=True)
    meaning: Mapped[MarkMeaning] = mapped_column(enum_type(MarkMeaning, "meaning"))
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class BodyMarkRow(Base):
    __tablename__ = "body_marks"
    __table_args__ = (at_least("placed_epoch", 0), Index("ix_body_marks_holder", "holder_node_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    holder_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    kind: Mapped[MarkKind] = mapped_column(enum_type(MarkKind, "kind"))
    meaning: Mapped[MarkMeaning] = mapped_column(enum_type(MarkMeaning, "meaning"))
    augment_id: Mapped[int | None] = mapped_column(ForeignKey("augments.id", ondelete="SET NULL"))
    placed_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class TimeBudgetRow(Base):
    __tablename__ = "time_budgets"
    __table_args__ = tuple(between(name, PERCENT_MIN, PERCENT_MAX) for name in TIME_FIELDS)

    people_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    social_class: Mapped[SocialClass] = mapped_column(enum_type(SocialClass, "social_class"), primary_key=True)
    life_stage: Mapped[LifeStage] = mapped_column(
        enum_type(LifeStage, "life_stage"), primary_key=True, default=LifeStage.ADULT, server_default=LifeStage.ADULT.value
    )
    work: Mapped[int] = mapped_column(default=55)
    rest: Mapped[int] = mapped_column(default=20)
    worship: Mapped[int] = mapped_column(default=10)
    leisure: Mapped[int] = mapped_column(default=10)
    travel: Mapped[int] = mapped_column(default=3)
    service: Mapped[int] = mapped_column(default=2)
    learning: Mapped[int] = mapped_column(default=0, server_default="0")
    care: Mapped[int] = mapped_column(default=0, server_default="0")
    art: Mapped[int] = mapped_column(default=0, server_default="0")
    housework: Mapped[int] = mapped_column(default=0, server_default="0")
    sleep: Mapped[int] = mapped_column(default=0, server_default="0")
    civic: Mapped[int] = mapped_column(default=0, server_default="0")
    training: Mapped[int] = mapped_column(default=0, server_default="0")
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class NamingCustomRow(Base):
    __tablename__ = "naming_customs"
    __table_args__ = (at_least("taboo_epochs", 0),)

    people_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    pattern: Mapped[NamingPattern] = mapped_column(enum_type(NamingPattern, "pattern"), default=NamingPattern.GIVEN)
    secret_names: Mapped[bool] = mapped_column(default=False)
    taboo_epochs: Mapped[int] = mapped_column(default=0)
    rename_on_initiation: Mapped[bool] = mapped_column(default=False)
    rename_on_marriage: Mapped[bool] = mapped_column(default=False)
    rename_on_vow: Mapped[bool] = mapped_column(default=False)
    posthumous_names: Mapped[bool] = mapped_column(default=False, server_default="0")
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class NameFormRow(Base):
    __tablename__ = "name_forms"
    __table_args__ = (at_least("given_epoch", 0),)

    holder_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    form: Mapped[NameForm] = mapped_column(enum_type(NameForm, "form"), primary_key=True)
    name: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH))
    given_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class AgeSetRow(Base):
    __tablename__ = "age_sets"
    __table_args__ = (at_least("initiated_from", 0), Index("ix_age_sets_people", "people_entity_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    people_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH))
    initiated_from: Mapped[int] = mapped_column(default=0)
    initiated_to: Mapped[int | None]
    grade: Mapped[AgeGrade] = mapped_column(enum_type(AgeGrade, "grade"), default=AgeGrade.YOUTHS)
    promoted_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class GradeDutyRow(Base):
    __tablename__ = "grade_duties"

    people_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    duty: Mapped[GradeDuty] = mapped_column(enum_type(GradeDuty, "duty"), primary_key=True)
    grade: Mapped[AgeGrade] = mapped_column(enum_type(AgeGrade, "grade"))
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class AgeSetMemberRow(Base):
    __tablename__ = "age_set_members"

    mortal_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    age_set_id: Mapped[int] = mapped_column(ForeignKey("age_sets.id", ondelete="CASCADE"), index=True)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class TavernRow(Base):
    __tablename__ = "taverns"
    __table_args__ = (at_least("patrons", 0), at_least("brawls", 0), at_least("lodging", 0), at_least("rumours", 0))

    structure_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    keeper_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    patrons: Mapped[int] = mapped_column(default=0)
    brawls: Mapped[int] = mapped_column(default=0)
    lodging: Mapped[int] = mapped_column(default=0)
    rumours: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class WelfareRow(Base):
    __tablename__ = "welfare_houses"
    __table_args__ = (at_least("inmates", 0), at_least("upkeep", 0))

    structure_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    patron_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    inmates: Mapped[int] = mapped_column(default=0)
    upkeep: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class CommuteRow(Base):
    __tablename__ = "commutes"
    __table_args__ = (between("distance", PERCENT_MIN, PERCENT_MAX), between("labour_lost", PERCENT_MIN, PERCENT_MAX))

    settlement_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    distance: Mapped[int] = mapped_column(default=0)
    labour_lost: Mapped[int] = mapped_column(default=0)
    worker_camp: Mapped[bool] = mapped_column(default=False)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class CooperativeRow(Base):
    __tablename__ = "cooperatives"
    __table_args__ = (at_least("pool", 0), at_least("members", 0))

    faction_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    purpose: Mapped[CoopPurpose] = mapped_column(enum_type(CoopPurpose, "purpose"))
    pool: Mapped[int] = mapped_column(default=0)
    members: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class EvidenceRow(Base):
    __tablename__ = "evidence"
    __table_args__ = (between("reliability", PERCENT_MIN, PERCENT_MAX), at_least("found_epoch", 0), Index("ix_evidence_case", "case_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("crime_cases.id", ondelete="CASCADE"))
    kind: Mapped[EvidenceKind] = mapped_column(enum_type(EvidenceKind, "kind"))
    points_to_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    reliability: Mapped[int] = mapped_column(default=50)
    forged: Mapped[bool] = mapped_column(default=False)
    sworn: Mapped[bool] = mapped_column(default=False, server_default="0")
    found_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class MembershipCategoryRow(Base):
    __tablename__ = "membership_categories"

    polity_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    category: Mapped[Membership] = mapped_column(enum_type(Membership, "category"), primary_key=True)
    rights: Mapped[list[str]] = mapped_column(JSON, default=list)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class MembershipRow(Base):
    __tablename__ = "memberships"
    __table_args__ = (at_least("since_epoch", 0), Index("ix_memberships_polity", "polity_entity_id"))

    mortal_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    polity_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    category: Mapped[Membership] = mapped_column(enum_type(Membership, "category"))
    path: Mapped[Naturalisation] = mapped_column(enum_type(Naturalisation, "path"), default=Naturalisation.DESCENT)
    spouse_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class BorderControlRow(Base):
    __tablename__ = "border_controls"
    __table_args__ = (
        at_least("fee", 0),
        at_least("delay", 0),
        between("enforcement", PERCENT_MIN, PERCENT_MAX),
        between("corruption", PERCENT_MIN, PERCENT_MAX),
    )

    polity_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    fee: Mapped[int] = mapped_column(default=0)
    delay: Mapped[int] = mapped_column(default=0)
    enforcement: Mapped[int] = mapped_column(default=50)
    corruption: Mapped[int] = mapped_column(default=20)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class PoorReliefRow(Base):
    __tablename__ = "poor_relief"
    __table_args__ = (at_least("budget", 0), between("reach", PERCENT_MIN, PERCENT_MAX))

    polity_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    kind: Mapped[ReliefKind] = mapped_column(enum_type(ReliefKind, "kind"))
    budget: Mapped[int] = mapped_column(default=0)
    reach: Mapped[int] = mapped_column(default=30)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class MeasureStandardRow(Base):
    __tablename__ = "measure_standards"
    __table_args__ = (between("fraud", PERCENT_MIN, PERCENT_MAX),)

    polity_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    standard: Mapped[bool] = mapped_column(default=True)
    adopted_epoch: Mapped[int] = mapped_column(default=0)
    fraud: Mapped[int] = mapped_column(default=10)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
