from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.base import Base
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held, write_blocked
from aerona.engine.primitives.stats import set_stats, shift_stat


class EffectKind(StrEnum):
    SET_STAT = "set_stat"
    SHIFT_STAT = "shift_stat"
    SET_COLUMN = "set_column"


@dataclass(frozen=True, order=True)
class Effect:
    shard: tuple[int, ...]
    entity_id: int
    sequence: int
    kind: EffectKind
    field: str
    value: Any
    table: str = ""


def merged(results: Iterable[Sequence[Effect]]) -> list[Effect]:
    return sorted((effect for found in results for effect in found), key=lambda effect: (effect.shard, effect.entity_id, effect.sequence))


def row_type(table: str) -> type[Base]:
    for mapper in Base.registry.mappers:
        if mapper.local_table is not None and getattr(mapper.local_table, "name", None) == table:
            found: type[Base] = mapper.class_
            return found
    raise KeyError(table)


async def commit(session: AsyncSession, effects: Sequence[Effect]) -> int:
    applied = 0
    for effect in effects:
        if held(effect.entity_id) or write_blocked(effect.entity_id, effect.field):
            continue
        if effect.kind is EffectKind.SET_COLUMN:
            row = await session.get(row_type(effect.table), effect.entity_id)
            if row is None or effect.field in (getattr(row, "locked", None) or []):
                continue
            setattr(row, effect.field, effect.value)
            applied += 1
            continue
        entity = await session.get(EntityRow, effect.entity_id)
        if entity is None:
            continue
        if effect.kind is EffectKind.SET_STAT:
            set_stats(entity, **{effect.field: effect.value})
        else:
            shift_stat(entity, effect.field, effect.value)
        applied += 1
    await session.flush()
    return applied
