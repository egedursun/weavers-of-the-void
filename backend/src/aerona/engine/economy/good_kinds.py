from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.commodities import COMMODITIES
from aerona.catalog.good_builtins import BUILT_IN_GOODS
from aerona.catalog.urban import cargo_class
from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.read_memo import memoized
from aerona.db.tables.kinds import GoodKindRow
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.kinds import GoodLegality, GoodTaxClass
from aerona.domain.enums.urban import CargoClass
from aerona.rules.registry import Rules

LEGALITY_KEYS = total(
    GoodLegality,
    {
        GoodLegality.FREE: None,
        GoodLegality.LICENSED: "licensed_demand_pct",
        GoodLegality.RESTRICTED: "restricted_demand_pct",
        GoodLegality.FORBIDDEN: "forbidden_demand_pct",
    },
)
TARIFF_KEYS = total(
    GoodTaxClass,
    {
        GoodTaxClass.EXEMPT: "exempt_tariff_pct",
        GoodTaxClass.STAPLE: "staple_tariff_pct",
        GoodTaxClass.ORDINARY: "ordinary_tariff_pct",
        GoodTaxClass.LUXURY: "luxury_tariff_pct",
        GoodTaxClass.STRATEGIC: "strategic_tariff_pct",
    },
)


def built_in_row(kind: CommodityKind) -> GoodKindRow:
    spec, good = COMMODITIES[kind], BUILT_IN_GOODS[kind]
    return GoodKindRow(
        name=spec.label,
        category=good.category,
        built_in=True,
        created_epoch=0,
        retired=False,
        locked=[],
        stocked_as=kind,
        source=good.source,
        cargo_class=cargo_class(kind),
        tax_class=good.tax_class,
        legality=GoodLegality.FREE,
        perishability=good.perishability,
        bulk=good.bulk,
        base_value=spec.base_price,
        nourishment=min(PERCENT, spec.nourishment * 5),
        prestige=good.prestige,
        sacred=good.sacred,
        taboo=0,
    )


async def ensure_built_in_goods(session: AsyncSession) -> int:
    present = set(await session.scalars(select(GoodKindRow.stocked_as).where(GoodKindRow.built_in.is_(True), GoodKindRow.stocked_as.is_not(None))))
    added = [built_in_row(kind) for kind in CommodityKind if kind not in present]
    session.add_all(added)
    await session.flush()
    return len(added)


@dataclass
class GoodBook:
    rows: dict[CommodityKind, GoodKindRow] = field(default_factory=dict)

    @classmethod
    async def load(cls, session: AsyncSession) -> "GoodBook":
        found = await session.scalars(
            select(GoodKindRow)
            .where(GoodKindRow.built_in.is_(True), GoodKindRow.retired.is_(False), GoodKindRow.stocked_as.is_not(None))
            .order_by(GoodKindRow.id)
        )
        rows: dict[CommodityKind, GoodKindRow] = {}
        for row in found:
            if row.stocked_as is not None:
                rows.setdefault(row.stocked_as, row)
        return cls(rows)

    def base_price(self, kind: CommodityKind) -> int:
        row = self.rows.get(kind)
        return row.base_value if row is not None else COMMODITIES[kind].base_price

    def nourishment(self, kind: CommodityKind) -> int:
        row = self.rows.get(kind)
        return row.nourishment if row is not None else min(PERCENT, COMMODITIES[kind].nourishment * 5)

    def cargo(self, kind: CommodityKind) -> CargoClass:
        row = self.rows.get(kind)
        return row.cargo_class if row is not None else cargo_class(kind)

    def spoil_scale(self, kind: CommodityKind) -> float:
        row = self.rows.get(kind)
        usual = BUILT_IN_GOODS[kind].perishability
        if row is None or usual == 0:
            return 1.0
        return usual / row.perishability if row.perishability > 0 else 0.0

    def bulk_scale(self, kind: CommodityKind) -> float:
        row = self.rows.get(kind)
        usual = BUILT_IN_GOODS[kind].bulk
        return row.bulk / usual if row is not None and usual > 0 else 1.0

    def tariff_scale(self, rules: Rules, kind: CommodityKind) -> float:
        row = self.rows.get(kind)
        tax = row.tax_class if row is not None else BUILT_IN_GOODS[kind].tax_class
        return int(getattr(rules.goods, TARIFF_KEYS[tax])) / PERCENT

    def demand_scale(self, rules: Rules, kind: CommodityKind, *, prosperity: int | None, piety: int | None) -> float:
        row = self.rows.get(kind)
        if row is None:
            return 1.0
        table = rules.goods
        key = LEGALITY_KEYS[row.legality]
        scale = int(getattr(table, key)) / PERCENT if key is not None else 1.0
        scale *= max(0.0, 1 - row.taboo * table.taboo_pct / PERCENT / PERCENT)
        wealth = ((prosperity if prosperity is not None else PERCENT // 2) - PERCENT // 2) / PERCENT
        scale *= max(0.0, 1 + wealth * row.prestige * table.prestige_demand_pct / PERCENT / PERCENT)
        faith = (piety if piety is not None else 0) / PERCENT
        scale *= 1 + faith * row.sacred * table.sacred_demand_pct / PERCENT / PERCENT
        return scale


@memoized(GoodKindRow)
async def good_book(session: AsyncSession) -> GoodBook:
    return await GoodBook.load(session)
