import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import ValidationFailedError
from aerona.db.tables.agency import ActionRecordRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.meta import LedgerOperation
from aerona.services.player import creator
from aerona.services.player.scope import PlayerScope
from tests.services.player.factories import PlayerWorld, action_kinds, chronicle_texts, ledger_changes, ledger_entries


async def test_ledgered_action_records_changes_and_action(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    outcome = await creator.edit_creator(scope, creator.EditCreator(title="the Weaver"))
    assert world.creator.title == "the Weaver"
    entries = await ledger_entries(session)
    assert [entry.tool for entry in entries] == ["creator:edit"]
    assert outcome.ledger_entry_id == entries[0].id
    changes = await ledger_changes(session, entries[0].id)
    by_table = {change.table_name: change for change in changes}
    assert by_table["creator"].operation is LedgerOperation.UPDATE
    assert by_table["creator"].before is not None and by_table["creator"].before["title"] is None
    assert by_table["creator"].after is not None and by_table["creator"].after["title"] == "the Weaver"
    assert by_table["chronicle"].operation is LedgerOperation.INSERT
    assert by_table["action_records"].after is not None and by_table["action_records"].after["ledger_entry_id"] == entries[0].id
    assert await action_kinds(session) == [ActionKind.EDIT_CREATOR]
    assert any("the Weaver" not in text and "reshaped" in text for text in await chronicle_texts(session))


async def test_rejected_action_leaves_no_trace(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    with pytest.raises(ValidationFailedError):
        await creator.edit_creator(scope, creator.EditCreator())
    assert await ledger_entries(session) == []
    assert await session.get(ActionRecordRow, 1) is None


async def test_service_recorded_action_is_not_doubled(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    await creator.set_mood(scope, creator.SetMood(anger=95))
    assert world.creator.mood_anger == 95
    assert await action_kinds(session) == [ActionKind.EDIT_CREATOR]
    entries = await ledger_entries(session)
    assert len(entries) == 1
