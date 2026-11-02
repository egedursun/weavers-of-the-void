from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.society import son_relation_label
from aerona.db.repositories.sons import SonRepository, ordered_pair
from aerona.db.tables.sons import SonRelationRow
from aerona.domain.enums.limits import RELATION_MAX, RELATION_MIN
from aerona.domain.enums.son import SonRelationLabel
from aerona.rules.registry import Rules


@dataclass(frozen=True)
class SonRelation:
    first: int
    second: int
    value: int
    note: str | None
    label: SonRelationLabel


def relation_label(rules: Rules, value: int) -> SonRelationLabel:
    return son_relation_label(rules, value)


async def get_relation(session: AsyncSession, rules: Rules, first: int, second: int) -> SonRelation:
    row = await session.get(SonRelationRow, ordered_pair(first, second)) if first != second else None
    value = row.value if row is not None else 0
    a, b = ordered_pair(first, second)
    return SonRelation(a, b, value, row.note if row is not None else None, relation_label(rules, value))


async def change_relation(session: AsyncSession, rules: Rules, first: int, second: int, *, delta: float, note: str | None = None) -> SonRelation:
    await SonRepository(session).change_relation(first, second, delta, note)
    return await get_relation(session, rules, first, second)


async def set_relation(session: AsyncSession, rules: Rules, first: int, second: int, *, value: int, note: str | None = None) -> SonRelation:
    current = await SonRepository(session).relation(first, second)
    target = max(RELATION_MIN, min(RELATION_MAX, value))
    return await change_relation(session, rules, first, second, delta=target - current, note=note)


async def all_relations(session: AsyncSession, rules: Rules) -> list[SonRelation]:
    rows = await session.scalars(select(SonRelationRow).order_by(SonRelationRow.son_a_id, SonRelationRow.son_b_id))
    return [SonRelation(row.son_a_id, row.son_b_id, row.value, row.note, relation_label(rules, row.value)) for row in rows]
