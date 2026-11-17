from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.kind_concepts.registry import CONCEPTS
from aerona.db.kind_concepts.spec import ConceptSpec
from aerona.db.tables.kinds import KindHoldingRow, KindRow
from aerona.domain.enums.kinds import KindConcept
from aerona.engine.kinds.acts import HOLDINGS

KEY_SPAN = 1_000_000_000
ORDER = list(KindConcept)


def kind_key(concept: KindConcept, kind_id: int) -> int:
    return ORDER.index(concept) * KEY_SPAN + kind_id


def kind_of_key(key: int) -> tuple[ConceptSpec | None, int]:
    return CONCEPTS.get(ORDER[key // KEY_SPAN]), key % KEY_SPAN


def counted(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def out_of_range(spec: ConceptSpec, kind: KindRow) -> bool:
    return any(not item.low <= getattr(kind, item.column) <= item.high for item in spec.properties if counted(getattr(kind, item.column)))


async def stray_holdings(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for holding in await session.scalars(select(KindHoldingRow).order_by(KindHoldingRow.id)):
        spec = CONCEPTS.get(holding.concept)
        if spec is None or await session.get(spec.table, holding.kind_id) is None:
            found.append(holding.id)
    return found


async def drop_holding(session: AsyncSession, holding_id: int) -> None:
    session.info.pop(HOLDINGS, None)
    await session.execute(delete(KindHoldingRow).where(KindHoldingRow.id == holding_id))


async def tangled_lineage(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for concept, spec in CONCEPTS.items():
        ids = set(await session.scalars(select(spec.table.id)))
        for kind in await session.scalars(select(spec.table).where(spec.table.derived_from_id.is_not(None)).order_by(spec.table.id)):
            if kind.derived_from_id == kind.id or kind.derived_from_id not in ids:
                found.append(kind_key(concept, kind.id))
    return found


async def cut_lineage(session: AsyncSession, key: int) -> None:
    spec, kind_id = kind_of_key(key)
    kind = await session.get(spec.table, kind_id) if spec is not None else None
    if kind is not None:
        kind.derived_from_id = None


async def kinds_out_of_range(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for concept, spec in CONCEPTS.items():
        found.extend(kind_key(concept, kind.id) for kind in await session.scalars(select(spec.table).order_by(spec.table.id)) if out_of_range(spec, kind))
    return found


async def bring_into_range(session: AsyncSession, key: int) -> None:
    spec, kind_id = kind_of_key(key)
    kind = await session.get(spec.table, kind_id) if spec is not None else None
    if spec is None or kind is None:
        return
    for item in spec.properties:
        value = getattr(kind, item.column)
        if counted(value):
            setattr(kind, item.column, min(item.high, max(item.low, value)))
