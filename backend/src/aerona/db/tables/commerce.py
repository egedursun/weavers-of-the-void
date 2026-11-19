from sqlalchemy import JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.commerce import LeaseDefault, LeaseThing, LeaseUpkeep, PromotionMedium, ShopForm, SupplyTier
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN

MARGIN_MAX = 200


class ShopRow(Base):
    __tablename__ = "shops"
    __table_args__ = (
        between("margin", 0, MARGIN_MAX),
        at_least("stock", 0),
        at_least("credit", 0),
        at_least("opened_epoch", 0),
        Index("ix_shops_settlement", "settlement_entity_id"),
        Index("ix_shops_keeper", "keeper_node_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    settlement_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    structure_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    keeper_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    form: Mapped[ShopForm] = mapped_column(enum_type(ShopForm, "form"), default=ShopForm.SHOP)
    margin: Mapped[int] = mapped_column(default=20)
    stock: Mapped[int] = mapped_column(default=10)
    credit: Mapped[int] = mapped_column(default=0)
    opened_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ShopGoodRow(Base):
    __tablename__ = "shop_goods"
    __table_args__ = (Index("ix_shop_goods_keeper", "keeper_node_id"),)

    shop_id: Mapped[int] = mapped_column(ForeignKey("shops.id", ondelete="CASCADE"), primary_key=True)
    commodity: Mapped[CommodityKind] = mapped_column(enum_type(CommodityKind, "commodity"), primary_key=True)
    keeper_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class SupplyTierRow(Base):
    __tablename__ = "supply_tiers"
    __table_args__ = (
        between("margin", 0, MARGIN_MAX),
        between("share", PERCENT_MIN, PERCENT_MAX),
        Index("ix_supply_tiers_market", "market_entity_id"),
        Index("ix_supply_tiers_holder", "holder_node_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    market_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    commodity: Mapped[CommodityKind | None] = mapped_column(enum_type(CommodityKind, "commodity"))
    tier: Mapped[SupplyTier] = mapped_column(enum_type(SupplyTier, "tier"), default=SupplyTier.RETAIL)
    holder_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    share: Mapped[int] = mapped_column(default=100)
    margin: Mapped[int] = mapped_column(default=20)
    cornered: Mapped[bool] = mapped_column(default=False)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class PromotionRow(Base):
    __tablename__ = "promotions"
    __table_args__ = (
        between("reach", PERCENT_MIN, PERCENT_MAX),
        between("accuracy", PERCENT_MIN, PERCENT_MAX),
        at_least("cost", 0),
        at_least("started_epoch", 0),
        Index("ix_promotions_holder", "holder_node_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    holder_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    commodity: Mapped[CommodityKind | None] = mapped_column(enum_type(CommodityKind, "commodity"))
    brand_id: Mapped[int | None] = mapped_column(ForeignKey("brands.id", ondelete="SET NULL"))
    medium: Mapped[PromotionMedium] = mapped_column(enum_type(PromotionMedium, "medium"), default=PromotionMedium.CRIER)
    reach: Mapped[int] = mapped_column(default=30)
    cost: Mapped[int] = mapped_column(default=5)
    accuracy: Mapped[int] = mapped_column(default=80)
    exposed: Mapped[bool] = mapped_column(default=False)
    started_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class LeaseRow(Base):
    __tablename__ = "leases"
    __table_args__ = (
        at_least("rent", 0),
        at_least("term_epochs", 1),
        at_least("signed_epoch", 0),
        Index("ix_leases_owner", "owner_node_id"),
        Index("ix_leases_lessee", "lessee_node_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    lessee_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    thing_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    thing: Mapped[LeaseThing] = mapped_column(enum_type(LeaseThing, "thing"), default=LeaseThing.STRUCTURE)
    rent: Mapped[int] = mapped_column(default=5)
    term_epochs: Mapped[int] = mapped_column(default=2)
    upkeep: Mapped[LeaseUpkeep] = mapped_column(enum_type(LeaseUpkeep, "upkeep"), default=LeaseUpkeep.OWNER)
    on_default: Mapped[LeaseDefault] = mapped_column(enum_type(LeaseDefault, "on_default"), default=LeaseDefault.EVICTION)
    signed_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
