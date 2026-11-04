from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.mortal import KindVariantRow


async def variants_by_id(session: AsyncSession, ids: Iterable[int | None]) -> dict[int, KindVariantRow]:
    wanted = sorted({item for item in ids if item is not None})
    if not wanted:
        return {}
    return {row.id: row for row in await session.scalars(select(KindVariantRow).where(KindVariantRow.id.in_(wanted)))}


def strength(variants: dict[int, KindVariantRow], variant_id: int | None) -> float:
    row = variants.get(variant_id) if variant_id is not None else None
    return row.strength_pct / PERCENT if row is not None else 1.0


def learning(variants: dict[int, KindVariantRow], variant_id: int | None) -> float:
    row = variants.get(variant_id) if variant_id is not None else None
    return row.learning_pct / PERCENT if row is not None else 1.0
