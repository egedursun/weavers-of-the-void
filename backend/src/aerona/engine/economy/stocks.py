from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.commodities import BACKFILL_SPLITS, COMMODITIES
from aerona.constants.units import PERCENT
from aerona.db.tables.economy import CommunityStockRow, GoodsFlowRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.society import Commodity
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import headcount
from aerona.rules.registry import Rules

DEFAULT_QUALITY = 50
THOUSAND = 1000


@dataclass(frozen=True)
class Lot:
    commodity: CommodityKind
    material: MaterialKind | None
    world_material_id: int | None
    quantity: int
    quality: int


async def lots_of(session: AsyncSession, community_id: int, commodity: CommodityKind | None = None) -> list[CommunityStockRow]:
    statement = select(CommunityStockRow).where(CommunityStockRow.community_entity_id == community_id)
    if commodity is not None:
        statement = statement.where(CommunityStockRow.commodity == commodity)
    return list(await session.scalars(statement.order_by(CommunityStockRow.id)))


async def holding(session: AsyncSession, community_id: int, commodity: CommodityKind, material: MaterialKind | None = None) -> int:
    return sum(row.quantity for row in await lots_of(session, community_id, commodity) if material is None or row.material == material)


async def holdings(session: AsyncSession, community_id: int) -> dict[CommodityKind, int]:
    totals: dict[CommodityKind, int] = defaultdict(int)
    for row in await lots_of(session, community_id):
        totals[row.commodity] += row.quantity
    return dict(totals)


def epoch_need(rules: Rules, population: int, commodity: CommodityKind) -> int:
    return round_half_up(population * COMMODITIES[commodity].consumption(rules) / THOUSAND)


def aggregate_need(rules: Rules, population: int, aggregate: Commodity) -> int:
    return sum(epoch_need(rules, population, kind) for kind, item in COMMODITIES.items() if item.aggregate is aggregate)


def nourishment_need(rules: Rules, population: int) -> int:
    return sum(epoch_need(rules, population, kind) * item.nourishment for kind, item in COMMODITIES.items() if item.nourishment > 0)


def supply_index(rules: Rules, stocked: int, need: int) -> int:
    return round_half_up(stocked * rules.economy.supply_index_epoch / max(1, need))


async def aggregate_index(session: AsyncSession, rules: Rules, community: EntityRow, aggregate: Commodity) -> int:
    totals = await holdings(session, community.id)
    if aggregate is Commodity.FOOD:
        nourished = sum(quantity * COMMODITIES[kind].nourishment for kind, quantity in totals.items())
        return supply_index(rules, nourished, nourishment_need(rules, headcount(community)))
    stocked = sum(quantity for kind, quantity in totals.items() if COMMODITIES[kind].aggregate is aggregate)
    return supply_index(rules, stocked, aggregate_need(rules, headcount(community), aggregate))


async def sync_aggregates(session: AsyncSession, rules: Rules, community: EntityRow) -> CommunitySocietyRow | None:
    row = await session.get(CommunitySocietyRow, community.id)
    if row is None:
        return None
    for aggregate in Commodity:
        setattr(row, f"stock_{aggregate.value}", await aggregate_index(session, rules, community, aggregate))
    return row


def index_units(rules: Rules, community: EntityRow, aggregate: Commodity, index: int, mix: Mapping[CommodityKind, int]) -> int:
    if aggregate is not Commodity.FOOD:
        need = aggregate_need(rules, headcount(community), aggregate)
        return round_half_up(abs(index) * need / rules.economy.supply_index_epoch)
    weight = sum(mix.values())
    nourishing = sum(share * COMMODITIES[kind].nourishment for kind, share in mix.items()) / max(1, weight)
    if nourishing <= 0:
        return 0
    return round_half_up(abs(index) * nourishment_need(rules, headcount(community)) / rules.economy.supply_index_epoch / nourishing)


@dataclass(frozen=True)
class GoodsLedger:
    session: AsyncSession
    epoch: int

    async def record(self, community_id: int, commodity: CommodityKind, flow: GoodsFlow, quantity: int) -> None:
        if quantity == 0:
            return
        row = await self.session.get(GoodsFlowRow, (self.epoch, community_id, commodity, flow))
        if row is None:
            self.session.add(GoodsFlowRow(epoch=self.epoch, community_entity_id=community_id, commodity=commodity, flow=flow, quantity=quantity))
        else:
            row.quantity += quantity

    async def _lot(self, community_id: int, commodity: CommodityKind, material: MaterialKind | None, world_material_id: int | None) -> CommunityStockRow | None:
        for row in await lots_of(self.session, community_id, commodity):
            if row.material == material and row.world_material_id == world_material_id:
                return row
        return None

    async def add(
        self,
        community_id: int,
        commodity: CommodityKind,
        quantity: int,
        flow: GoodsFlow,
        *,
        material: MaterialKind | None = None,
        world_material_id: int | None = None,
        quality: int = DEFAULT_QUALITY,
    ) -> int:
        if quantity <= 0:
            return 0
        row = await self._lot(community_id, commodity, material, world_material_id)
        if row is None:
            row = CommunityStockRow(
                community_entity_id=community_id, commodity=commodity, material=material, world_material_id=world_material_id, quantity=0, quality=quality
            )
            self.session.add(row)
        total = row.quantity + quantity
        row.quality = clamp_int(round_half_up((row.quality * row.quantity + quality * quantity) / total), 0, PERCENT)
        row.quantity = total
        await self.record(community_id, commodity, flow, quantity)
        await self.session.flush()
        return quantity

    async def take(
        self,
        community_id: int,
        commodity: CommodityKind,
        quantity: int,
        flow: GoodsFlow,
        *,
        material: MaterialKind | None = None,
        world_material_id: int | None = None,
        best_first: bool = True,
    ) -> list[Lot]:
        if quantity <= 0:
            return []
        rows = [
            row
            for row in await lots_of(self.session, community_id, commodity)
            if row.quantity > 0 and (material is None or row.material == material) and (world_material_id is None or row.world_material_id == world_material_id)
        ]
        rows.sort(key=lambda row: (-row.quality if best_first else row.quality, row.id))
        taken: list[Lot] = []
        left = quantity
        for row in rows:
            if left <= 0:
                break
            part = min(left, row.quantity)
            row.quantity -= part
            left -= part
            taken.append(Lot(commodity, row.material, row.world_material_id, part, row.quality))
        await self.record(community_id, commodity, flow, -(quantity - left))
        await self.session.flush()
        return taken

    async def take_units(self, community_id: int, commodity: CommodityKind, quantity: int, flow: GoodsFlow) -> int:
        return sum(lot.quantity for lot in await self.take(community_id, commodity, quantity, flow))

    async def move(self, source_id: int, target_id: int, commodity: CommodityKind, quantity: int, *, flow: GoodsFlow) -> int:
        moved = 0
        for lot in await self.take(source_id, commodity, quantity, flow):
            moved += await self.add(
                target_id, commodity, lot.quantity, flow, material=lot.material, world_material_id=lot.world_material_id, quality=lot.quality
            )
        return moved

    async def shift_aggregate(self, rules: Rules, community: EntityRow, aggregate: Commodity, index_delta: int, *, flow: GoodsFlow) -> int:
        totals = await holdings(self.session, community.id)
        family = {kind: quantity for kind, quantity in totals.items() if COMMODITIES[kind].aggregate is aggregate and quantity > 0}
        split = dict(BACKFILL_SPLITS[aggregate])
        units = index_units(rules, community, aggregate, index_delta, split if index_delta > 0 else family)
        if units <= 0:
            return 0
        moved = 0
        if index_delta > 0:
            for kind, share in split.items():
                moved += await self.add(community.id, kind, round_half_up(units * share / PERCENT), flow)
        else:
            stocked = sum(family.values())
            for kind, quantity in sorted(family.items()):
                moved -= await self.take_units(community.id, kind, min(quantity, round_half_up(units * quantity / max(1, stocked))), flow)
        await sync_aggregates(self.session, rules, community)
        return moved

    async def move_aggregate(self, rules: Rules, source: EntityRow, target: EntityRow, aggregate: Commodity, *, index: int, flow: GoodsFlow) -> int:
        totals = await holdings(self.session, source.id)
        family = {kind: quantity for kind, quantity in totals.items() if COMMODITIES[kind].aggregate is aggregate and quantity > 0}
        units = index_units(rules, source, aggregate, index, family)
        stocked = sum(family.values())
        moved = 0
        for kind, quantity in sorted(family.items()):
            moved += await self.move(source.id, target.id, kind, min(quantity, round_half_up(units * quantity / max(1, stocked))), flow=flow)
        await sync_aggregates(self.session, rules, source)
        await sync_aggregates(self.session, rules, target)
        return moved


def goods_of(session: AsyncSession, epoch: int) -> GoodsLedger:
    return GoodsLedger(session, epoch)
