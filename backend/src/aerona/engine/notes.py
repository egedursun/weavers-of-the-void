from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.lore import ChronicleEntityRow, ChronicleRow
from aerona.rules.registry import Rules

LINK_CHUNK = 500


@dataclass(frozen=True)
class FoldResult:
    folded_groups: int
    hidden_duplicates: int


async def last_chronicle_id(session: AsyncSession) -> int:
    return int(await session.scalar(select(func.max(ChronicleRow.id))) or 0)


async def tick_rows(session: AsyncSession, epoch: int, since_id: int) -> list[ChronicleRow]:
    statement = select(ChronicleRow).where(ChronicleRow.epoch == epoch, ChronicleRow.id > since_id).order_by(ChronicleRow.id)
    return list(await session.scalars(statement))


async def linked_ids(session: AsyncSession, chronicle_ids: list[int]) -> dict[int, tuple[int, ...]]:
    found: dict[int, list[int]] = {chronicle_id: [] for chronicle_id in chronicle_ids}
    for start in range(0, len(chronicle_ids), LINK_CHUNK):
        statement = (
            select(ChronicleEntityRow.chronicle_id, ChronicleEntityRow.entity_id)
            .where(ChronicleEntityRow.chronicle_id.in_(chronicle_ids[start : start + LINK_CHUNK]))
            .order_by(ChronicleEntityRow.chronicle_id, ChronicleEntityRow.position)
        )
        for chronicle_id, entity_id in await session.execute(statement):
            found[chronicle_id].append(entity_id)
    return {chronicle_id: tuple(ids) for chronicle_id, ids in found.items()}


async def fold_tick_lines(session: AsyncSession, rules: Rules, epoch: int, since_id: int) -> FoldResult:
    rows = await tick_rows(session, epoch, since_id)
    ids_of = await linked_ids(session, [row.id for row in rows])
    by_event: dict[tuple[str | None, frozenset[int]], list[ChronicleRow]] = defaultdict(list)
    by_template: dict[str, list[ChronicleRow]] = defaultdict(list)
    for row in rows:
        by_event[(row.template_key, frozenset(ids_of[row.id]))].append(row)
        if row.template_key:
            by_template[row.template_key].append(row)
    twins = sum(len(group) - 1 for group in by_event.values() if len(group) > 1)
    threshold = rules.world_engine.chronicle_fold_threshold
    grouped = sum(1 for group in by_template.values() if len(group) >= threshold)
    return FoldResult(folded_groups=grouped, hidden_duplicates=twins)
