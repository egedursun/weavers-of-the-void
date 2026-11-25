from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import AeronaError
from aerona.db.base import Base
from aerona.db.ledger_rows import parse_key
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.changes import StateChangeRow
from aerona.db.tables.interconnect import ModifierRow
from aerona.db.tables.lore import CanonFactRow
from aerona.db.tables.node import NodeRow
from aerona.domain.enums.meta import LedgerOperation
from aerona.domain.enums.modifier import ModifierSource
from aerona.domain.enums.team import CanonTouch
from aerona.engine.primitives.manual import silent
from aerona.services.container import Services
from aerona.services.divine_will.reading import Reading, summarise
from aerona.services.player.catalog import ActionSpec
from aerona.services.player.scope import PlayerScope
from aerona.services.team.execute import rules_in

HOLD_SOURCES = (ModifierSource.PIN, ModifierSource.SUPPRESSION)
HOLD_SOURCE_VALUES = frozenset(source.value for source in HOLD_SOURCES)
HOLD_TABLE = ModifierRow.__tablename__
FACT_TABLE = CanonFactRow.__tablename__
CANON_STATUS_ACTS = frozenset({"canon:set"})
SOURCE_COLUMN = "source_kind"
ID_COLUMN = "id"
LOCKED_LIST = "locked"
HELD_FLAG = "held"
LOCK_FIELDS = frozenset({LOCKED_LIST, HELD_FLAG})


@dataclass(frozen=True)
class CanonReading:
    touches: tuple[CanonTouch, ...]
    held_node_ids: tuple[int, ...]
    preview: dict[str, Any] = field(default_factory=dict)

    @property
    def locked(self) -> bool:
        return bool(self.touches)


class RehearsedError(Exception):
    def __init__(self, reading: CanonReading) -> None:
        super().__init__("rehearsed")
        self.reading = reading


async def held_among(session: AsyncSession, node_ids: set[int], epoch: int) -> set[int]:
    if not node_ids:
        return set()
    found = await session.scalars(
        select(ModifierRow.target_node_id).where(
            ModifierRow.target_node_id.in_(sorted(node_ids)),
            ModifierRow.source_kind.in_(HOLD_SOURCES),
            ModifierRow.start_epoch <= epoch,
            or_(ModifierRow.end_epoch.is_(None), ModifierRow.end_epoch >= epoch),
        )
    )
    return {int(node_id) for node_id in found if node_id is not None}


async def hold_rows_changed(session: AsyncSession, changes: list[StateChangeRow]) -> bool:
    ids: set[int] = set()
    for row in changes:
        if row.table_name != HOLD_TABLE:
            continue
        if row.operation is LedgerOperation.DELETE:
            whole = parse_key(row.before_text or "")
            if str(whole.get(SOURCE_COLUMN, "")) in HOLD_SOURCE_VALUES:
                return True
            continue
        found = parse_key(row.row_key).get(ID_COLUMN)
        if isinstance(found, int):
            ids.add(found)
    if not ids:
        return False
    held = await session.scalar(select(ModifierRow.id).where(ModifierRow.id.in_(sorted(ids)), ModifierRow.source_kind.in_(HOLD_SOURCES)).limit(1))
    return held is not None


async def locked_fields(session: AsyncSession, changes: list[StateChangeRow]) -> tuple[bool, bool]:
    lock_changed = any(row.field in LOCK_FIELDS for row in changes)
    fields: dict[tuple[str, str], set[str]] = {}
    for row in changes:
        if row.field is not None and row.field not in LOCK_FIELDS and row.operation is LedgerOperation.UPDATE:
            fields.setdefault((row.table_name, row.row_key), set()).add(row.field)
    for (table_name, row_key), touched in sorted(fields.items()):
        table = Base.metadata.tables.get(table_name)
        key = parse_key(row_key)
        if table is None or not key or not any(name in table.c for name in LOCK_FIELDS):
            continue
        wanted = [table.c[name] for name in sorted(LOCK_FIELDS) if name in table.c]
        found = (await session.execute(select(*wanted).where(*(table.c[column] == value for column, value in key.items() if column in table.c)))).first()
        if found is None:
            continue
        values = dict(zip(sorted(name for name in LOCK_FIELDS if name in table.c), found, strict=True))
        locked = values.get(LOCKED_LIST) or []
        if values.get(HELD_FLAG) is True or (isinstance(locked, list) and touched.intersection(str(item) for item in locked)):
            return lock_changed, True
    return lock_changed, False


async def reading_of(session: AsyncSession, spec: ActionSpec, changes: list[StateChangeRow], epoch: int) -> CanonReading:
    touched = {row.node_id for row in changes if row.node_id is not None} | {row.after_node_id for row in changes if row.after_node_id is not None}
    held = await held_among(session, touched, epoch)
    touches: list[CanonTouch] = []
    if spec.id in CANON_STATUS_ACTS:
        touches.append(CanonTouch.CANON_STATUS)
    if any(row.table_name == FACT_TABLE for row in changes):
        touches.append(CanonTouch.CANON_FACT)
    if held:
        touches.append(CanonTouch.HELD_THING)
    if await hold_rows_changed(session, changes):
        touches.append(CanonTouch.HOLD_CHANGED)
    lock_changed, locked_field = await locked_fields(session, changes)
    if lock_changed:
        touches.append(CanonTouch.LOCK_CHANGED)
    if locked_field:
        touches.append(CanonTouch.LOCKED_FIELD)
    named = await session.execute(select(NodeRow.id, NodeRow.name).where(NodeRow.id.in_(sorted(touched)))) if touched else None
    names = {int(node_id): str(name) for node_id, name in named} if named is not None else {}
    return CanonReading(tuple(touches), tuple(sorted(held)), summarise(Reading(changes, names)))


async def rehearse(services: Services, spec: ActionSpec, payload: Mapping[str, Any]) -> CanonReading:
    if spec.sync is None:
        return CanonReading((CanonTouch.CANON_STATUS,) if spec.id in CANON_STATUS_ACTS else (), ())
    sync = spec.sync
    command = spec.input_model.model_validate(dict(payload))
    try:
        async with services.database.write() as session:
            rules = await rules_in(services, session)
            outer = await session.begin_nested()
            try:
                marker = int(await session.scalar(select(func.coalesce(func.max(StateChangeRow.id), 0))) or 0)
                await sync(PlayerScope(session, rules, silent), command)
                await session.flush()
                changes = list(await session.scalars(select(StateChangeRow).where(StateChangeRow.id > marker).order_by(StateChangeRow.id)))
                cosmos = await CosmosRepository(session).require_cosmos()
                reading = await reading_of(session, spec, changes, cosmos.epoch)
            finally:
                if outer.is_active:
                    await outer.rollback()
            raise RehearsedError(reading)
    except RehearsedError as rehearsed:
        return rehearsed.reading
    except AeronaError:
        return CanonReading((), ())
