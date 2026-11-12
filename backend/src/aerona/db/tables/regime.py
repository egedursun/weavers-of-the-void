from sqlalchemy import JSON, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.regime import (
    ClientRole,
    CredentialKind,
    LeadershipMode,
    PowerStance,
    Routinisation,
    SegmentLevel,
    SelectorateKind,
)

NAME = 200
REGIME_FIELDS = (
    "selectorate",
    "selectorate_size",
    "coalition_size",
    "coalition_loyalty",
    "public_share",
    "traditional",
    "charismatic",
    "rational",
    "founder_entity_id",
    "routinisation",
    "horizon",
    "extraction",
    "institutions",
    "leadership",
    "rotation",
    "parallel_guard",
    "loyalty_promotion",
    "hostages",
)
MEMBER_FIELDS = ("reward", "loyalty")
TIE_FIELDS = ("role", "strength")
VENAL_FIELDS = ("price", "buyer_entity_id", "sinecure", "recouped")
BASE_FIELDS = ("holdings", "troops", "offices", "wealth", "popularity", "threat", "stance")
SEGMENT_FIELDS = ("level", "tribe_entity_id", "backs_entity_id")
BREEDING_FIELDS = ("locus", "allele", "target_share", "claim_polity_id", "matches", "love_matches", "barren", "concealed")
EXAM_FIELDS = ("interval", "quota", "pass_mark", "demand", "last_epoch")
SITTING_FIELDS = ("candidates", "passed", "mark")
CREDENTIAL_FIELDS = ("kind", "granter_node_id", "skill")
FREEDOM_FIELDS = ("level", "orthodoxy_node_id", "suppressed")
SCHOOL_FIELDS = ("name", "doctrine_entity_id", "founder_entity_id", "rival_id", "persecuted")
DISCIPLE_FIELDS = ("master_entity_id", "generation")


class RegimeRow(Base):
    __tablename__ = "regimes"
    __table_args__ = (
        at_least("selectorate_size", 0),
        at_least("coalition_size", 0),
        between("coalition_loyalty", PERCENT_MIN, PERCENT_MAX),
        between("public_share", PERCENT_MIN, PERCENT_MAX),
        between("traditional", PERCENT_MIN, PERCENT_MAX),
        between("charismatic", PERCENT_MIN, PERCENT_MAX),
        between("rational", PERCENT_MIN, PERCENT_MAX),
        between("horizon", PERCENT_MIN, PERCENT_MAX),
        between("extraction", PERCENT_MIN, PERCENT_MAX * 2),
        between("institutions", PERCENT_MIN, PERCENT_MAX),
        at_least("updated_epoch", 0),
    )

    polity_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    selectorate: Mapped[SelectorateKind] = mapped_column(enum_type(SelectorateKind, "selectorate"), default=SelectorateKind.NOBLES)
    selectorate_size: Mapped[int] = mapped_column(default=0)
    coalition_size: Mapped[int] = mapped_column(default=0)
    coalition_loyalty: Mapped[int] = mapped_column(default=50)
    public_share: Mapped[int] = mapped_column(default=50)
    traditional: Mapped[int] = mapped_column(default=40)
    charismatic: Mapped[int] = mapped_column(default=20)
    rational: Mapped[int] = mapped_column(default=10)
    founder_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    ruler_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    routinisation: Mapped[Routinisation] = mapped_column(enum_type(Routinisation, "routinisation"), default=Routinisation.NONE)
    crisis_epoch: Mapped[int | None]
    horizon: Mapped[int] = mapped_column(default=50)
    extraction: Mapped[int] = mapped_column(default=100)
    institutions: Mapped[int] = mapped_column(default=20)
    leadership: Mapped[LeadershipMode] = mapped_column(enum_type(LeadershipMode, "leadership"), default=LeadershipMode.STATE)
    rotation: Mapped[bool] = mapped_column(default=False)
    parallel_guard: Mapped[bool] = mapped_column(default=False)
    loyalty_promotion: Mapped[bool] = mapped_column(default=False)
    hostages: Mapped[bool] = mapped_column(default=False)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class CoalitionMemberRow(Base):
    __tablename__ = "coalition_members"
    __table_args__ = (
        between("reward", PERCENT_MIN, PERCENT_MAX),
        between("loyalty", PERCENT_MIN, PERCENT_MAX),
        at_least("since_epoch", 0),
        Index("ix_coalition_members_mortal", "mortal_entity_id"),
    )

    polity_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    mortal_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    reward: Mapped[int] = mapped_column(default=0)
    loyalty: Mapped[int] = mapped_column(default=50)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class PatronageTieRow(Base):
    __tablename__ = "patronage_ties"
    __table_args__ = (
        between("strength", PERCENT_MIN, PERCENT_MAX),
        at_least("since_epoch", 0),
        Index("ix_patronage_ties_patron", "patron_node_id"),
        Index("ix_patronage_ties_client", "client_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    patron_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    client_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    role: Mapped[ClientRole] = mapped_column(enum_type(ClientRole, "role"), default=ClientRole.RETAINER)
    strength: Mapped[int] = mapped_column(default=30)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class VenalOfficeRow(Base):
    __tablename__ = "venal_offices"
    __table_args__ = (at_least("price", 0), at_least("recouped", 0), at_least("sold_epoch", 0))

    office_id: Mapped[int] = mapped_column(ForeignKey("offices.id", ondelete="CASCADE"), primary_key=True)
    price: Mapped[int] = mapped_column(default=0)
    buyer_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    sinecure: Mapped[bool] = mapped_column(default=False)
    recouped: Mapped[int] = mapped_column(default=0)
    sold_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class PowerBaseRow(Base):
    __tablename__ = "power_bases"
    __table_args__ = (
        at_least("holdings", 0),
        at_least("troops", 0),
        at_least("offices", 0),
        at_least("wealth", 0),
        between("popularity", PERCENT_MIN, PERCENT_MAX),
        at_least("total", 0),
        between("threat", PERCENT_MIN, PERCENT_MAX),
        at_least("updated_epoch", 0),
    )

    mortal_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    polity_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    holdings: Mapped[int] = mapped_column(default=0)
    troops: Mapped[int] = mapped_column(default=0)
    offices: Mapped[int] = mapped_column(default=0)
    wealth: Mapped[int] = mapped_column(default=0)
    popularity: Mapped[int] = mapped_column(default=0)
    total: Mapped[int] = mapped_column(default=0)
    threat: Mapped[int] = mapped_column(default=0)
    stance: Mapped[PowerStance] = mapped_column(enum_type(PowerStance, "stance"), default=PowerStance.LOYAL)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class LineageSegmentRow(Base):
    __tablename__ = "lineage_segments"
    __table_args__ = (at_least("since_epoch", 0), Index("ix_lineage_segments_tribe", "tribe_entity_id"))

    house_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    level: Mapped[SegmentLevel] = mapped_column(enum_type(SegmentLevel, "level"), default=SegmentLevel.LINEAGE)
    tribe_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    backs_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class BreedingPlanRow(Base):
    __tablename__ = "breeding_plans"
    __table_args__ = (
        between("target_share", PERCENT_MIN, PERCENT_MAX),
        at_least("matches", 0),
        at_least("love_matches", 0),
        at_least("barren", 0),
        at_least("concealed", 0),
        Index("ix_breeding_plans_house", "house_entity_id"),
    )

    plan_id: Mapped[int] = mapped_column(ForeignKey("long_plans.id", ondelete="CASCADE"), primary_key=True)
    house_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    locus: Mapped[str | None] = mapped_column(String(NAME))
    allele: Mapped[str | None] = mapped_column(String(NAME))
    target_share: Mapped[int] = mapped_column(default=60)
    claim_polity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    matches: Mapped[int] = mapped_column(default=0)
    love_matches: Mapped[int] = mapped_column(default=0)
    barren: Mapped[int] = mapped_column(default=0)
    concealed: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ExaminationRow(Base):
    __tablename__ = "examinations"
    __table_args__ = (
        between("interval", 1, PERCENT_MAX),
        at_least("quota", 0),
        between("pass_mark", PERCENT_MIN, PERCENT_MAX),
        between("demand", PERCENT_MIN, PERCENT_MAX),
    )

    polity_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    interval: Mapped[int] = mapped_column(default=2)
    quota: Mapped[int] = mapped_column(default=20)
    pass_mark: Mapped[int] = mapped_column(default=50)
    demand: Mapped[int] = mapped_column(default=0)
    last_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ExamSittingRow(Base):
    __tablename__ = "exam_sittings"
    __table_args__ = (
        at_least("candidates", 0),
        at_least("passed", 0),
        between("mark", PERCENT_MIN, PERCENT_MAX),
        at_least("epoch", 0),
        Index("ix_exam_sittings_polity", "polity_entity_id", "epoch"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    polity_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    candidates: Mapped[int] = mapped_column(default=0)
    passed: Mapped[int] = mapped_column(default=0)
    mark: Mapped[int] = mapped_column(default=50)
    epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class CredentialRow(Base):
    __tablename__ = "credentials"
    __table_args__ = (at_least("epoch", 0), Index("ix_credentials_mortal", "mortal_entity_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    mortal_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    kind: Mapped[CredentialKind] = mapped_column(enum_type(CredentialKind, "kind"))
    granter_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    skill: Mapped[SkillKind | None] = mapped_column(enum_type(SkillKind, "skill"))
    epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class AcademicFreedomRow(Base):
    __tablename__ = "academic_freedom"
    __table_args__ = (between("level", PERCENT_MIN, PERCENT_MAX), at_least("updated_epoch", 0))

    structure_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    level: Mapped[int] = mapped_column(default=50)
    orthodoxy_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    suppressed: Mapped[bool] = mapped_column(default=False)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class SchoolLineageRow(Base):
    __tablename__ = "school_lineages"
    __table_args__ = (at_least("since_epoch", 0), Index("ix_school_lineages_doctrine", "doctrine_entity_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(NAME))
    doctrine_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    founder_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    rival_id: Mapped[int | None] = mapped_column(ForeignKey("school_lineages.id", ondelete="SET NULL"))
    persecuted: Mapped[bool] = mapped_column(default=False)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class SchoolMemberRow(Base):
    __tablename__ = "school_members"
    __table_args__ = (at_least("generation", 0), at_least("since_epoch", 0), Index("ix_school_members_mortal", "mortal_entity_id"))

    school_id: Mapped[int] = mapped_column(ForeignKey("school_lineages.id", ondelete="CASCADE"), primary_key=True)
    mortal_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    master_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    generation: Mapped[int] = mapped_column(default=0)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
