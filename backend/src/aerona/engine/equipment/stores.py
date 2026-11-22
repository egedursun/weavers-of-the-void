from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.goods_tables import FORGED
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.equipment import EquipmentModelRow, EquipmentStoreRow, UnitDesignEquipmentRow
from aerona.db.tables.military import UnitDesignRow
from aerona.db.write_guard import held
from aerona.domain.enums.economy import GoodsFlow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.engine.context import TickContext
from aerona.engine.economy.stocks import goods_of, holding
from aerona.engine.equipment.models import model_for
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.renown.currencies import realm_of_community


@dataclass
class ForgeTally:
    forged: int = 0
    models: int = 0


async def store_of(session: AsyncSession, holder_id: int, model_id: int) -> EquipmentStoreRow | None:
    return await session.get(EquipmentStoreRow, (holder_id, model_id))


async def stores_of(session: AsyncSession, holder_id: int) -> list[EquipmentStoreRow]:
    statement = select(EquipmentStoreRow).where(EquipmentStoreRow.holder_node_id == holder_id, EquipmentStoreRow.count > 0)
    return list(await session.scalars(statement.order_by(EquipmentStoreRow.model_id)))


async def add_pieces(session: AsyncSession, holder_id: int, model_id: int, count: int) -> int:
    if count <= 0 or held(holder_id):
        return 0
    row = await store_of(session, holder_id, model_id)
    if row is None:
        row = EquipmentStoreRow(holder_node_id=holder_id, model_id=model_id, count=0, locked=[])
        session.add(row)
    if "count" in (row.locked or []):
        return 0
    row.count += count
    return count


async def take_pieces(session: AsyncSession, holder_id: int, model_id: int, count: int) -> int:
    if count <= 0 or held(holder_id):
        return 0
    row = await store_of(session, holder_id, model_id)
    if row is None or "count" in (row.locked or []):
        return 0
    taken = min(row.count, count)
    row.count -= taken
    return taken


async def kit_models(session: AsyncSession, holder_id: int) -> list[EquipmentModelRow]:
    statement = (
        select(EquipmentModelRow)
        .join(UnitDesignEquipmentRow, UnitDesignEquipmentRow.model_id == EquipmentModelRow.id)
        .join(UnitDesignRow, UnitDesignRow.id == UnitDesignEquipmentRow.design_id)
        .where(UnitDesignRow.owner_entity_id == holder_id, UnitDesignRow.retired.is_(False))
        .distinct()
        .order_by(EquipmentModelRow.id)
    )
    return list(await session.scalars(statement))


async def forge(ctx: TickContext, town: EntityRow, holder: EntityRow, knowledge: KnowledgeMap, tally: ForgeTally) -> None:
    if held(holder.id) or held(town.id):
        return
    table = ctx.rules.armament
    kit = max(1, ctx.rules.materials.soldiers_per_kit)
    ledger = goods_of(ctx.session, ctx.epoch)
    for commodity, slots in FORGED.items():
        stock = await holding(ctx.session, town.id, commodity)
        budget = round_half_up(stock * table.forge_share_pct / PERCENT)
        if budget <= 0:
            continue
        models = [model for model in await kit_models(ctx.session, holder.id) if model.slot in slots]
        for slot in slots:
            if any(model.slot is slot for model in models):
                continue
            model = await model_for(ctx, holder, slot, knowledge)
            if model is not None:
                models.append(model)
        if not models:
            continue
        share = max(1, budget // len(models))
        for model in models:
            used = await ledger.take_units(town.id, commodity, share, GoodsFlow.INPUT)
            pieces = used * kit // max(1, 1 + model.crew)
            tally.forged += await add_pieces(ctx.session, holder.id, model.id, pieces)
            tally.models += 1


async def forge_all(ctx: TickContext) -> ForgeTally:
    tally = ForgeTally()
    knowledge = await KnowledgeMap.load(ctx.session)
    towns = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    for town in list(towns):
        realm_id = await realm_of_community(ctx.session, town.id)
        holder = await living_entity(ctx.session, realm_id) if realm_id is not None else town
        if holder is not None:
            await forge(ctx, town, holder, knowledge, tally)
    return tally
