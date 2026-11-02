from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.agency import ActionRecordRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.cosmos import CosmosRow, CreatorRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.ledger import LedgerChangeRow, LedgerEntryRow
from aerona.db.tables.lore import ChronicleRow
from aerona.domain.enums.action import ActionKind
from aerona.events.kinds import EventKind
from tests.engine.gods.factories import add_world, bond, chronicle_keys, make_entity, make_son, seed_gods_world

__all__ = ["add_world", "bond", "chronicle_keys", "make_entity", "make_son"]


@dataclass
class PlayerWorld:
    cosmos: CosmosRow
    creator: CreatorRow
    world: WorldRow
    region: EntityRow


@dataclass
class Recorder:
    events: list[tuple[EventKind, dict[str, Any]]] = field(default_factory=list)

    def publish(self, kind: EventKind, payload: dict[str, Any]) -> None:
        self.events.append((kind, payload))

    def kinds(self) -> list[EventKind]:
        return [kind for kind, _ in self.events]


async def seed_player_world(session: AsyncSession) -> PlayerWorld:
    seeded = await seed_gods_world(session)
    seeded.cosmos.primary_world_id = seeded.world.id
    await session.flush()
    return PlayerWorld(seeded.cosmos, seeded.creator, seeded.world, seeded.region)


async def ledger_entries(session: AsyncSession) -> list[LedgerEntryRow]:
    return list(await session.scalars(select(LedgerEntryRow).order_by(LedgerEntryRow.id)))


async def ledger_changes(session: AsyncSession, entry_id: int) -> list[LedgerChangeRow]:
    return list(await session.scalars(select(LedgerChangeRow).where(LedgerChangeRow.entry_id == entry_id).order_by(LedgerChangeRow.id)))


async def changed_tables(session: AsyncSession, entry_id: int | None) -> set[str]:
    assert entry_id is not None
    return {change.table_name for change in await ledger_changes(session, entry_id)}


async def action_kinds(session: AsyncSession) -> list[ActionKind]:
    return list(await session.scalars(select(ActionRecordRow.kind).order_by(ActionRecordRow.id)))


async def chronicle_texts(session: AsyncSession) -> list[str]:
    return list(await session.scalars(select(ChronicleRow.text).order_by(ChronicleRow.id)))


async def count_rows(session: AsyncSession, table: Any) -> int:
    return int(await session.scalar(select(func.count()).select_from(table)) or 0)
