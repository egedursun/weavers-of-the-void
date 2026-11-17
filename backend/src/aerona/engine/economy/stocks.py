from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass

from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import ORMExecuteState, Session
from sqlalchemy.orm.attributes import instance_state

from aerona.catalog.commodities import BACKFILL_SPLITS, COMMODITIES
from aerona.constants.units import PERCENT
from aerona.db.attr_history import changed
from aerona.db.read_memo import register_index, touched_rows
from aerona.db.tables.economy import CommunityStockRow, GoodsFlowRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.write_guard import held
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


FLOW_INDEX = "aerona.economy.goods_flows"
FlowKey = tuple[CommodityKind, GoodsFlow]


async def flows_of(session: AsyncSession, epoch: int, community_id: int) -> dict[FlowKey, GoodsFlowRow]:
    index: dict[tuple[int, int], dict[FlowKey, GoodsFlowRow]] = session.sync_session.info.setdefault(FLOW_INDEX, {})
    found = index.get((epoch, community_id))
    if found is None:
        statement = select(GoodsFlowRow).where(GoodsFlowRow.epoch == epoch, GoodsFlowRow.community_entity_id == community_id)
        found = {(row.commodity, row.flow): row for row in await session.scalars(statement)}
        index[(epoch, community_id)] = found
    return found


def drop_flows(sync: Session, *_: object) -> None:
    sync.info.pop(FLOW_INDEX, None)


def follow_flows(sync: Session, *_: object) -> None:
    if FLOW_INDEX in sync.info and touched_rows(sync, GoodsFlowRow)[2]:
        drop_flows(sync)


def drop_flows_on_write(state: ORMExecuteState) -> None:
    if not state.is_select and getattr(getattr(state.statement, "table", None), "name", GoodsFlowRow.__tablename__) == GoodsFlowRow.__tablename__:
        drop_flows(state.session)


event.listen(Session, "after_flush", follow_flows)
event.listen(Session, "after_soft_rollback", drop_flows)
event.listen(Session, "do_orm_execute", drop_flows_on_write)
register_index(FLOW_INDEX)


LOTS_INDEX = "aerona.economy.lots"


def lot_index(sync: Session) -> dict[int, list[CommunityStockRow]]:
    found: dict[int, list[CommunityStockRow]] = sync.info.setdefault(LOTS_INDEX, {})
    return found


def note_lot(sync: Session, instance: object) -> None:
    if not isinstance(instance, CommunityStockRow) or LOTS_INDEX not in sync.info:
        return
    if instance.community_entity_id is None:
        drop_lots(sync)
        return
    known = lot_index(sync).get(instance.community_entity_id)
    if known is not None and instance not in known:
        known.append(instance)


def unnote_lot(sync: Session, instance: object) -> None:
    if not isinstance(instance, CommunityStockRow) or LOTS_INDEX not in sync.info:
        return
    known = lot_index(sync).get(instance.community_entity_id) if instance.community_entity_id is not None else None
    if known is not None and instance in known:
        known.remove(instance)


def follow_lots(sync: Session, *_: object) -> None:
    if LOTS_INDEX not in sync.info:
        return
    dirty, deleted = touched_rows(sync, CommunityStockRow)[1:]
    if any(changed(instance_state(row), "community_entity_id") for row in dirty):
        drop_lots(sync)
        return
    for row in deleted:
        unnote_lot(sync, row)


def drop_lots(sync: Session, *_: object) -> None:
    sync.info.pop(LOTS_INDEX, None)


def drop_lots_on_write(state: ORMExecuteState) -> None:
    if not state.is_select and getattr(getattr(state.statement, "table", None), "name", CommunityStockRow.__tablename__) == CommunityStockRow.__tablename__:
        drop_lots(state.session)


event.listen(Session, "transient_to_pending", note_lot)
event.listen(Session, "pending_to_transient", unnote_lot)
event.listen(Session, "after_flush", follow_lots)
event.listen(Session, "after_soft_rollback", drop_lots)
event.listen(Session, "do_orm_execute", drop_lots_on_write)
register_index(LOTS_INDEX)


def unsettled(sync: Session, lots: list[CommunityStockRow]) -> bool:
    if any(row.id is None for row in lots):
        return True
    return bool(sync._deleted) and any(isinstance(item, CommunityStockRow) and item in lots for item in sync.deleted)


async def lots_of(session: AsyncSession, community_id: int, commodity: CommodityKind | None = None) -> list[CommunityStockRow]:
    sync = session.sync_session
    lots = lot_index(sync).get(community_id)
    if lots is not None and unsettled(sync, lots):
        await session.flush()
        lots = lot_index(sync).get(community_id)
    if lots is None:
        statement = select(CommunityStockRow).where(CommunityStockRow.community_entity_id == community_id)
        lots = list(await session.scalars(statement.order_by(CommunityStockRow.id)))
        lot_index(sync)[community_id] = lots
    return [row for row in lots if commodity is None or row.commodity == commodity]


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
    if aggregate is Commodity.FOOD:
        return round_half_up(nourishment_need(rules, population) / COMMODITIES[CommodityKind.GRAIN].nourishment)
    return sum(epoch_need(rules, population, kind) for kind, item in COMMODITIES.items() if item.aggregate is aggregate)


def nourishment_need(rules: Rules, population: int) -> int:
    return round_half_up(population * rules.consumption.nourishment_per_1000 / THOUSAND)


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
        if quantity == 0 or held(community_id):
            return
        flows = await flows_of(self.session, self.epoch, community_id)
        row = flows.get((commodity, flow))
        if row is None:
            row = flows[(commodity, flow)] = GoodsFlowRow(epoch=self.epoch, community_entity_id=community_id, commodity=commodity, flow=flow, quantity=quantity)
            self.session.add(row)
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
        force: bool = False,
    ) -> int:
        if quantity <= 0 or (held(community_id) and not force):
            return 0
        row = await self._lot(community_id, commodity, material, world_material_id)
        if row is not None and row.held and not force:
            return 0
        if row is None:
            row = CommunityStockRow(
                community_entity_id=community_id, commodity=commodity, material=material, world_material_id=world_material_id, quantity=0, quality=quality
            )
            self.session.add(row)
        total = row.quantity + quantity
        row.quality = clamp_int(round_half_up((row.quality * row.quantity + quality * quantity) / total), 0, PERCENT)
        row.quantity = total
        await self.record(community_id, commodity, flow, quantity)
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
        force: bool = False,
        exclude: frozenset[MaterialKind] = frozenset(),
        exclude_worlds: frozenset[int] = frozenset(),
    ) -> list[Lot]:
        if quantity <= 0 or (held(community_id) and not force):
            return []
        rows = [
            row
            for row in await lots_of(self.session, community_id, commodity)
            if row.quantity > 0
            and (force or not row.held)
            and (material is None or row.material == material)
            and (world_material_id is None or row.world_material_id == world_material_id)
            and row.material not in exclude
            and row.world_material_id not in exclude_worlds
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
        return taken

    async def shift_lot(self, row: CommunityStockRow, delta: int, flow: GoodsFlow) -> int:
        if delta == 0 or row.held or held(row.community_entity_id):
            return 0
        applied = max(delta, -row.quantity)
        row.quantity += applied
        await self.record(row.community_entity_id, row.commodity, flow, applied)
        return applied

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
