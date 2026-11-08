from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.ledger_capture import LedgerDraft, capture_changes
from aerona.db.ledger_undo import undo_entry
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.entities import EntityFlagRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.entity import EntityFlag, EntityType
from aerona.domain.enums.node import ActorKind
from tests.db.factories import make_entity

DRAFT = LedgerDraft(
    epoch=1, actor_kind=ActorKind.ENGINE, actor_node_id=None, actor_name="engine", tool="test", action_kind=ActionKind.OTHER, input_summary=None
)


async def removed_flag(session: AsyncSession, world_id: int) -> tuple[int, int]:
    region = await make_entity(session, "Ashvale", EntityType.REGION, world_id=world_id)
    entities = EntityRepository(session)
    await entities.add_flag(region.id, EntityFlag.PROTECTED, 1)
    async with capture_changes(session) as capture:
        await entities.remove_flag(region.id, EntityFlag.PROTECTED)
        entry_id = await capture.seal(DRAFT)
    assert entry_id is not None
    return region.id, entry_id


async def test_undoing_a_deletion_restores_the_row(session: AsyncSession, world_id: int) -> None:
    region_id, entry_id = await removed_flag(session, world_id)
    assert await session.get(EntityFlagRow, (region_id, EntityFlag.PROTECTED)) is None
    report = await undo_entry(session, entry_id, 2)
    assert any(line.endswith("restored") for line in report.applied) and report.conflicts == []
    assert await session.get(EntityFlagRow, (region_id, EntityFlag.PROTECTED), populate_existing=True) is not None


async def test_undoing_a_deletion_whose_key_was_taken_again_reports_a_conflict(session: AsyncSession, world_id: int) -> None:
    region_id, entry_id = await removed_flag(session, world_id)
    session.add(EntityFlagRow(entity_id=region_id, flag=EntityFlag.PROTECTED, epoch=5))
    await session.flush()
    report = await undo_entry(session, entry_id, 6)
    assert report.conflicts and "same key" in report.conflicts[0]


async def test_undoing_a_deletion_of_a_row_already_back_as_it_was_does_nothing(session: AsyncSession, world_id: int) -> None:
    region_id, entry_id = await removed_flag(session, world_id)
    session.add(EntityFlagRow(entity_id=region_id, flag=EntityFlag.PROTECTED, epoch=1))
    await session.flush()
    report = await undo_entry(session, entry_id, 6)
    assert report.conflicts == [] and not any(line.endswith("restored") for line in report.applied)
