from sqlalchemy import JSON, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import NAME_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.folkways import (
    AccusationOutcome,
    BiasedDecision,
    CharmPower,
    DecisionBias,
    ImpuritySource,
    LuckReach,
    LuckSign,
    MishapAttribution,
    MishapKind,
    MishapResponse,
    Nutrient,
    Purification,
    PurityState,
)
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN

DIET_FIELDS = ("staple", "protein", "fat", "fresh", "mineral", "preserved", "special", "energy")
NEED_FIELDS = ("weight",)
SCORE_FIELDS = ("energy", "balance", "score", "deficiency", "childhood")
BIAS_FIELDS = ("weight",)
PURITY_FIELDS = ("state", "source", "until_epoch", "rank_id")
IMPURITY_FIELDS = ("weight", "lasts")
PURIFICATION_FIELDS = ("epochs", "cost", "success")
RANK_FIELDS = ("name", "standing", "endogamous", "commensal")
MISHAP_FIELDS = ("kind", "true_cause", "explained", "attribution", "response", "victim_node_id", "cause_node_id")
LUCK_FIELDS = ("sign", "reach", "lucky", "name")
CHARM_FIELDS = ("power", "real", "strength")
ACCUSATION_FIELDS = ("settlement_entity_id", "accuser_node_id", "accused_node_id", "outcome", "guilty_in_truth")
HUNT_FIELDS = ("fervour", "accused", "killed", "ended_epoch")


class DietRow(Base):
    __tablename__ = "diets"
    __table_args__ = tuple(between(name, PERCENT_MIN, PERCENT_MAX) for name in DIET_FIELDS)

    holder_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    staple: Mapped[int] = mapped_column(default=60)
    protein: Mapped[int] = mapped_column(default=15)
    fat: Mapped[int] = mapped_column(default=10)
    fresh: Mapped[int] = mapped_column(default=10)
    mineral: Mapped[int] = mapped_column(default=5)
    preserved: Mapped[int] = mapped_column(default=0)
    special: Mapped[int] = mapped_column(default=0)
    energy: Mapped[int] = mapped_column(default=100)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class NutrientNeedRow(Base):
    __tablename__ = "nutrient_needs"
    __table_args__ = (between("weight", PERCENT_MIN, PERCENT_MAX),)

    people_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    nutrient: Mapped[Nutrient] = mapped_column(enum_type(Nutrient, "nutrient"), primary_key=True)
    weight: Mapped[int] = mapped_column(default=50)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class NutritionScoreRow(Base):
    __tablename__ = "nutrition_scores"
    __table_args__ = (
        between("energy", PERCENT_MIN, PERCENT_MAX),
        between("balance", PERCENT_MIN, PERCENT_MAX),
        between("score", PERCENT_MIN, PERCENT_MAX),
        between("childhood", PERCENT_MIN, PERCENT_MAX),
    )

    holder_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    energy: Mapped[int] = mapped_column(default=100)
    balance: Mapped[int] = mapped_column(default=100)
    score: Mapped[int] = mapped_column(default=100)
    deficiency: Mapped[Nutrient | None] = mapped_column(enum_type(Nutrient, "deficiency"))
    childhood: Mapped[int | None]
    grown: Mapped[bool] = mapped_column(default=False)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class BiasWeightRow(Base):
    __tablename__ = "bias_weights"
    __table_args__ = (between("weight", PERCENT_MIN, PERCENT_MAX),)

    holder_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    bias: Mapped[DecisionBias] = mapped_column(enum_type(DecisionBias, "bias"), primary_key=True)
    weight: Mapped[int] = mapped_column(default=50)
    last_decision: Mapped[BiasedDecision | None] = mapped_column(enum_type(BiasedDecision, "last_decision"))
    last_shift: Mapped[int] = mapped_column(default=0)
    last_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class PurityRankRow(Base):
    __tablename__ = "purity_ranks"
    __table_args__ = (between("standing", PERCENT_MIN, PERCENT_MAX), UniqueConstraint("people_entity_id", "name", name="uq_purity_ranks_people_name"))

    id: Mapped[int] = mapped_column(primary_key=True)
    people_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH))
    standing: Mapped[int] = mapped_column(default=50)
    professions: Mapped[list[str]] = mapped_column(JSON, default=list)
    endogamous: Mapped[bool] = mapped_column(default=True)
    commensal: Mapped[bool] = mapped_column(default=True)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class PurityRow(Base):
    __tablename__ = "purity"
    __table_args__ = (at_least("since_epoch", 0),)

    holder_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    state: Mapped[PurityState] = mapped_column(enum_type(PurityState, "state"), default=PurityState.PURE)
    source: Mapped[ImpuritySource | None] = mapped_column(enum_type(ImpuritySource, "source"))
    since_epoch: Mapped[int] = mapped_column(default=0)
    until_epoch: Mapped[int | None]
    rank_id: Mapped[int | None] = mapped_column(ForeignKey("purity_ranks.id", ondelete="SET NULL"), index=True)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ImpuritySourceRow(Base):
    __tablename__ = "impurity_sources"
    __table_args__ = (between("weight", PERCENT_MIN, PERCENT_MAX), at_least("lasts", 1))

    people_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    source: Mapped[ImpuritySource] = mapped_column(enum_type(ImpuritySource, "source"), primary_key=True)
    weight: Mapped[int] = mapped_column(default=50)
    lasts: Mapped[int] = mapped_column(default=1)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class PurificationRow(Base):
    __tablename__ = "purifications"
    __table_args__ = (at_least("epochs", 0), at_least("cost", 0), between("success", PERCENT_MIN, PERCENT_MAX))

    people_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    method: Mapped[Purification] = mapped_column(enum_type(Purification, "method"), primary_key=True)
    epochs: Mapped[int] = mapped_column(default=1)
    cost: Mapped[int] = mapped_column(default=0)
    success: Mapped[int] = mapped_column(default=80)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class MishapRow(Base):
    __tablename__ = "mishaps"
    __table_args__ = (at_least("epoch", 0), Index("ix_mishaps_settlement", "settlement_entity_id", "epoch"))

    id: Mapped[int] = mapped_column(primary_key=True)
    settlement_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    victim_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    cause_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    kind: Mapped[MishapKind] = mapped_column(enum_type(MishapKind, "kind"))
    true_cause: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH))
    explained: Mapped[bool] = mapped_column(default=False)
    attribution: Mapped[MishapAttribution | None] = mapped_column(enum_type(MishapAttribution, "attribution"))
    response: Mapped[MishapResponse | None] = mapped_column(enum_type(MishapResponse, "response"))
    epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class LuckBeliefRow(Base):
    __tablename__ = "luck_beliefs"

    id: Mapped[int] = mapped_column(primary_key=True)
    people_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    sign: Mapped[LuckSign] = mapped_column(enum_type(LuckSign, "sign"))
    reach: Mapped[LuckReach] = mapped_column(enum_type(LuckReach, "reach"))
    lucky: Mapped[bool] = mapped_column(default=True)
    name: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH))
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class CharmRow(Base):
    __tablename__ = "charms"
    __table_args__ = (between("strength", PERCENT_MIN, PERCENT_MAX),)

    item_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    power: Mapped[CharmPower] = mapped_column(enum_type(CharmPower, "power"))
    real: Mapped[bool] = mapped_column(default=False)
    strength: Mapped[int] = mapped_column(default=30)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class AccusationRow(Base):
    __tablename__ = "accusations"
    __table_args__ = (at_least("opened_epoch", 0), Index("ix_accusations_accused", "accused_node_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    settlement_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"), index=True)
    mishap_id: Mapped[int | None] = mapped_column(ForeignKey("mishaps.id", ondelete="SET NULL"))
    hunt_id: Mapped[int | None] = mapped_column(ForeignKey("witch_hunts.id", ondelete="SET NULL"), index=True)
    accuser_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    accused_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    case_id: Mapped[int | None] = mapped_column(ForeignKey("crime_cases.id", ondelete="SET NULL"))
    outcome: Mapped[AccusationOutcome] = mapped_column(enum_type(AccusationOutcome, "outcome"), default=AccusationOutcome.PENDING)
    guilty_in_truth: Mapped[bool] = mapped_column(default=False)
    opened_epoch: Mapped[int] = mapped_column(default=0)
    closed_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class WitchHuntRow(Base):
    __tablename__ = "witch_hunts"
    __table_args__ = (between("fervour", PERCENT_MIN, PERCENT_MAX), at_least("accused", 0), at_least("killed", 0), at_least("started_epoch", 0))

    id: Mapped[int] = mapped_column(primary_key=True)
    settlement_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    fervour: Mapped[int] = mapped_column(default=50)
    accused: Mapped[int] = mapped_column(default=0)
    killed: Mapped[int] = mapped_column(default=0)
    started_epoch: Mapped[int] = mapped_column(default=0)
    ended_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
