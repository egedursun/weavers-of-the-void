import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.ledger_capture import LEDGER_TABLES, TURN_TABLES, LedgerDraft, capture_changes
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.ledger import LedgerChangeRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.entity import EntityFlag, EntityType
from aerona.domain.enums.meta import LedgerOperation
from aerona.domain.enums.node import ActorKind
from tests.db.factories import make_entity

DRAFT = LedgerDraft(
    epoch=1, actor_kind=ActorKind.ENGINE, actor_node_id=None, actor_name="engine", tool="test", action_kind=ActionKind.OTHER, input_summary=None
)


async def test_capture_records_bulk_statements_with_json_keys(session: AsyncSession, world_id: int) -> None:
    region = await make_entity(session, "Ashvale", EntityType.REGION, world_id=world_id)
    entities = EntityRepository(session)
    await entities.add_flag(region.id, EntityFlag.PROTECTED, 1)
    async with capture_changes(session) as capture:
        await entities.remove_flag(region.id, EntityFlag.PROTECTED)
        region.description = "A changed vale."
        entry_id = await capture.seal(DRAFT)
    assert entry_id is not None
    changes = list(await session.scalars(select(LedgerChangeRow).where(LedgerChangeRow.entry_id == entry_id)))
    operations = {(change.table_name, change.operation) for change in changes}
    assert ("entity_flags", LedgerOperation.DELETE) in operations
    assert ("entities", LedgerOperation.UPDATE) in operations
    assert all(isinstance(json.loads(change.row_key), dict) for change in changes)


async def test_capture_skips_untracked_tables(session: AsyncSession, world_id: int) -> None:
    async with capture_changes(session, LEDGER_TABLES | TURN_TABLES) as capture:
        await make_entity(session, "Brinehold", EntityType.REGION, world_id=world_id)
        changes = await capture.changes()
    assert {change.table_name for change in changes} >= {"entities"}
    assert not {change.table_name for change in changes} & (LEDGER_TABLES | TURN_TABLES)
