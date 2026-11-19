from sqlalchemy import JSON, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.agrarian import (
    AidKind,
    CentralityRank,
    CommonsKind,
    CommonsRule,
    KeystoneUse,
    LandUseRing,
    NutrientKind,
    PerennialKind,
    PreparednessKind,
    RebuildCause,
    RebuildPlan,
)
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN

NAME = 200
RING_FIELDS = ("market_entity_id", "ring", "distance", "by_water", "gap")
CENTRAL_FIELDS = ("rank", "catchment", "served_by_entity_id", "centrality")
NUTRIENT_FIELDS = ("stock", "trend")
INTENSITY_FIELDS = ("pressure", "intensity", "research_boost")
PERENNIAL_FIELDS = ("kind", "species_entity_id", "line_id", "owner_node_id", "area", "maturity", "mature_epochs", "condition")
COMMONS_FIELDS = ("kind", "rule", "condition", "use", "steward_entity_id", "encloser_node_id", "dispossessed")
RESERVE_FIELDS = ("holder_node_id", "species_entity_id", "strictness", "poaching", "resentment")
FAMINE_FIELDS = ("memory", "famine_foods", "storage")
PREPAREDNESS_FIELDS = ("level", "condition", "averted")
PREPAREDNESS_LEVEL_MAX = 1000
AID_FIELDS = ("kind", "amount", "god_node_id", "refused")
REBUILD_FIELDS = ("cause", "plan", "cost", "paid", "progress", "planner_entity_id", "seized_by_node_id", "seized")
KEYSTONE_FIELDS = (
    "name",
    "producer_entity_id",
    "source_region_entity_id",
    "commodity",
    "use",
    "cult_entity_id",
    "controller_entity_id",
    "harvest",
    "supply",
    "price",
)
BRAND_FIELDS = ("name", "owner_node_id", "reputation", "quality", "renowned", "counterfeits")


class LandRingRow(Base):
    __tablename__ = "land_rings"
    __table_args__ = (at_least("distance", 0), between("gap", PERCENT_MIN, PERCENT_MAX), at_least("updated_epoch", 0))

    region_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    market_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    ring: Mapped[LandUseRing] = mapped_column(enum_type(LandUseRing, "ring"), default=LandUseRing.WILDS)
    distance: Mapped[int] = mapped_column(default=0)
    by_water: Mapped[bool] = mapped_column(default=False)
    gap: Mapped[int] = mapped_column(default=0)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class CentralPlaceRow(Base):
    __tablename__ = "central_places"
    __table_args__ = (at_least("catchment", 0), between("centrality", PERCENT_MIN, PERCENT_MAX), at_least("updated_epoch", 0))

    settlement_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    rank: Mapped[CentralityRank] = mapped_column(enum_type(CentralityRank, "rank"), default=CentralityRank.DAILY)
    catchment: Mapped[int] = mapped_column(default=0)
    served_by_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    centrality: Mapped[int] = mapped_column(default=0)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class SoilNutrientRow(Base):
    __tablename__ = "soil_nutrients"
    __table_args__ = (between("stock", PERCENT_MIN, PERCENT_MAX), between("trend", -PERCENT_MAX, PERCENT_MAX), at_least("updated_epoch", 0))

    region_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    nutrient: Mapped[NutrientKind] = mapped_column(enum_type(NutrientKind, "nutrient"), primary_key=True)
    stock: Mapped[int] = mapped_column(default=50)
    trend: Mapped[int] = mapped_column(default=0)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class IntensificationRow(Base):
    __tablename__ = "intensification"
    __table_args__ = (
        between("pressure", PERCENT_MIN, PERCENT_MAX * 3),
        between("intensity", PERCENT_MIN, PERCENT_MAX),
        between("research_boost", PERCENT_MIN, PERCENT_MAX),
        at_least("updated_epoch", 0),
    )

    region_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    pressure: Mapped[int] = mapped_column(default=0)
    intensity: Mapped[int] = mapped_column(default=0)
    research_boost: Mapped[int] = mapped_column(default=0)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class PerennialRow(Base):
    __tablename__ = "perennials"
    __table_args__ = (
        between("area", PERCENT_MIN, PERCENT_MAX),
        between("maturity", PERCENT_MIN, PERCENT_MAX),
        at_least("mature_epochs", 1),
        between("condition", PERCENT_MIN, PERCENT_MAX),
        at_least("planted_epoch", 0),
        Index("ix_perennials_region", "region_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    region_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    kind: Mapped[PerennialKind] = mapped_column(enum_type(PerennialKind, "kind"))
    species_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    line_id: Mapped[int | None] = mapped_column(ForeignKey("living_lines.id", ondelete="SET NULL"))
    owner_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"), index=True)
    area: Mapped[int] = mapped_column(default=5)
    maturity: Mapped[int] = mapped_column(default=0)
    mature_epochs: Mapped[int] = mapped_column(default=3)
    condition: Mapped[int] = mapped_column(default=100)
    planted_epoch: Mapped[int] = mapped_column(default=0)
    felled_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class CommonsRow(Base):
    __tablename__ = "commons"
    __table_args__ = (
        between("condition", PERCENT_MIN, PERCENT_MAX),
        between("use", PERCENT_MIN, PERCENT_MAX * 2),
        at_least("dispossessed", 0),
        UniqueConstraint("region_entity_id", "kind", name="uq_commons_region_kind"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    region_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    kind: Mapped[CommonsKind] = mapped_column(enum_type(CommonsKind, "kind"))
    rule: Mapped[CommonsRule] = mapped_column(enum_type(CommonsRule, "rule"), default=CommonsRule.CUSTOMARY)
    condition: Mapped[int] = mapped_column(default=80)
    use: Mapped[int] = mapped_column(default=0)
    steward_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    encloser_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"), index=True)
    enclosed_epoch: Mapped[int | None]
    dispossessed: Mapped[int] = mapped_column(default=0)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class GameReserveRow(Base):
    __tablename__ = "game_reserves"
    __table_args__ = (
        between("strictness", PERCENT_MIN, PERCENT_MAX),
        between("poaching", PERCENT_MIN, PERCENT_MAX),
        between("resentment", PERCENT_MIN, PERCENT_MAX),
        at_least("since_epoch", 0),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    region_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    holder_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"), index=True)
    species_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    strictness: Mapped[int] = mapped_column(default=60)
    poaching: Mapped[int] = mapped_column(default=0)
    resentment: Mapped[int] = mapped_column(default=0)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class FamineLoreRow(Base):
    __tablename__ = "famine_lore"
    __table_args__ = (between("memory", PERCENT_MIN, PERCENT_MAX), between("storage", PERCENT_MIN, PERCENT_MAX), at_least("updated_epoch", 0))

    people_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    memory: Mapped[int] = mapped_column(default=0)
    famine_foods: Mapped[bool] = mapped_column(default=False)
    storage: Mapped[int] = mapped_column(default=0)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class PreparednessRow(Base):
    __tablename__ = "preparedness"
    __table_args__ = (
        between("level", 0, PREPAREDNESS_LEVEL_MAX),
        between("condition", PERCENT_MIN, PERCENT_MAX),
        at_least("averted", 0),
        at_least("built_epoch", 0),
    )

    settlement_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    kind: Mapped[PreparednessKind] = mapped_column(enum_type(PreparednessKind, "kind"), primary_key=True)
    level: Mapped[int] = mapped_column(default=1)
    condition: Mapped[int] = mapped_column(default=100)
    averted: Mapped[int] = mapped_column(default=0)
    built_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ReliefAidRow(Base):
    __tablename__ = "relief_aid"
    __table_args__ = (at_least("amount", 0), at_least("epoch", 0), Index("ix_relief_aid_receiver", "receiver_entity_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    event_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    giver_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), index=True)
    receiver_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    kind: Mapped[AidKind] = mapped_column(enum_type(AidKind, "kind"))
    amount: Mapped[int] = mapped_column(default=0)
    god_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    refused: Mapped[bool] = mapped_column(default=False)
    gift_id: Mapped[int | None] = mapped_column(ForeignKey("gifts.id", ondelete="SET NULL"))
    epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ReconstructionRow(Base):
    __tablename__ = "reconstructions"
    __table_args__ = (
        at_least("cost", 0),
        at_least("paid", 0),
        between("progress", PERCENT_MIN, PERCENT_MAX),
        at_least("seized", 0),
        at_least("started_epoch", 0),
        Index("ix_reconstructions_settlement", "settlement_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    settlement_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    cause: Mapped[RebuildCause] = mapped_column(enum_type(RebuildCause, "cause"))
    plan: Mapped[RebuildPlan] = mapped_column(enum_type(RebuildPlan, "plan"), default=RebuildPlan.OPPORTUNISTIC)
    cost: Mapped[int] = mapped_column(default=0)
    paid: Mapped[int] = mapped_column(default=0)
    progress: Mapped[int] = mapped_column(default=0)
    planner_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    seized_by_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    seized: Mapped[int] = mapped_column(default=0)
    started_epoch: Mapped[int] = mapped_column(default=0)
    finished_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class KeystoneResourceRow(Base):
    __tablename__ = "keystone_resources"
    __table_args__ = (
        between("harvest", PERCENT_MIN, PERCENT_MAX),
        between("supply", PERCENT_MIN, PERCENT_MAX),
        at_least("price", 0),
        at_least("designated_epoch", 0),
        UniqueConstraint("world_id", name="uq_keystone_resources_world"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(NAME))
    producer_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    source_region_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    commodity: Mapped[CommodityKind | None] = mapped_column(enum_type(CommodityKind, "commodity"))
    use: Mapped[KeystoneUse] = mapped_column(enum_type(KeystoneUse, "use"), default=KeystoneUse.RITE)
    cult_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    controller_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    harvest: Mapped[int] = mapped_column(default=20)
    supply: Mapped[int] = mapped_column(default=50)
    price: Mapped[int] = mapped_column(default=100)
    designated_epoch: Mapped[int] = mapped_column(default=0)
    designated_by_son_id: Mapped[int | None] = mapped_column(ForeignKey("sons.id", ondelete="SET NULL"))
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class BrandRow(Base):
    __tablename__ = "brands"
    __table_args__ = (
        between("reputation", PERCENT_MIN, PERCENT_MAX),
        between("quality", PERCENT_MIN, PERCENT_MAX),
        at_least("renowned", 0),
        between("counterfeits", PERCENT_MIN, PERCENT_MAX),
        at_least("since_epoch", 0),
        UniqueConstraint("workshop_id", name="uq_brands_workshop"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    workshop_id: Mapped[int] = mapped_column(ForeignKey("workshops.id", ondelete="CASCADE"))
    community_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    owner_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"), index=True)
    name: Mapped[str] = mapped_column(String(NAME))
    reputation: Mapped[int] = mapped_column(default=10)
    quality: Mapped[int] = mapped_column(default=50)
    renowned: Mapped[int] = mapped_column(default=0)
    counterfeits: Mapped[int] = mapped_column(default=0)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
