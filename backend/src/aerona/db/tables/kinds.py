from sqlalchemy import JSON, ForeignKey, Index, String, Text, UniqueConstraint, inspect
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import NAME_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.kinds import GoodCategory, GoodLegality, GoodSource, GoodTaxClass, KindConcept, KindSpread, KindStance
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.urban import CargoClass

KIND_BASE_FIELDS = ("name", "description", "world_id", "origin_node_id", "derived_from_id", "retired")
HOLDING_FIELDS = ("stance", "strength", "spread")


class KindRow(Base):
    __abstract__ = True

    id: Mapped[int] = mapped_column(primary_key=True)
    world_id: Mapped[int | None] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"), index=True)
    origin_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"), index=True)
    name: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH))
    description: Mapped[str | None] = mapped_column(Text)
    built_in: Mapped[bool] = mapped_column(default=False)
    created_epoch: Mapped[int] = mapped_column(default=0)
    retired: Mapped[bool] = mapped_column(default=False)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
    derived_from_id: Mapped[int | None]

    def category_key(self) -> str:
        return str(inspect(self).attrs["category"].value)


class KindHoldingRow(Base):
    __tablename__ = "kind_holdings"
    __table_args__ = (
        UniqueConstraint("concept", "kind_id", "holder_node_id", name="uq_kind_holdings_kind_holder"),
        between("strength", PERCENT_MIN, PERCENT_MAX),
        at_least("since_epoch", 0),
        Index("ix_kind_holdings_holder", "holder_node_id"),
        Index("ix_kind_holdings_kind", "concept", "kind_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    concept: Mapped[KindConcept] = mapped_column(enum_type(KindConcept, "concept"))
    kind_id: Mapped[int]
    holder_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    stance: Mapped[KindStance] = mapped_column(enum_type(KindStance, "stance"), default=KindStance.USES)
    strength: Mapped[int] = mapped_column(default=50)
    spread: Mapped[KindSpread] = mapped_column(enum_type(KindSpread, "spread"), default=KindSpread.INVENTED)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class GoodKindRow(KindRow):
    __tablename__ = "good_kinds"
    __table_args__ = (
        at_least("perishability", 0),
        between("bulk", PERCENT_MIN, PERCENT_MAX),
        at_least("base_value", 0),
        between("nourishment", PERCENT_MIN, PERCENT_MAX),
        between("prestige", PERCENT_MIN, PERCENT_MAX),
        between("sacred", PERCENT_MIN, PERCENT_MAX),
        between("taboo", PERCENT_MIN, PERCENT_MAX),
        at_least("created_epoch", 0),
        Index("ix_good_kinds_stocked_as", "stocked_as"),
    )

    derived_from_id: Mapped[int | None] = mapped_column(ForeignKey("good_kinds.id", ondelete="SET NULL"))
    category: Mapped[GoodCategory] = mapped_column(enum_type(GoodCategory, "category"))
    perishability: Mapped[int] = mapped_column(default=0)
    bulk: Mapped[int] = mapped_column(default=20)
    base_value: Mapped[int] = mapped_column(default=10)
    nourishment: Mapped[int] = mapped_column(default=0)
    prestige: Mapped[int] = mapped_column(default=10)
    sacred: Mapped[int] = mapped_column(default=0)
    stocked_as: Mapped[CommodityKind | None] = mapped_column(enum_type(CommodityKind, "stocked_as"))
    source: Mapped[GoodSource] = mapped_column(enum_type(GoodSource, "source"), default=GoodSource.MAKING)
    cargo_class: Mapped[CargoClass] = mapped_column(enum_type(CargoClass, "cargo_class"), default=CargoClass.BULK)
    tax_class: Mapped[GoodTaxClass] = mapped_column(enum_type(GoodTaxClass, "tax_class"), default=GoodTaxClass.ORDINARY)
    legality: Mapped[GoodLegality] = mapped_column(enum_type(GoodLegality, "legality"), default=GoodLegality.FREE)
    taboo: Mapped[int] = mapped_column(default=0)
