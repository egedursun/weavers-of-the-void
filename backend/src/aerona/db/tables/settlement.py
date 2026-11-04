from sqlalchemy import JSON, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import KEY_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.settlement import BuildMaterial, DistrictKind, SizeTier, TreasuryEntry, WaterSupply


class SettlementProfileRow(Base):
    __tablename__ = "settlement_profiles"
    __table_args__ = (
        between("public_order", PERCENT_MIN, PERCENT_MAX),
        between("crime", PERCENT_MIN, PERCENT_MAX),
        between("unrest", PERCENT_MIN, PERCENT_MAX),
        between("sanitation", PERCENT_MIN, PERCENT_MAX),
        between("fire_risk", PERCENT_MIN, PERCENT_MAX),
        between("prestige", PERCENT_MIN, PERCENT_MAX),
        between("tax_rate", PERCENT_MIN, PERCENT_MAX),
        at_least("militia", 0),
        at_least("siege_supplies", 0),
        at_least("siege_water", 0),
        at_least("investment_pool", 0),
        at_least("construction_capacity", 0),
        at_least("hauling_capacity", 0),
    )

    settlement_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    size_tier: Mapped[SizeTier] = mapped_column(enum_type(SizeTier, "size_tier"))
    treasury: Mapped[int] = mapped_column(default=0)
    tax_rate: Mapped[int] = mapped_column(default=10)
    public_order: Mapped[int] = mapped_column(default=50)
    crime: Mapped[int] = mapped_column(default=10)
    unrest: Mapped[int] = mapped_column(default=10)
    sanitation: Mapped[int] = mapped_column(default=20)
    fire_risk: Mapped[int] = mapped_column(default=20)
    prestige: Mapped[int] = mapped_column(default=10)
    militia: Mapped[int] = mapped_column(default=0)
    garrison_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    free_city: Mapped[bool] = mapped_column(default=False)
    charter_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    foreigners: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    siege_supplies: Mapped[int] = mapped_column(default=0)
    siege_water: Mapped[int] = mapped_column(default=0)
    siege_disease: Mapped[int] = mapped_column(default=0)
    investment_pool: Mapped[int] = mapped_column(default=0)
    construction_capacity: Mapped[int] = mapped_column(default=0)
    hauling_capacity: Mapped[int] = mapped_column(default=0)
    rationing: Mapped[bool] = mapped_column(default=False)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class DistrictRow(Base):
    __tablename__ = "districts"
    __table_args__ = (between("level", 1, 5), between("condition", PERCENT_MIN, PERCENT_MAX), Index("ix_districts_settlement", "settlement_entity_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    settlement_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    kind: Mapped[DistrictKind] = mapped_column(enum_type(DistrictKind, "kind"))
    level: Mapped[int] = mapped_column(default=1)
    condition: Mapped[int] = mapped_column(default=100)
    material: Mapped[BuildMaterial] = mapped_column(enum_type(BuildMaterial, "material"), default=BuildMaterial.TIMBER)
    built_epoch: Mapped[int]
    built_by_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    built_by_son_id: Mapped[int | None] = mapped_column(ForeignKey("sons.id", ondelete="SET NULL"))


class SettlementInfrastructureRow(Base):
    __tablename__ = "settlement_infrastructure"
    __table_args__ = (
        between("walls_level", 0, 5),
        between("walls_condition", PERCENT_MIN, PERCENT_MAX),
        between("roads", 0, 5),
        between("towers", 0, 20),
        between("gates", 0, 20),
        between("bridges", 0, 5),
        between("irrigation", 0, 5),
        at_least("granary_capacity", 0),
        at_least("warehouse_capacity", 0),
        at_least("harbour_capacity", 0),
    )

    settlement_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    walls_level: Mapped[int] = mapped_column(default=0)
    walls_material: Mapped[BuildMaterial] = mapped_column(enum_type(BuildMaterial, "walls_material"), default=BuildMaterial.TIMBER)
    walls_condition: Mapped[int] = mapped_column(default=100)
    gates: Mapped[int] = mapped_column(default=0)
    roads: Mapped[int] = mapped_column(default=0)
    water: Mapped[WaterSupply] = mapped_column(enum_type(WaterSupply, "water"), default=WaterSupply.WELL)
    sewers: Mapped[bool] = mapped_column(default=False)
    granary_capacity: Mapped[int] = mapped_column(default=0)
    warehouse_capacity: Mapped[int] = mapped_column(default=0)
    harbour_capacity: Mapped[int] = mapped_column(default=0)
    towers: Mapped[int] = mapped_column(default=0)
    bridges: Mapped[int] = mapped_column(default=0)
    irrigation: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class SettlementTreasuryRow(Base):
    __tablename__ = "settlement_treasury"
    __table_args__ = (Index("ix_settlement_treasury_settlement", "settlement_entity_id", "epoch"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    settlement_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    epoch: Mapped[int]
    entry: Mapped[TreasuryEntry] = mapped_column(enum_type(TreasuryEntry, "entry"))
    amount: Mapped[int]
    balance: Mapped[int]
    note: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))


class SettlementHistoryRow(Base):
    __tablename__ = "settlement_history"

    settlement_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    epoch: Mapped[int] = mapped_column(primary_key=True)
    size_tier: Mapped[SizeTier] = mapped_column(enum_type(SizeTier, "size_tier"))
    public_order: Mapped[int]
    crime: Mapped[int]
    unrest: Mapped[int]
    sanitation: Mapped[int]
    wealth: Mapped[int]
    treasury: Mapped[int]
    population: Mapped[int]
