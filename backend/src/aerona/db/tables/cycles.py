from sqlalchemy import JSON, CheckConstraint, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.cycles import (
    AdoptionKind,
    ChallengeKind,
    ChallengeResponse,
    CyclePhase,
    DescentGroup,
    GiftOccasion,
    GiftState,
    KinshipDescent,
    KinTermSystem,
    LabourRegime,
    LegacyKind,
    LongPlanKind,
    LongPlanStatus,
    ManumissionPath,
    MobilityMode,
    ReproductiveCaste,
    ReproductiveSystem,
    ResidenceRule,
)
from aerona.domain.enums.demography import Sex
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN

NAME = 200
STRESS_FIELDS = ("pressure", "immiseration", "elite_overproduction", "fiscal_distress", "aspirants", "positions", "challenge", "phase")
ASABIYYA_FIELDS = ("value", "frontier", "luxury_generations", "conflict")
PLAN_FIELDS = ("name", "kind", "target_node_id", "carrier_node_id", "steps", "progress", "step_cost", "secrecy", "exposed", "status")
GIFT_FIELDS = ("value", "occasion", "item_entity_id", "state", "due_epoch")
CIRCUIT_FIELDS = ("name", "item_entity_id", "position", "passes")
DEBT_FIELDS = ("offered", "answered")
KINSHIP_FIELDS = (
    "descent",
    "residence",
    "descent_group",
    "kin_terms",
    "adoption",
    "first_side",
    "sibling_union_first",
    "sibling_union_second",
)
ALLIANCE_FIELDS = ("marriages", "treaty_id")
REPRODUCTION_FIELDS = ("system", "change_age", "breeder_pct", "soldier_pct", "worker_pct")
CASTE_FIELDS = ("caste",)
CAMP_FIELDS = ("mode", "season_index", "herd", "grazing", "water")
CONFEDERATION_FIELDS = ("name", "leader_entity_id", "dissolved_epoch")
INDENTURE_FIELDS = ("employer_node_id", "regime", "count", "term_epochs", "debt", "exploitation", "origin_entity_id")
MARKET_FIELDS = ("price", "stock", "sold", "open")
READING_FIELDS = ("pressure", "immiseration", "elite_overproduction", "fiscal_distress", "psi", "phase")
CHALLENGE_FIELDS = ("kind", "severity", "response", "source_node_id")
LEGACY_FIELDS = ("predecessor_entity_id",)
MANUMISSION_FIELDS = ("count", "path", "standing", "origin_entity_id")


class PolityStressRow(Base):
    __tablename__ = "polity_stress"
    __table_args__ = (
        between("pressure", PERCENT_MIN, PERCENT_MAX),
        between("immiseration", PERCENT_MIN, PERCENT_MAX),
        between("elite_overproduction", PERCENT_MIN, PERCENT_MAX),
        between("fiscal_distress", PERCENT_MIN, PERCENT_MAX),
        between("psi", PERCENT_MIN, PERCENT_MAX),
        between("challenge", PERCENT_MIN, PERCENT_MAX),
        at_least("aspirants", 0),
        at_least("positions", 0),
        at_least("updated_epoch", 0),
    )

    polity_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    pressure: Mapped[int] = mapped_column(default=0)
    immiseration: Mapped[int] = mapped_column(default=0)
    elite_overproduction: Mapped[int] = mapped_column(default=0)
    fiscal_distress: Mapped[int] = mapped_column(default=0)
    psi: Mapped[int] = mapped_column(default=0)
    aspirants: Mapped[int] = mapped_column(default=0)
    positions: Mapped[int] = mapped_column(default=0)
    challenge: Mapped[int] = mapped_column(default=0)
    phase: Mapped[CyclePhase] = mapped_column(enum_type(CyclePhase, "phase"), default=CyclePhase.GROWTH)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class StressReadingRow(Base):
    __tablename__ = "stress_readings"
    __table_args__ = (
        between("pressure", PERCENT_MIN, PERCENT_MAX),
        between("immiseration", PERCENT_MIN, PERCENT_MAX),
        between("elite_overproduction", PERCENT_MIN, PERCENT_MAX),
        between("fiscal_distress", PERCENT_MIN, PERCENT_MAX),
        between("psi", PERCENT_MIN, PERCENT_MAX),
        at_least("epoch", 0),
    )

    polity_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    epoch: Mapped[int] = mapped_column(primary_key=True)
    pressure: Mapped[int] = mapped_column(default=0)
    immiseration: Mapped[int] = mapped_column(default=0)
    elite_overproduction: Mapped[int] = mapped_column(default=0)
    fiscal_distress: Mapped[int] = mapped_column(default=0)
    psi: Mapped[int] = mapped_column(default=0)
    phase: Mapped[CyclePhase] = mapped_column(enum_type(CyclePhase, "phase"), default=CyclePhase.GROWTH)


class AsabiyyaRow(Base):
    __tablename__ = "asabiyya"
    __table_args__ = (
        between("value", PERCENT_MIN, PERCENT_MAX),
        between("conflict", PERCENT_MIN, PERCENT_MAX),
        at_least("frontier", 0),
        at_least("luxury_generations", 0),
        at_least("updated_epoch", 0),
    )

    holder_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    value: Mapped[int] = mapped_column(default=50)
    frontier: Mapped[int] = mapped_column(default=0)
    luxury_generations: Mapped[int] = mapped_column(default=0)
    conflict: Mapped[int] = mapped_column(default=0)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ChallengeRow(Base):
    __tablename__ = "challenges"
    __table_args__ = (between("severity", PERCENT_MIN, PERCENT_MAX), at_least("epoch", 0), Index("ix_challenges_holder", "holder_entity_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    holder_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    kind: Mapped[ChallengeKind] = mapped_column(enum_type(ChallengeKind, "kind"))
    severity: Mapped[int] = mapped_column(default=0)
    response: Mapped[ChallengeResponse] = mapped_column(enum_type(ChallengeResponse, "response"), default=ChallengeResponse.RESPONSE)
    source_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    epoch: Mapped[int] = mapped_column(default=0)


class LongPlanRow(Base):
    __tablename__ = "long_plans"
    __table_args__ = (
        at_least("steps", 1),
        at_least("progress", 0),
        at_least("step_cost", 0),
        between("secrecy", PERCENT_MIN, PERCENT_MAX),
        at_least("started_epoch", 0),
        CheckConstraint("progress <= steps", name="progress_within_steps"),
        Index("ix_long_plans_holder", "holder_node_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    holder_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    author_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    carrier_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    target_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    kind: Mapped[LongPlanKind] = mapped_column(enum_type(LongPlanKind, "kind"))
    name: Mapped[str] = mapped_column(String(NAME))
    steps: Mapped[int] = mapped_column(default=10)
    progress: Mapped[int] = mapped_column(default=0)
    step_cost: Mapped[int] = mapped_column(default=10)
    secrecy: Mapped[int] = mapped_column(default=50)
    exposed: Mapped[bool] = mapped_column(default=False)
    status: Mapped[LongPlanStatus] = mapped_column(enum_type(LongPlanStatus, "status"), default=LongPlanStatus.ACTIVE)
    started_epoch: Mapped[int] = mapped_column(default=0)
    finished_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class GiftRow(Base):
    __tablename__ = "gifts"
    __table_args__ = (
        at_least("value", 0),
        at_least("epoch", 0),
        CheckConstraint("giver_node_id <> receiver_node_id", name="two_sides"),
        Index("ix_gifts_giver", "giver_node_id"),
        Index("ix_gifts_receiver", "receiver_node_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    giver_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    receiver_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    value: Mapped[int] = mapped_column(default=10)
    occasion: Mapped[GiftOccasion] = mapped_column(enum_type(GiftOccasion, "occasion"), default=GiftOccasion.COURTESY)
    item_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    state: Mapped[GiftState] = mapped_column(enum_type(GiftState, "state"), default=GiftState.OPEN)
    answers_gift_id: Mapped[int | None] = mapped_column(ForeignKey("gifts.id", ondelete="SET NULL"))
    due_epoch: Mapped[int | None]
    settled_epoch: Mapped[int | None]
    epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class CircuitRow(Base):
    __tablename__ = "ceremonial_circuits"
    __table_args__ = (at_least("position", 0), at_least("passes", 0), at_least("started_epoch", 0))

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(NAME))
    item_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    stops: Mapped[list[int]] = mapped_column(JSON, default=list)
    position: Mapped[int] = mapped_column(default=0)
    passes: Mapped[int] = mapped_column(default=0)
    started_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class DivineDebtRow(Base):
    __tablename__ = "divine_debts"
    __table_args__ = (at_least("offered", 0), at_least("answered", 0), Index("ix_divine_debts_community", "community_entity_id"))

    god_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    community_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    offered: Mapped[int] = mapped_column(default=0)
    answered: Mapped[int] = mapped_column(default=0)
    last_offering_epoch: Mapped[int | None]
    last_answer_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class KinshipSystemRow(Base):
    __tablename__ = "kinship_systems"

    people_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    descent: Mapped[KinshipDescent] = mapped_column(enum_type(KinshipDescent, "descent"), default=KinshipDescent.BILATERAL)
    residence: Mapped[ResidenceRule] = mapped_column(enum_type(ResidenceRule, "residence"), default=ResidenceRule.NEW_HOUSEHOLD)
    descent_group: Mapped[DescentGroup] = mapped_column(enum_type(DescentGroup, "descent_group"), default=DescentGroup.LINEAGE)
    kin_terms: Mapped[KinTermSystem] = mapped_column(
        "cousin_terms", enum_type(KinTermSystem, "cousin_terms"), default=KinTermSystem.LINEAL, server_default=KinTermSystem.LINEAL.value
    )
    first_side: Mapped[Sex] = mapped_column(enum_type(Sex, "first_side"), default=Sex.MALE, server_default=Sex.MALE.value)
    adoption: Mapped[AdoptionKind] = mapped_column(enum_type(AdoptionKind, "adoption"), default=AdoptionKind.FOSTER, server_default=AdoptionKind.FOSTER.value)
    sibling_union_first: Mapped[bool] = mapped_column(default=False)
    sibling_union_second: Mapped[bool] = mapped_column(default=False)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class MarriageAllianceRow(Base):
    __tablename__ = "marriage_alliances"
    __table_args__ = (
        at_least("marriages", 0),
        at_least("since_epoch", 0),
        CheckConstraint("giver_entity_id <> taker_entity_id", name="two_lines"),
        Index("ix_marriage_alliances_taker", "taker_entity_id"),
    )

    giver_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    taker_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    marriages: Mapped[int] = mapped_column(default=0)
    treaty_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    since_epoch: Mapped[int] = mapped_column(default=0)
    last_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class PeopleReproductionRow(Base):
    __tablename__ = "people_reproduction"
    __table_args__ = (
        at_least("change_age", 0),
        between("breeder_pct", PERCENT_MIN, PERCENT_MAX),
        between("soldier_pct", PERCENT_MIN, PERCENT_MAX),
        between("worker_pct", PERCENT_MIN, PERCENT_MAX),
    )

    people_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    system: Mapped[ReproductiveSystem] = mapped_column(enum_type(ReproductiveSystem, "system"), default=ReproductiveSystem.TWO_SEX)
    change_age: Mapped[int] = mapped_column(default=40)
    breeder_pct: Mapped[int] = mapped_column(default=10)
    soldier_pct: Mapped[int] = mapped_column(default=20)
    worker_pct: Mapped[int] = mapped_column(default=70)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class MortalCasteRow(Base):
    __tablename__ = "mortal_castes"
    __table_args__ = (at_least("since_epoch", 0),)

    mortal_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    caste: Mapped[ReproductiveCaste] = mapped_column(enum_type(ReproductiveCaste, "caste"))
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class CampRow(Base):
    __tablename__ = "camps"
    __table_args__ = (
        at_least("season_index", 0),
        at_least("herd", 0),
        between("grazing", PERCENT_MIN, PERCENT_MAX),
        between("water", PERCENT_MIN, PERCENT_MAX),
    )

    settlement_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    mode: Mapped[MobilityMode] = mapped_column(enum_type(MobilityMode, "mode"), default=MobilityMode.NOMADIC)
    circuit: Mapped[list[int]] = mapped_column(JSON, default=list)
    season_index: Mapped[int] = mapped_column(default=0)
    herd: Mapped[int] = mapped_column(default=100)
    grazing: Mapped[int] = mapped_column(default=50)
    water: Mapped[int] = mapped_column(default=50)
    last_moved_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ConfederationRow(Base):
    __tablename__ = "confederations"
    __table_args__ = (at_least("formed_epoch", 0),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(NAME))
    leader_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    members: Mapped[list[int]] = mapped_column(JSON, default=list)
    formed_epoch: Mapped[int] = mapped_column(default=0)
    dissolved_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class LegacyTraitRow(Base):
    __tablename__ = "legacy_traits"
    __table_args__ = (at_least("since_epoch", 0),)

    people_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    kind: Mapped[LegacyKind] = mapped_column(enum_type(LegacyKind, "kind"), primary_key=True)
    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    predecessor_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class IndentureRow(Base):
    __tablename__ = "indentures"
    __table_args__ = (
        at_least("count", 0),
        at_least("term_epochs", 0),
        at_least("debt", 0),
        between("exploitation", PERCENT_MIN, PERCENT_MAX),
        at_least("since_epoch", 0),
        Index("ix_indentures_community", "community_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    community_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    employer_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    regime: Mapped[LabourRegime] = mapped_column(enum_type(LabourRegime, "regime"), default=LabourRegime.INDENTURE)
    count: Mapped[int] = mapped_column(default=0)
    term_epochs: Mapped[int] = mapped_column(default=3)
    debt: Mapped[int] = mapped_column(default=0)
    exploitation: Mapped[int] = mapped_column(default=30)
    origin_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class SlaveMarketRow(Base):
    __tablename__ = "slave_markets"
    __table_args__ = (at_least("price", 0), at_least("stock", 0), at_least("sold", 0), at_least("updated_epoch", 0))

    settlement_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    price: Mapped[int] = mapped_column(default=20)
    stock: Mapped[int] = mapped_column(default=0)
    sold: Mapped[int] = mapped_column(default=0)
    open: Mapped[bool] = mapped_column(default=True)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ManumissionRow(Base):
    __tablename__ = "manumissions"
    __table_args__ = (
        at_least("count", 0),
        between("standing", PERCENT_MIN, PERCENT_MAX),
        at_least("epoch", 0),
        Index("ix_manumissions_community", "community_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    community_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    count: Mapped[int] = mapped_column(default=0)
    path: Mapped[ManumissionPath] = mapped_column(enum_type(ManumissionPath, "path"))
    standing: Mapped[int] = mapped_column(default=40)
    origin_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
