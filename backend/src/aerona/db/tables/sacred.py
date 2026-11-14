from sqlalchemy import JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.culture import ProphecyPredicate
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.mind import Emotion
from aerona.domain.enums.sacred import (
    AfterlifeModel,
    BureauRank,
    DivinationKind,
    DivinationQuestion,
    DivinationValidity,
    ForesightSource,
    ForesightStatus,
    GeniusLocusKind,
    MillenarianStage,
    MysticState,
    OmenVerdict,
    PetitionKind,
    PetitionStatus,
    SacramentKind,
    SacramentProtection,
    SpiritOffence,
    TheodicyCause,
    TheodicyResolution,
    VisionKind,
)

PULL_MIN = -100
PULL_MAX = 100
GENIUS_FIELDS = ("place_entity_id", "community_entity_id", "kind", "temperament", "contentment", "offerings", "owed", "favour", "offended")
OFFICE_FIELDS = ("rank", "superior_spirit_id", "overseer_node_id", "jurisdiction_entity_id", "merit", "corruption", "resolved", "neglected", "dismissed")
PETITION_FIELDS = ("office_spirit_id", "kind", "defendant_spirit_id", "bribe", "status", "due_epoch", "appealed_to_id")
MYSTIC_FIELDS = (
    "state",
    "visions",
    "genuine_visions",
    "followers",
    "answered_by_node_id",
    "cult_entity_id",
    "founded_entity_id",
    "reverence",
    "persecution",
)
VISION_FIELDS = ("kind", "sender_node_id", "genuine", "awe")
MILLENARIAN_FIELDS = (
    "cult_entity_id",
    "prophet_entity_id",
    "prophecy_entity_id",
    "stage",
    "end_epoch",
    "members",
    "conviction",
    "given_up",
    "idle_share",
    "attacks",
    "dates_set",
    "sect_entity_id",
)
THEODICY_FIELDS = ("god_node_id", "cause", "suffering", "answered", "resolution", "theologian_entity_id")
DOCTRINE_SACRAMENT_FIELDS = ("protection", "strength")
SACRAMENT_FIELDS = ("kind", "cult_entity_id", "priest_entity_id", "missed")
AFTERLIFE_FIELDS = ("model", "aligned", "aligned_by_node_id", "shocks", "testimonies", "doubt")
CLIMATE_FIELDS = (
    "piety_drift",
    "literacy_pull",
    "science_pull",
    "prosperity_pull",
    "city_pull",
    "silence_pull",
    "disaster_push",
    "miracle_push",
    "war_push",
    "dominion_push",
    "silent_epochs",
    "godless",
)
SYSTEM_FIELDS = ("kind", "validity", "trust", "diviners")
DIVINATION_FIELDS = ("diviner_entity_id", "client_entity_id", "question", "verdict", "true_verdict", "heeded", "swayed_by_node_id")
FORESIGHT_FIELDS = ("subject_node_id", "predicate", "horizon", "due_epoch", "certainty", "source", "status")
MODEL_FIELDS = ("subject_entity_id", "archive", "accuracy", "forecast_psi", "actual_psi", "plan_id", "disruption", "disrupted_by_node_id", "horizon")
FEEDING_FIELDS = ("weight",)


class GeniusLocusRow(Base):
    __tablename__ = "genius_loci"
    __table_args__ = (
        between("temperament", PERCENT_MIN, PERCENT_MAX),
        between("contentment", PERCENT_MIN, PERCENT_MAX),
        between("favour", PERCENT_MIN, PERCENT_MAX),
        at_least("offerings", 0),
        at_least("owed", 0),
        Index("ix_genius_loci_place", "place_entity_id"),
        Index("ix_genius_loci_community", "community_entity_id"),
    )

    spirit_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    place_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    community_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    kind: Mapped[GeniusLocusKind] = mapped_column(enum_type(GeniusLocusKind, "kind"))
    temperament: Mapped[int] = mapped_column(default=50)
    contentment: Mapped[int] = mapped_column(default=60)
    offerings: Mapped[int] = mapped_column(default=0)
    owed: Mapped[int] = mapped_column(default=0)
    favour: Mapped[int] = mapped_column(default=0)
    offended: Mapped[SpiritOffence | None] = mapped_column(enum_type(SpiritOffence, "offended"))
    last_offering_epoch: Mapped[int | None]
    bound_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class SpiritOfficeRow(Base):
    __tablename__ = "spirit_offices"
    __table_args__ = (
        at_least("merit", 0),
        between("corruption", PERCENT_MIN, PERCENT_MAX),
        at_least("resolved", 0),
        at_least("neglected", 0),
        Index("ix_spirit_offices_superior", "superior_spirit_id"),
        Index("ix_spirit_offices_overseer", "overseer_node_id"),
        Index("ix_spirit_offices_jurisdiction", "jurisdiction_entity_id"),
    )

    spirit_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    rank: Mapped[BureauRank] = mapped_column(enum_type(BureauRank, "rank"), default=BureauRank.LOCAL)
    superior_spirit_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    overseer_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    jurisdiction_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    merit: Mapped[int] = mapped_column(default=0)
    corruption: Mapped[int] = mapped_column(default=0)
    resolved: Mapped[int] = mapped_column(default=0)
    neglected: Mapped[int] = mapped_column(default=0)
    dismissed: Mapped[bool] = mapped_column(default=False)
    appointed_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class PetitionRow(Base):
    __tablename__ = "petitions"
    __table_args__ = (
        at_least("bribe", 0),
        at_least("filed_epoch", 0),
        Index("ix_petitions_office", "office_spirit_id", "status"),
        Index("ix_petitions_petitioner", "petitioner_node_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    petitioner_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    office_spirit_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    kind: Mapped[PetitionKind] = mapped_column(enum_type(PetitionKind, "kind"))
    defendant_spirit_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    bribe: Mapped[int] = mapped_column(default=0)
    status: Mapped[PetitionStatus] = mapped_column(enum_type(PetitionStatus, "status"), default=PetitionStatus.FILED)
    filed_epoch: Mapped[int] = mapped_column(default=0)
    due_epoch: Mapped[int] = mapped_column(default=0)
    resolved_epoch: Mapped[int | None]
    appealed_to_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class MysticRow(Base):
    __tablename__ = "mystics"
    __table_args__ = (
        at_least("visions", 0),
        at_least("genuine_visions", 0),
        at_least("followers", 0),
        between("reverence", PERCENT_MIN, PERCENT_MAX),
        between("persecution", PERCENT_MIN, PERCENT_MAX),
        Index("ix_mystics_cult", "cult_entity_id"),
    )

    mortal_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    state: Mapped[MysticState] = mapped_column(enum_type(MysticState, "state"), default=MysticState.SEEKER)
    visions: Mapped[int] = mapped_column(default=0)
    genuine_visions: Mapped[int] = mapped_column(default=0)
    followers: Mapped[int] = mapped_column(default=0)
    answered_by_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    cult_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    founded_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    reverence: Mapped[int] = mapped_column(default=0)
    persecution: Mapped[int] = mapped_column(default=0)
    since_epoch: Mapped[int] = mapped_column(default=0)
    last_vision_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class VisionRow(Base):
    __tablename__ = "visions"
    __table_args__ = (between("awe", PERCENT_MIN, PERCENT_MAX), at_least("epoch", 0), Index("ix_visions_mystic", "mystic_entity_id", "epoch"))

    id: Mapped[int] = mapped_column(primary_key=True)
    mystic_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    epoch: Mapped[int]
    kind: Mapped[VisionKind] = mapped_column(enum_type(VisionKind, "kind"))
    sender_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    genuine: Mapped[bool] = mapped_column(default=False)
    awe: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class MillenarianRow(Base):
    __tablename__ = "millenarian_movements"
    __table_args__ = (
        at_least("members", 0),
        between("conviction", PERCENT_MIN, PERCENT_MAX),
        at_least("given_up", 0),
        between("idle_share", PERCENT_MIN, PERCENT_MAX),
        at_least("attacks", 0),
        at_least("dates_set", 0),
        at_least("since_epoch", 0),
        Index("ix_millenarian_movements_settlement", "settlement_entity_id"),
        Index("ix_millenarian_movements_cult", "cult_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    settlement_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    cult_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    prophet_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    prophecy_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    movement_id: Mapped[int | None] = mapped_column(ForeignKey("movements.id", ondelete="SET NULL"))
    stage: Mapped[MillenarianStage] = mapped_column(enum_type(MillenarianStage, "stage"), default=MillenarianStage.STIRRING)
    end_epoch: Mapped[int] = mapped_column(default=0)
    members: Mapped[int] = mapped_column(default=0)
    conviction: Mapped[int] = mapped_column(default=50)
    given_up: Mapped[int] = mapped_column(default=0)
    idle_share: Mapped[int] = mapped_column(default=0)
    attacks: Mapped[int] = mapped_column(default=0)
    dates_set: Mapped[int] = mapped_column(default=1)
    sect_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    since_epoch: Mapped[int] = mapped_column(default=0)
    ended_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class TheodicyCrisisRow(Base):
    __tablename__ = "theodicy_crises"
    __table_args__ = (
        between("suffering", PERCENT_MIN, PERCENT_MAX),
        at_least("started_epoch", 0),
        Index("ix_theodicy_crises_cult", "cult_entity_id"),
        Index("ix_theodicy_crises_community", "community_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    cult_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    community_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    god_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    cause: Mapped[TheodicyCause] = mapped_column(enum_type(TheodicyCause, "cause"))
    suffering: Mapped[int] = mapped_column(default=0)
    answered: Mapped[bool] = mapped_column(default=False)
    resolution: Mapped[TheodicyResolution] = mapped_column(enum_type(TheodicyResolution, "resolution"), default=TheodicyResolution.PENDING)
    theologian_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    started_epoch: Mapped[int] = mapped_column(default=0)
    resolved_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class DoctrineSacramentRow(Base):
    __tablename__ = "doctrine_sacraments"
    __table_args__ = (between("strength", PERCENT_MIN, PERCENT_MAX),)

    cult_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    kind: Mapped[SacramentKind] = mapped_column(enum_type(SacramentKind, "kind"), primary_key=True)
    protection: Mapped[SacramentProtection] = mapped_column(enum_type(SacramentProtection, "protection"))
    strength: Mapped[int] = mapped_column(default=50)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class SacramentRow(Base):
    __tablename__ = "sacraments"
    __table_args__ = (at_least("epoch", 0), Index("ix_sacraments_mortal", "mortal_entity_id", "kind"), Index("ix_sacraments_cult", "cult_entity_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    mortal_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    kind: Mapped[SacramentKind] = mapped_column(enum_type(SacramentKind, "kind"))
    cult_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    priest_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    epoch: Mapped[int]
    missed: Mapped[bool] = mapped_column(default=False)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class DoctrineAfterlifeRow(Base):
    __tablename__ = "doctrine_afterlives"
    __table_args__ = (at_least("shocks", 0), at_least("testimonies", 0), between("doubt", PERCENT_MIN, PERCENT_MAX))

    cult_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    model: Mapped[AfterlifeModel] = mapped_column(enum_type(AfterlifeModel, "model"))
    aligned: Mapped[bool] = mapped_column(default=False)
    aligned_by_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    shocks: Mapped[int] = mapped_column(default=0)
    testimonies: Mapped[int] = mapped_column(default=0)
    doubt: Mapped[int] = mapped_column(default=0)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class FaithClimateRow(Base):
    __tablename__ = "faith_climates"
    __table_args__ = (
        between("piety_drift", PULL_MIN, PULL_MAX),
        between("literacy_pull", PULL_MIN, PULL_MAX),
        between("science_pull", PULL_MIN, PULL_MAX),
        between("prosperity_pull", PULL_MIN, PULL_MAX),
        between("city_pull", PULL_MIN, PULL_MAX),
        between("silence_pull", PULL_MIN, PULL_MAX),
        between("disaster_push", PULL_MIN, PULL_MAX),
        between("miracle_push", PULL_MIN, PULL_MAX),
        between("war_push", PULL_MIN, PULL_MAX),
        between("dominion_push", PULL_MIN, PULL_MAX),
        at_least("silent_epochs", 0),
    )

    community_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    piety_drift: Mapped[int] = mapped_column(default=0)
    literacy_pull: Mapped[int] = mapped_column(default=0)
    science_pull: Mapped[int] = mapped_column(default=0)
    prosperity_pull: Mapped[int] = mapped_column(default=0)
    city_pull: Mapped[int] = mapped_column(default=0)
    silence_pull: Mapped[int] = mapped_column(default=0)
    disaster_push: Mapped[int] = mapped_column(default=0)
    miracle_push: Mapped[int] = mapped_column(default=0)
    war_push: Mapped[int] = mapped_column(default=0)
    dominion_push: Mapped[int] = mapped_column(default=0)
    silent_epochs: Mapped[int] = mapped_column(default=0)
    godless: Mapped[bool] = mapped_column(default=False)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class DivinationSystemRow(Base):
    __tablename__ = "divination_systems"
    __table_args__ = (
        between("trust", PERCENT_MIN, PERCENT_MAX),
        at_least("diviners", 0),
        at_least("founded_epoch", 0),
        Index("ix_divination_systems_people", "people_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    people_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    kind: Mapped[DivinationKind] = mapped_column(enum_type(DivinationKind, "kind"))
    validity: Mapped[DivinationValidity] = mapped_column(enum_type(DivinationValidity, "validity"), default=DivinationValidity.NOISE)
    trust: Mapped[int] = mapped_column(default=50)
    diviners: Mapped[int] = mapped_column(default=1)
    founded_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class DivinationRow(Base):
    __tablename__ = "divinations"
    __table_args__ = (at_least("epoch", 0), Index("ix_divinations_system", "system_id"), Index("ix_divinations_client", "client_entity_id", "epoch"))

    id: Mapped[int] = mapped_column(primary_key=True)
    system_id: Mapped[int] = mapped_column(ForeignKey("divination_systems.id", ondelete="CASCADE"))
    diviner_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    client_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    question: Mapped[DivinationQuestion] = mapped_column(enum_type(DivinationQuestion, "question"))
    verdict: Mapped[OmenVerdict] = mapped_column(enum_type(OmenVerdict, "verdict"))
    true_verdict: Mapped[OmenVerdict] = mapped_column(enum_type(OmenVerdict, "true_verdict"))
    heeded: Mapped[bool] = mapped_column(default=False)
    swayed_by_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    epoch: Mapped[int]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ForesightRow(Base):
    __tablename__ = "foresights"
    __table_args__ = (
        between("certainty", PERCENT_MIN, PERCENT_MAX),
        at_least("horizon", 0),
        at_least("made_epoch", 0),
        Index("ix_foresights_seer", "seer_node_id", "status"),
        Index("ix_foresights_due", "status", "due_epoch"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    seer_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    subject_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    predicate: Mapped[ProphecyPredicate] = mapped_column(enum_type(ProphecyPredicate, "predicate"))
    args: Mapped[dict[str, int | str]] = mapped_column(JSON, default=dict)
    horizon: Mapped[int] = mapped_column(default=1)
    due_epoch: Mapped[int] = mapped_column(default=0)
    certainty: Mapped[int] = mapped_column(default=50)
    source: Mapped[ForesightSource] = mapped_column(enum_type(ForesightSource, "source"))
    divination_id: Mapped[int | None] = mapped_column(ForeignKey("divinations.id", ondelete="SET NULL"))
    status: Mapped[ForesightStatus] = mapped_column(enum_type(ForesightStatus, "status"), default=ForesightStatus.PENDING)
    checked_epoch: Mapped[int | None]
    made_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ForecastModelRow(Base):
    __tablename__ = "forecast_models"
    __table_args__ = (
        at_least("archive", 0),
        between("accuracy", PERCENT_MIN, PERCENT_MAX),
        between("forecast_psi", PERCENT_MIN, PERCENT_MAX),
        between("actual_psi", PERCENT_MIN, PERCENT_MAX),
        between("disruption", PERCENT_MIN, PERCENT_MAX),
        at_least("horizon", 0),
        Index("ix_forecast_models_order", "order_entity_id"),
        Index("ix_forecast_models_subject", "subject_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    order_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    subject_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    archive: Mapped[int] = mapped_column(default=0)
    accuracy: Mapped[int] = mapped_column(default=0)
    forecast_psi: Mapped[int] = mapped_column(default=0)
    actual_psi: Mapped[int] = mapped_column(default=0)
    plan_id: Mapped[int | None] = mapped_column(ForeignKey("long_plans.id", ondelete="SET NULL"))
    disruption: Mapped[int] = mapped_column(default=0)
    disrupted_by_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    built_epoch: Mapped[int] = mapped_column(default=0)
    horizon: Mapped[int] = mapped_column(default=5)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class GodFeedingRow(Base):
    __tablename__ = "god_feedings"
    __table_args__ = (between("weight", PERCENT_MIN, PERCENT_MAX), at_least("harvested", 0))

    god_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    emotion: Mapped[Emotion] = mapped_column(enum_type(Emotion, "emotion"), primary_key=True)
    weight: Mapped[int] = mapped_column(default=50)
    harvested: Mapped[int] = mapped_column(default=0)
    epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class EmotionHarvestRow(Base):
    __tablename__ = "emotion_harvests"
    __table_args__ = (at_least("count", 0), at_least("essence", 0), Index("ix_emotion_harvests_god_epoch", "god_node_id", "epoch"))

    id: Mapped[int] = mapped_column(primary_key=True)
    god_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    epoch: Mapped[int]
    emotion: Mapped[Emotion] = mapped_column(enum_type(Emotion, "emotion"))
    count: Mapped[int] = mapped_column(default=0)
    essence: Mapped[int] = mapped_column(default=0)
