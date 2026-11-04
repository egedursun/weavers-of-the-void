from sqlalchemy import JSON, CheckConstraint, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import NAME_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.economy import (
    CommodityKind,
    GoodsFlow,
    LoanStatus,
    MaterialFamily,
    MaterialOrigin,
    MaterialSlot,
    TradeLoss,
    TradeMode,
    TradeRouteStatus,
    WorkshopKind,
)
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.society import KnowledgeBranch

ROUTE_DANGER_COLUMNS = ("danger_bandits", "danger_beasts", "danger_weather", "danger_sea")
PROPERTY_COLUMNS = ("hardness", "toughness", "weight", "edge", "conductivity", "sanctity", "corruption", "rarity", "base_value", "decay")


class WorldMaterialRow(Base):
    __tablename__ = "world_materials"
    __table_args__ = (
        *(between(column, PERCENT_MIN, PERCENT_MAX) for column in PROPERTY_COLUMNS),
        at_least("level", 0),
        Index("ix_world_materials_world", "world_id"),
        Index("ux_world_materials_override", "world_id", "base_kind", unique=True, sqlite_where=text("origin = 'catalog'")),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"))
    origin: Mapped[MaterialOrigin] = mapped_column(enum_type(MaterialOrigin, "origin"))
    base_kind: Mapped[MaterialKind | None] = mapped_column(enum_type(MaterialKind, "base_kind"))
    name: Mapped[str | None] = mapped_column(String(NAME_MAX_LENGTH))
    description: Mapped[str | None] = mapped_column(Text)
    family: Mapped[MaterialFamily] = mapped_column(enum_type(MaterialFamily, "family"))
    hardness: Mapped[int]
    toughness: Mapped[int]
    weight: Mapped[int]
    edge: Mapped[int]
    conductivity: Mapped[int]
    sanctity: Mapped[int]
    corruption: Mapped[int]
    rarity: Mapped[int]
    base_value: Mapped[int]
    decay: Mapped[int]
    branch: Mapped[KnowledgeBranch | None] = mapped_column(enum_type(KnowledgeBranch, "branch"))
    level: Mapped[int] = mapped_column(default=0)
    source_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    deposit_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    created_epoch: Mapped[int]
    held: Mapped[bool] = mapped_column(default=False)


class NodeMaterialRow(Base):
    __tablename__ = "node_materials"
    __table_args__ = (CheckConstraint("(material IS NULL) <> (world_material_id IS NULL)", name="one_material"),)

    node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    slot: Mapped[MaterialSlot] = mapped_column(enum_type(MaterialSlot, "slot"), primary_key=True)
    material: Mapped[MaterialKind | None] = mapped_column(enum_type(MaterialKind, "material"))
    world_material_id: Mapped[int | None] = mapped_column(ForeignKey("world_materials.id", ondelete="CASCADE"))
    held: Mapped[bool] = mapped_column(default=False)


class CommunityStockRow(Base):
    __tablename__ = "community_stocks"
    __table_args__ = (
        at_least("quantity", 0),
        between("quality", PERCENT_MIN, PERCENT_MAX),
        Index(
            "ux_community_stocks_key",
            "community_entity_id",
            "commodity",
            text("coalesce(material, '')"),
            text("coalesce(world_material_id, 0)"),
            unique=True,
        ),
        Index("ix_community_stocks_commodity", "commodity"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    community_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    commodity: Mapped[CommodityKind] = mapped_column(enum_type(CommodityKind, "commodity"))
    material: Mapped[MaterialKind | None] = mapped_column(enum_type(MaterialKind, "material"))
    world_material_id: Mapped[int | None] = mapped_column(ForeignKey("world_materials.id", ondelete="CASCADE"))
    quantity: Mapped[int] = mapped_column(default=0)
    quality: Mapped[int] = mapped_column(default=50)
    held: Mapped[bool] = mapped_column(default=False)


class WorkshopDesignRow(Base):
    __tablename__ = "workshop_designs"
    __table_args__ = (
        between("output_pct", 0, 500),
        between("capacity_pct", 0, 500),
        between("store_pct", 0, 500),
        between("quality_bonus", PERCENT_MIN, PERCENT_MAX),
        Index("ix_workshop_designs_world", "world_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"))
    base_kind: Mapped[WorkshopKind] = mapped_column(enum_type(WorkshopKind, "base_kind"))
    name: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH))
    description: Mapped[str | None] = mapped_column(Text)
    output_pct: Mapped[int] = mapped_column(default=100)
    capacity_pct: Mapped[int] = mapped_column(default=100)
    store_pct: Mapped[int] = mapped_column(default=100)
    quality_bonus: Mapped[int] = mapped_column(default=0)
    held: Mapped[bool] = mapped_column(default=False)
    created_epoch: Mapped[int]


class WorkshopRow(Base):
    __tablename__ = "workshops"
    __table_args__ = (
        at_least("level", 1),
        at_least("fleet", 0),
        at_least("idle_epochs", 0),
        Index("ux_workshops_kind", "community_entity_id", "kind", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    community_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    kind: Mapped[WorkshopKind] = mapped_column(enum_type(WorkshopKind, "kind"))
    level: Mapped[int] = mapped_column(default=1)
    structure_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    built_epoch: Mapped[int]
    fleet: Mapped[int] = mapped_column(default=0)
    idle_epochs: Mapped[int] = mapped_column(default=0)
    held: Mapped[bool] = mapped_column(default=False)
    design_id: Mapped[int | None] = mapped_column(ForeignKey("workshop_designs.id", ondelete="SET NULL"))


class ResourceProfileRow(Base):
    __tablename__ = "resource_profiles"
    __table_args__ = (
        at_least("reserve", 0),
        at_least("initial_reserve", 1),
        at_least("regeneration", 0),
        at_least("required_level", 0),
        at_least("last_output", 0),
        between("richness", PERCENT_MIN, PERCENT_MAX),
        between("extraction_difficulty", PERCENT_MIN, PERCENT_MAX),
        between("quality", PERCENT_MIN, PERCENT_MAX),
        between("byproduct_pct", PERCENT_MIN, PERCENT_MAX),
        CheckConstraint("reserve <= initial_reserve * 4", name="reserve_bounded"),
    )

    resource_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    commodity: Mapped[CommodityKind] = mapped_column(enum_type(CommodityKind, "commodity"))
    material: Mapped[MaterialKind | None] = mapped_column(enum_type(MaterialKind, "material"))
    world_material_id: Mapped[int | None] = mapped_column(ForeignKey("world_materials.id", ondelete="SET NULL"))
    reserve: Mapped[int]
    initial_reserve: Mapped[int]
    richness: Mapped[int]
    regeneration: Mapped[int] = mapped_column(default=0)
    extraction_difficulty: Mapped[int]
    required_branch: Mapped[KnowledgeBranch | None] = mapped_column(enum_type(KnowledgeBranch, "required_branch"))
    required_level: Mapped[int] = mapped_column(default=0)
    quality: Mapped[int]
    byproduct_material: Mapped[MaterialKind | None] = mapped_column(enum_type(MaterialKind, "byproduct_material"))
    byproduct_pct: Mapped[int] = mapped_column(default=0)
    revealed: Mapped[bool] = mapped_column(default=True)
    sealed_until_epoch: Mapped[int | None]
    last_output: Mapped[int] = mapped_column(default=0)
    held: Mapped[bool] = mapped_column(default=False)


class ResourceWorkerRow(Base):
    __tablename__ = "resource_workers"
    __table_args__ = (at_least("workers", 0),)

    resource_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    community_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True, index=True)
    workers: Mapped[int] = mapped_column(default=0)
    held: Mapped[bool] = mapped_column(default=False)


class ProductionRunRow(Base):
    __tablename__ = "production_runs"
    __table_args__ = (
        at_least("quantity", 0),
        at_least("workers", 0),
        between("quality", PERCENT_MIN, PERCENT_MAX),
        Index("ix_production_runs_epoch", "epoch", "community_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    epoch: Mapped[int]
    community_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    step: Mapped[str] = mapped_column(String(64))
    workshop: Mapped[WorkshopKind | None] = mapped_column(enum_type(WorkshopKind, "workshop"))
    resource_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    output: Mapped[CommodityKind] = mapped_column(enum_type(CommodityKind, "output"))
    material: Mapped[MaterialKind | None] = mapped_column(enum_type(MaterialKind, "material"))
    quantity: Mapped[int]
    quality: Mapped[int]
    inputs: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    workers: Mapped[int] = mapped_column(default=0)
    bottleneck: Mapped[CommodityKind | None] = mapped_column(enum_type(CommodityKind, "bottleneck"))


class MarketPriceRow(Base):
    __tablename__ = "market_prices"
    __table_args__ = (at_least("price", 0), at_least("supply", 0), at_least("demand", 0), Index("ix_market_prices_epoch", "epoch"))

    market_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    commodity: Mapped[CommodityKind] = mapped_column(enum_type(CommodityKind, "commodity"), primary_key=True)
    epoch: Mapped[int] = mapped_column(primary_key=True)
    price: Mapped[int]
    supply: Mapped[int]
    demand: Mapped[int]
    imported: Mapped[int] = mapped_column(default=0)
    exported: Mapped[int] = mapped_column(default=0)
    swing: Mapped[int] = mapped_column(default=0)


class MarketPriceHoldRow(Base):
    __tablename__ = "market_price_holds"
    __table_args__ = (at_least("price", 0), at_least("supply", 0))

    market_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    commodity: Mapped[CommodityKind] = mapped_column(enum_type(CommodityKind, "commodity"), primary_key=True)
    price: Mapped[int | None]
    supply: Mapped[int | None]
    set_epoch: Mapped[int]


class TradeRouteProfileRow(Base):
    __tablename__ = "trade_route_profiles"
    __table_args__ = (
        CheckConstraint("first_market_id <> second_market_id", name="distinct_markets"),
        at_least("length", 1),
        at_least("traffic_epochs", 0),
        Index("ix_trade_route_markets", "first_market_id", "second_market_id"),
        *(between(column, PERCENT_MIN, PERCENT_MAX) for column in ROUTE_DANGER_COLUMNS),
        between("season_pct", PERCENT_MIN, PERCENT_MAX),
    )

    route_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    first_market_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    second_market_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    mode: Mapped[TradeMode] = mapped_column(enum_type(TradeMode, "mode"))
    status: Mapped[TradeRouteStatus] = mapped_column(enum_type(TradeRouteStatus, "status"))
    length: Mapped[int]
    controller_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    blockaded_by_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    founded_epoch: Mapped[int]
    last_traffic_epoch: Mapped[int | None]
    traffic_epochs: Mapped[int] = mapped_column(default=0)
    closed_by_player: Mapped[bool] = mapped_column(default=False)
    danger_bandits: Mapped[int] = mapped_column(default=0)
    danger_beasts: Mapped[int] = mapped_column(default=0)
    danger_weather: Mapped[int] = mapped_column(default=0)
    danger_sea: Mapped[int] = mapped_column(default=0)
    season_pct: Mapped[int] = mapped_column(default=100)
    chokepoint: Mapped[bool] = mapped_column(default=False)
    closed_by_son_id: Mapped[int | None] = mapped_column(ForeignKey("sons.id", ondelete="SET NULL"))
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class TradeRouteRegionRow(Base):
    __tablename__ = "trade_route_regions"

    route_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    position: Mapped[int] = mapped_column(primary_key=True)
    region_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), index=True)


class TradeRouteTollRow(Base):
    __tablename__ = "trade_route_tolls"
    __table_args__ = (between("rate_pct", PERCENT_MIN, PERCENT_MAX),)

    route_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    region_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    controller_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    rate_pct: Mapped[int]
    set_by_player: Mapped[bool] = mapped_column(default=False)
    controller_held: Mapped[bool] = mapped_column(default=False)
    polity_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))


class TradeFlowRow(Base):
    __tablename__ = "trade_flows"
    __table_args__ = (
        at_least("volume", 0),
        at_least("lost", 0),
        at_least("value", 0),
        at_least("toll_paid", 0),
        Index("ix_trade_flows_route", "route_entity_id", "epoch"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    route_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    epoch: Mapped[int]
    commodity: Mapped[CommodityKind] = mapped_column(enum_type(CommodityKind, "commodity"))
    material: Mapped[MaterialKind | None] = mapped_column(enum_type(MaterialKind, "material"))
    from_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    to_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    volume: Mapped[int]
    lost: Mapped[int] = mapped_column(default=0)
    loss: Mapped[TradeLoss | None] = mapped_column(enum_type(TradeLoss, "loss"))
    value: Mapped[int] = mapped_column(default=0)
    toll_paid: Mapped[int] = mapped_column(default=0)


class TradeRouteLossRow(Base):
    __tablename__ = "trade_route_losses"
    __table_args__ = (at_least("units", 0), Index("ix_trade_route_losses_route", "route_entity_id", "epoch"))

    id: Mapped[int] = mapped_column(primary_key=True)
    route_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    epoch: Mapped[int]
    commodity: Mapped[CommodityKind] = mapped_column(enum_type(CommodityKind, "commodity"))
    cause: Mapped[TradeLoss] = mapped_column(enum_type(TradeLoss, "cause"))
    units: Mapped[int]
    culprit_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))


class CurrencyRow(Base):
    __tablename__ = "currencies"
    __table_args__ = (between("purity", PERCENT_MIN, PERCENT_MAX), between("trust", PERCENT_MIN, PERCENT_MAX), at_least("supply", 0))

    id: Mapped[int] = mapped_column(primary_key=True)
    issuer_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    item_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH))
    metal: Mapped[MaterialKind] = mapped_column(enum_type(MaterialKind, "metal"))
    purity: Mapped[int]
    supply: Mapped[int]
    trust: Mapped[int]
    minted_epoch: Mapped[int]
    debased_epoch: Mapped[int | None]
    held: Mapped[bool] = mapped_column(default=False)


class LoanRow(Base):
    __tablename__ = "loans"
    __table_args__ = (
        CheckConstraint("lender_entity_id <> borrower_entity_id", name="distinct_parties"),
        at_least("principal", 1),
        at_least("repaid", 0),
        between("interest_pct", PERCENT_MIN, PERCENT_MAX),
        Index("ix_loans_status", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    lender_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    borrower_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    currency_id: Mapped[int | None] = mapped_column(ForeignKey("currencies.id", ondelete="SET NULL"))
    principal: Mapped[int]
    interest_pct: Mapped[int]
    repaid: Mapped[int] = mapped_column(default=0)
    issued_epoch: Mapped[int]
    due_epoch: Mapped[int]
    status: Mapped[LoanStatus] = mapped_column(enum_type(LoanStatus, "status"))
    purpose: Mapped[str] = mapped_column(String(64))
    war_id: Mapped[int | None] = mapped_column(ForeignKey("wars.id", ondelete="SET NULL"))
    held: Mapped[bool] = mapped_column(default=False)


class GoodsFlowRow(Base):
    __tablename__ = "goods_flows"

    epoch: Mapped[int] = mapped_column(primary_key=True)
    community_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    commodity: Mapped[CommodityKind] = mapped_column(enum_type(CommodityKind, "commodity"), primary_key=True)
    flow: Mapped[GoodsFlow] = mapped_column(enum_type(GoodsFlow, "flow"), primary_key=True)
    quantity: Mapped[int] = mapped_column(default=0)
