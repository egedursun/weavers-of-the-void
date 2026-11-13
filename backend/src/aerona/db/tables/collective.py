from sqlalchemy import JSON, CheckConstraint, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.collective import (
    AccountKind,
    AccountMedium,
    AccountStance,
    ArmsRim,
    CascadeOutcome,
    ChargeArrangement,
    CollectiveActKind,
    CollectiveTrigger,
    DatingSystemKind,
    DesignComponentKind,
    DesignKind,
    HeraldicCharge,
    HeraldicDivision,
    HeraldryHolderKind,
    MobEnd,
    MobStatus,
    MobTarget,
    NormBehaviour,
    NormSituation,
    PartitionLine,
    RoleEligibility,
    RoleKind,
    ShieldShape,
    SocialBias,
    StoryletId,
    StoryletStatus,
    SupporterPose,
    Tincture,
)
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.mind import EthicalStance, ValueAxis
from aerona.domain.enums.vehicles import FireControl, Propulsion, VehicleDomain, VehicleFamily, VehicleFrame, VehicleSize

KEY_LENGTH = 80
MOOD_FIELDS = ("anger", "anxiety", "fervour", "deterrence", "agitation", "last_trigger")
MOB_FIELDS = ("act", "size", "anger", "damage", "target", "target_entity_id", "leader_entity_id", "status")
MOVEMENT_FIELDS = ("act", "trigger", "members", "strength", "leader_entity_id", "cult_entity_id", "faction_entity_id", "ended_epoch")
ACCOUNT_FIELDS = ("kind", "fidelity", "credence", "defaced", "medium", "author_node_id", "subject_node_id")
STRIKE_FIELDS = ("active",)
MYTH_FIELDS = ("credence", "account_id")
COMMEMORATION_FIELDS = ("strength", "pride")
LOST_LAND_FIELDS = ("strength", "claimed_epoch")
STORYLET_FIELDS = ("status", "choice", "due_epoch", "chooser_node_id")
NORM_FIELDS = ("stance",)
BIAS_FIELDS = ("prestige_pct", "conformity_pct", "content_pct")
GENERATION_FIELDS = ("alive", "passed_epoch")
DIASPORA_FIELDS = ("population", "ties", "remittance", "home_entity_id")
TRANSITION_FIELDS = ("fertility_pct", "elder_share", "urban_share", "literacy")
SEX_RATIO_FIELDS = ("males_per_hundred", "widows")
ROLE_FIELDS = ("eligibility", "min_age", "classes", "stance")
DATING_FIELDS = ("kind", "anchor_year", "anchor_node_id", "cycle_years", "label_node_id")
ARMS_FIELDS = (
    "shape",
    "field",
    "division",
    "line",
    "second",
    "charge",
    "charge_tincture",
    "charge_two",
    "charge_two_tincture",
    "charge_three",
    "charge_three_tincture",
    "arrangement",
    "rim",
    "rim_line",
    "rim_tincture",
    "supporter",
    "supporter_pose",
    "supporter_tincture",
    "crest",
    "crest_tincture",
    "motto",
)
DESIGN_FIELDS = (
    "name",
    "description",
    "frame",
    "world_id",
    "origin_node_id",
    "owner_entity_id",
    "domain",
    "family",
    "propulsion",
    "size_class",
    "obsolete",
    "speed",
    "range",
    "seaworthiness",
    "cargo",
    "armament",
    "crew",
    "troops",
    "armour",
    "structure",
    "fuel",
    "fuel_use",
    "cost",
    "upkeep",
    "tech_level",
    "strangeness",
    "fire_control",
    "designer_entity_id",
)
COMPONENT_FIELDS = ("material_id", "size", "quality")
WEAR_FIELDS = ("wear",)


class CrowdMoodRow(Base):
    __tablename__ = "crowd_moods"
    __table_args__ = (
        between("anger", PERCENT_MIN, PERCENT_MAX),
        between("anxiety", PERCENT_MIN, PERCENT_MAX),
        between("fervour", PERCENT_MIN, PERCENT_MAX),
        between("deterrence", PERCENT_MIN, PERCENT_MAX),
        between("agitation", PERCENT_MIN, PERCENT_MAX),
    )

    settlement_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    anger: Mapped[int] = mapped_column(default=0)
    anxiety: Mapped[int] = mapped_column(default=0)
    fervour: Mapped[int] = mapped_column(default=0)
    deterrence: Mapped[int] = mapped_column(default=0)
    agitation: Mapped[int] = mapped_column(default=0)
    last_trigger: Mapped[CollectiveTrigger | None] = mapped_column(enum_type(CollectiveTrigger, "last_trigger"))
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class CascadeRow(Base):
    __tablename__ = "cascades"
    __table_args__ = (
        between("share", PERCENT_MIN, PERCENT_MAX),
        at_least("participants", 0),
        at_least("deaths", 0),
        at_least("epoch", 0),
        Index("ix_cascades_settlement", "settlement_entity_id", "epoch"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    settlement_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    district_id: Mapped[int | None] = mapped_column(ForeignKey("districts.id", ondelete="SET NULL"))
    trigger: Mapped[CollectiveTrigger] = mapped_column(enum_type(CollectiveTrigger, "trigger"))
    act: Mapped[CollectiveActKind] = mapped_column(enum_type(CollectiveActKind, "act"))
    participants: Mapped[int] = mapped_column(default=0)
    share: Mapped[int] = mapped_column(default=0)
    outcome: Mapped[CascadeOutcome] = mapped_column(enum_type(CascadeOutcome, "outcome"), default=CascadeOutcome.FIZZLED)
    deaths: Mapped[int] = mapped_column(default=0)
    fled: Mapped[int] = mapped_column(default=0)
    collection_id: Mapped[int | None] = mapped_column(ForeignKey("incident_collections.id", ondelete="SET NULL"))
    epoch: Mapped[int] = mapped_column(default=0)


class MobRow(Base):
    __tablename__ = "mobs"
    __table_args__ = (
        at_least("size", 0),
        between("anger", PERCENT_MIN, PERCENT_MAX),
        at_least("since_epoch", 0),
        at_least("damage", 0),
        Index("ix_mobs_settlement", "settlement_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    settlement_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    district_id: Mapped[int | None] = mapped_column(ForeignKey("districts.id", ondelete="SET NULL"))
    act: Mapped[CollectiveActKind] = mapped_column(enum_type(CollectiveActKind, "act"))
    size: Mapped[int] = mapped_column(default=0)
    anger: Mapped[int] = mapped_column(default=50)
    target: Mapped[MobTarget] = mapped_column(enum_type(MobTarget, "target"))
    target_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    leader_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    status: Mapped[MobStatus] = mapped_column(enum_type(MobStatus, "status"), default=MobStatus.GATHERING)
    ended_by: Mapped[MobEnd | None] = mapped_column(enum_type(MobEnd, "ended_by"))
    damage: Mapped[int] = mapped_column(default=0)
    cascade_id: Mapped[int | None] = mapped_column(ForeignKey("cascades.id", ondelete="SET NULL"))
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class MovementRow(Base):
    __tablename__ = "movements"
    __table_args__ = (
        at_least("members", 0),
        between("strength", PERCENT_MIN, PERCENT_MAX),
        at_least("since_epoch", 0),
        Index("ix_movements_settlement", "settlement_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    settlement_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    act: Mapped[CollectiveActKind] = mapped_column(enum_type(CollectiveActKind, "act"))
    trigger: Mapped[CollectiveTrigger] = mapped_column(enum_type(CollectiveTrigger, "trigger"))
    members: Mapped[int] = mapped_column(default=0)
    strength: Mapped[int] = mapped_column(default=30)
    leader_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    cult_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    faction_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    since_epoch: Mapped[int] = mapped_column(default=0)
    ended_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class AccountRow(Base):
    __tablename__ = "accounts"
    __table_args__ = (
        between("fidelity", PERCENT_MIN, PERCENT_MAX),
        between("credence", PERCENT_MIN, PERCENT_MAX),
        at_least("epoch", 0),
        Index("ix_accounts_holder", "holder_entity_id"),
        Index("ix_accounts_collection", "collection_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    holder_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    author_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    kind: Mapped[AccountKind] = mapped_column(enum_type(AccountKind, "kind"))
    medium: Mapped[AccountMedium] = mapped_column(enum_type(AccountMedium, "medium"), default=AccountMedium.ORAL)
    collection_id: Mapped[int | None] = mapped_column(ForeignKey("incident_collections.id", ondelete="CASCADE"))
    subject_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    structure_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    artwork_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    fidelity: Mapped[int] = mapped_column(default=80)
    credence: Mapped[int] = mapped_column(default=60)
    revised_from_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id", ondelete="SET NULL"))
    defaced: Mapped[bool] = mapped_column(default=False)
    epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class AccountStanceRow(Base):
    __tablename__ = "account_stances"

    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), primary_key=True)
    node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True, index=True)
    stance: Mapped[AccountStance] = mapped_column(enum_type(AccountStance, "stance"))


class MemoryStrikeRow(Base):
    __tablename__ = "memory_strikes"
    __table_args__ = (at_least("since_epoch", 0),)

    node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    by_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    active: Mapped[bool] = mapped_column(default=True)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class FoundingMythRow(Base):
    __tablename__ = "founding_myths"
    __table_args__ = (between("credence", PERCENT_MIN, PERCENT_MAX), at_least("since_epoch", 0))

    holder_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id", ondelete="SET NULL"))
    credence: Mapped[int] = mapped_column(default=70)
    debunked_epoch: Mapped[int | None]
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class CommemorationRow(Base):
    __tablename__ = "commemorations"
    __table_args__ = (between("strength", PERCENT_MIN, PERCENT_MAX), at_least("since_epoch", 0))

    holder_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    collection_id: Mapped[int] = mapped_column(ForeignKey("incident_collections.id", ondelete="CASCADE"), primary_key=True)
    pride: Mapped[bool] = mapped_column(default=True)
    strength: Mapped[int] = mapped_column(default=60)
    last_observed_epoch: Mapped[int | None]
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class LostLandRow(Base):
    __tablename__ = "lost_lands"
    __table_args__ = (between("strength", PERCENT_MIN, PERCENT_MAX), at_least("lost_epoch", 0))

    claimant_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    region_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    strength: Mapped[int] = mapped_column(default=50)
    lost_epoch: Mapped[int] = mapped_column(default=0)
    claimed_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class StoryletRunRow(Base):
    __tablename__ = "storylet_runs"
    __table_args__ = (at_least("opened_epoch", 0), Index("ix_storylet_runs_world", "world_id", "storylet"))

    id: Mapped[int] = mapped_column(primary_key=True)
    storylet: Mapped[StoryletId] = mapped_column(enum_type(StoryletId, "storylet"))
    world_id: Mapped[int | None] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"))
    cast: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    status: Mapped[StoryletStatus] = mapped_column(enum_type(StoryletStatus, "status"), default=StoryletStatus.OPEN)
    chooser_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    choice: Mapped[int | None]
    step: Mapped[int] = mapped_column(default=0)
    follows_run_id: Mapped[int | None] = mapped_column(ForeignKey("storylet_runs.id", ondelete="SET NULL"))
    collection_id: Mapped[int | None] = mapped_column(ForeignKey("incident_collections.id", ondelete="SET NULL"))
    due_epoch: Mapped[int | None]
    opened_epoch: Mapped[int] = mapped_column(default=0)
    resolved_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class SocialNormRow(Base):
    __tablename__ = "social_norms"
    __table_args__ = (at_least("since_epoch", 0),)

    holder_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    situation: Mapped[NormSituation] = mapped_column(enum_type(NormSituation, "situation"), primary_key=True)
    behaviour: Mapped[NormBehaviour] = mapped_column(enum_type(NormBehaviour, "behaviour"), primary_key=True)
    stance: Mapped[EthicalStance] = mapped_column(enum_type(EthicalStance, "stance"))
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class NormChangeRow(Base):
    __tablename__ = "norm_changes"
    __table_args__ = (
        at_least("epoch", 0),
        CheckConstraint("before IS NULL OR before <> after", name="a_change"),
        Index("ix_norm_changes_holder", "holder_entity_id", "epoch"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    holder_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    situation: Mapped[NormSituation] = mapped_column(enum_type(NormSituation, "situation"))
    behaviour: Mapped[NormBehaviour] = mapped_column(enum_type(NormBehaviour, "behaviour"))
    before: Mapped[EthicalStance | None] = mapped_column(enum_type(EthicalStance, "before"))
    after: Mapped[EthicalStance] = mapped_column(enum_type(EthicalStance, "after"))
    cause: Mapped[str] = mapped_column(String(KEY_LENGTH))
    epoch: Mapped[int] = mapped_column(default=0)


class LearningBiasRow(Base):
    __tablename__ = "learning_biases"
    __table_args__ = (
        between("prestige_pct", PERCENT_MIN, PERCENT_MAX),
        between("conformity_pct", PERCENT_MIN, PERCENT_MAX),
        between("content_pct", PERCENT_MIN, PERCENT_MAX),
    )

    holder_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    prestige_pct: Mapped[int] = mapped_column(default=40)
    conformity_pct: Mapped[int] = mapped_column(default=40)
    content_pct: Mapped[int] = mapped_column(default=20)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class LearningEventRow(Base):
    __tablename__ = "learning_events"
    __table_args__ = (at_least("epoch", 0), Index("ix_learning_events_learner", "learner_entity_id", "epoch"))

    id: Mapped[int] = mapped_column(primary_key=True)
    learner_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    model_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    bias: Mapped[SocialBias] = mapped_column(enum_type(SocialBias, "bias"))
    axis: Mapped[ValueAxis] = mapped_column(enum_type(ValueAxis, "axis"))
    shift: Mapped[int] = mapped_column(default=0)
    epoch: Mapped[int] = mapped_column(default=0)


class GenerationRow(Base):
    __tablename__ = "generations"
    __table_args__ = (at_least("generation_epoch", 0), at_least("alive", 0))

    community_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    generation_epoch: Mapped[int] = mapped_column(primary_key=True)
    formative: Mapped[list[str]] = mapped_column(JSON, default=list)
    value_shifts: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    alive: Mapped[int] = mapped_column(default=0)
    passed_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class DiasporaRow(Base):
    __tablename__ = "diasporas"
    __table_args__ = (at_least("population", 0), between("ties", PERCENT_MIN, PERCENT_MAX), at_least("remittance", 0), at_least("since_epoch", 0))

    people_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    host_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    home_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    population: Mapped[int] = mapped_column(default=0)
    ties: Mapped[int] = mapped_column(default=60)
    remittance: Mapped[int] = mapped_column(default=0)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class DemographicTransitionRow(Base):
    __tablename__ = "demographic_transitions"
    __table_args__ = (
        between("fertility_pct", 0, 200),
        between("elder_share", PERCENT_MIN, PERCENT_MAX),
        between("urban_share", PERCENT_MIN, PERCENT_MAX),
        between("literacy", PERCENT_MIN, PERCENT_MAX),
    )

    community_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    fertility_pct: Mapped[int] = mapped_column(default=100)
    elder_share: Mapped[int] = mapped_column(default=0)
    urban_share: Mapped[int] = mapped_column(default=0)
    literacy: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class SexRatioRow(Base):
    __tablename__ = "sex_ratios"
    __table_args__ = (between("males_per_hundred", 0, 1000), at_least("widows", 0))

    community_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    males_per_hundred: Mapped[int] = mapped_column(default=100)
    widows: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class RoleNormRow(Base):
    __tablename__ = "role_norms"
    __table_args__ = (between("min_age", 0, 200), at_least("since_epoch", 0))

    holder_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    role: Mapped[RoleKind] = mapped_column(enum_type(RoleKind, "role"), primary_key=True)
    eligibility: Mapped[RoleEligibility] = mapped_column(enum_type(RoleEligibility, "eligibility"), default=RoleEligibility.ANY)
    min_age: Mapped[int] = mapped_column(default=0)
    classes: Mapped[list[str]] = mapped_column(JSON, default=list)
    stance: Mapped[EthicalStance] = mapped_column(enum_type(EthicalStance, "stance"), default=EthicalStance.ACCEPTABLE)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class DatingSystemRow(Base):
    __tablename__ = "dating_systems"
    __table_args__ = (at_least("anchor_year", 0), at_least("cycle_years", 0), at_least("since_epoch", 0))

    holder_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    kind: Mapped[DatingSystemKind] = mapped_column(enum_type(DatingSystemKind, "kind"))
    anchor_year: Mapped[int] = mapped_column(default=0)
    anchor_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    label_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    cycle_years: Mapped[int] = mapped_column(default=0)
    reformed_epoch: Mapped[int | None]
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ArmsRow(Base):
    __tablename__ = "arms"
    __table_args__ = (at_least("since_epoch", 0),)

    holder_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    holder_kind: Mapped[HeraldryHolderKind] = mapped_column(enum_type(HeraldryHolderKind, "holder_kind"))
    shape: Mapped[ShieldShape] = mapped_column(enum_type(ShieldShape, "shape"), default=ShieldShape.HEATER, server_default=ShieldShape.HEATER.value)
    field: Mapped[Tincture] = mapped_column(enum_type(Tincture, "field"))
    division: Mapped[HeraldicDivision] = mapped_column(enum_type(HeraldicDivision, "division"), default=HeraldicDivision.PLAIN)
    line: Mapped[PartitionLine] = mapped_column(enum_type(PartitionLine, "line"), default=PartitionLine.STRAIGHT, server_default=PartitionLine.STRAIGHT.value)
    second: Mapped[Tincture | None] = mapped_column(enum_type(Tincture, "second"))
    charge: Mapped[HeraldicCharge] = mapped_column(enum_type(HeraldicCharge, "charge"), default=HeraldicCharge.NONE)
    charge_tincture: Mapped[Tincture | None] = mapped_column(enum_type(Tincture, "charge_tincture"))
    charge_two: Mapped[HeraldicCharge] = mapped_column(
        enum_type(HeraldicCharge, "charge_two"), default=HeraldicCharge.NONE, server_default=HeraldicCharge.NONE.value
    )
    charge_two_tincture: Mapped[Tincture | None] = mapped_column(enum_type(Tincture, "charge_two_tincture"))
    charge_three: Mapped[HeraldicCharge] = mapped_column(
        enum_type(HeraldicCharge, "charge_three"), default=HeraldicCharge.NONE, server_default=HeraldicCharge.NONE.value
    )
    charge_three_tincture: Mapped[Tincture | None] = mapped_column(enum_type(Tincture, "charge_three_tincture"))
    arrangement: Mapped[ChargeArrangement] = mapped_column(
        enum_type(ChargeArrangement, "arrangement"), default=ChargeArrangement.TWO_AND_ONE, server_default=ChargeArrangement.TWO_AND_ONE.value
    )
    rim: Mapped[ArmsRim] = mapped_column(enum_type(ArmsRim, "rim"), default=ArmsRim.LINE, server_default=ArmsRim.LINE.value)
    rim_line: Mapped[PartitionLine] = mapped_column(
        enum_type(PartitionLine, "rim_line"), default=PartitionLine.STRAIGHT, server_default=PartitionLine.STRAIGHT.value
    )
    rim_tincture: Mapped[Tincture | None] = mapped_column(enum_type(Tincture, "rim_tincture"))
    supporter: Mapped[HeraldicCharge] = mapped_column(
        enum_type(HeraldicCharge, "supporter"), default=HeraldicCharge.NONE, server_default=HeraldicCharge.NONE.value
    )
    supporter_pose: Mapped[SupporterPose] = mapped_column(
        enum_type(SupporterPose, "supporter_pose"), default=SupporterPose.CROSSED, server_default=SupporterPose.CROSSED.value
    )
    supporter_tincture: Mapped[Tincture | None] = mapped_column(enum_type(Tincture, "supporter_tincture"))
    crest: Mapped[HeraldicCharge] = mapped_column(enum_type(HeraldicCharge, "crest"), default=HeraldicCharge.NONE, server_default=HeraldicCharge.NONE.value)
    crest_tincture: Mapped[Tincture | None] = mapped_column(enum_type(Tincture, "crest_tincture"))
    motto: Mapped[str | None] = mapped_column(String(200))
    parent_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    quartered_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class DesignRow(Base):
    __tablename__ = "designs"
    __table_args__ = (
        at_least("troops", 0),
        between("armour", PERCENT_MIN, PERCENT_MAX),
        at_least("structure", 0),
        at_least("fuel_use", 0),
        at_least("cost", 0),
        at_least("upkeep", 0),
        between("tech_level", 0, 10),
        between("strangeness", PERCENT_MIN, PERCENT_MAX),
        Index("ix_designs_world", "world_id"),
        at_least("speed", 0),
        at_least("range", 0),
        between("seaworthiness", PERCENT_MIN, PERCENT_MAX),
        at_least("cargo", 0),
        at_least("armament", 0),
        at_least("crew", 0),
        at_least("mass", 0),
        at_least("epoch", 0),
        Index("ix_designs_owner", "owner_entity_id", "kind"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), unique=True)
    owner_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    kind: Mapped[DesignKind] = mapped_column(enum_type(DesignKind, "kind"))
    frame: Mapped[VehicleFrame | None] = mapped_column(enum_type(VehicleFrame, "frame"))
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    world_id: Mapped[int | None] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"))
    origin_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    domain: Mapped[VehicleDomain | None] = mapped_column(enum_type(VehicleDomain, "domain"))
    family: Mapped[VehicleFamily | None] = mapped_column(enum_type(VehicleFamily, "family"))
    propulsion: Mapped[Propulsion | None] = mapped_column(enum_type(Propulsion, "propulsion"))
    size_class: Mapped[VehicleSize] = mapped_column(enum_type(VehicleSize, "size_class"), default=VehicleSize.MEDIUM, server_default=VehicleSize.MEDIUM.value)
    troops: Mapped[int] = mapped_column(default=0, server_default="0")
    armour: Mapped[int] = mapped_column(default=0, server_default="0")
    structure: Mapped[int] = mapped_column(default=30, server_default="30")
    fuel: Mapped[CommodityKind | None] = mapped_column(enum_type(CommodityKind, "fuel"))
    fuel_use: Mapped[int] = mapped_column(default=0, server_default="0")
    cost: Mapped[int] = mapped_column(default=0, server_default="0")
    upkeep: Mapped[int] = mapped_column(default=0, server_default="0")
    tech_level: Mapped[int] = mapped_column(default=0, server_default="0")
    strangeness: Mapped[int] = mapped_column(default=0, server_default="0")
    fire_control: Mapped[FireControl] = mapped_column(
        enum_type(FireControl, "fire_control"), default=FireControl.MANUAL, server_default=FireControl.MANUAL.value
    )
    designer_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    parent_design_id: Mapped[int | None] = mapped_column(ForeignKey("designs.id", ondelete="SET NULL"))
    mass: Mapped[int] = mapped_column(default=0)
    speed: Mapped[int] = mapped_column(default=0)
    range: Mapped[int] = mapped_column(default=0)
    seaworthiness: Mapped[int] = mapped_column(default=0)
    cargo: Mapped[int] = mapped_column(default=0)
    armament: Mapped[int] = mapped_column(default=0)
    crew: Mapped[int] = mapped_column(default=0)
    obsolete: Mapped[bool] = mapped_column(default=False)
    epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class DesignComponentRow(Base):
    __tablename__ = "design_components"
    __table_args__ = (between("size", 0, 10), between("quality", PERCENT_MIN, PERCENT_MAX))

    design_id: Mapped[int] = mapped_column(ForeignKey("designs.id", ondelete="CASCADE"), primary_key=True)
    component: Mapped[DesignComponentKind] = mapped_column(enum_type(DesignComponentKind, "component"), primary_key=True)
    material_id: Mapped[int | None] = mapped_column(ForeignKey("world_materials.id", ondelete="SET NULL"))
    size: Mapped[int] = mapped_column(default=3)
    quality: Mapped[int] = mapped_column(default=50)


class ComponentWearRow(Base):
    __tablename__ = "component_wear"
    __table_args__ = (between("wear", PERCENT_MIN, PERCENT_MAX),)

    vessel_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    component: Mapped[DesignComponentKind] = mapped_column(enum_type(DesignComponentKind, "component"), primary_key=True)
    wear: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
