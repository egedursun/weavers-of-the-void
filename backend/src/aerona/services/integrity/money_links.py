from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.money import MONEY_FORMS
from aerona.db.kind_concepts.nature import ORIGIN_SOURCE, SOURCE_NODES
from aerona.db.tables.economy import CurrencyRow, WorldMaterialRow
from aerona.db.tables.node import NodeRow

NON_METAL = [form for form, spec in MONEY_FORMS.items() if not spec.uses_metal]


async def metal_paper(session: AsyncSession) -> list[int]:
    query = select(CurrencyRow.id).where(CurrencyRow.metal.is_not(None), CurrencyRow.form.in_(NON_METAL)).order_by(CurrencyRow.id)
    return list(await session.scalars(query))


async def clear_metal(session: AsyncSession, currency_id: int) -> None:
    await session.execute(update(CurrencyRow).where(CurrencyRow.id == currency_id).values(metal=None))


async def stray_sources(session: AsyncSession) -> list[int]:
    query = select(WorldMaterialRow.id, WorldMaterialRow.origin, NodeRow.kind).join(NodeRow, NodeRow.id == WorldMaterialRow.source_node_id)
    return sorted(row_id for row_id, origin, kind in await session.execute(query) if kind not in SOURCE_NODES[ORIGIN_SOURCE[origin]])


async def clear_source(session: AsyncSession, material_id: int) -> None:
    await session.execute(update(WorldMaterialRow).where(WorldMaterialRow.id == material_id).values(source_node_id=None))
