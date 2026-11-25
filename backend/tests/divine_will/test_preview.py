from dataclasses import dataclass

from sqlalchemy import func, select

from aerona.db.tables.agency import ActionRecordRow
from aerona.db.tables.changes import StateChangeRow
from aerona.db.tables.cosmos import CreatorRow
from aerona.db.tables.ledger import LedgerEntryRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.son import SonStatus
from aerona.services.divine_will.player import CatalogPlayer
from tests.api.conftest import ApiWorld, seeded

BACKGROUND_TABLES = ("jobs", "divine_will_chunks")


@dataclass(frozen=True)
class Snapshot:
    last_change: int
    ledger_entries: int
    action_records: int
    essence: int
    contentment: int
    son_status: SonStatus


async def snapshot(api: ApiWorld) -> Snapshot:
    async with api.services.database.read() as session:
        creator = (await session.scalars(select(CreatorRow))).one()
        son = await session.get(SonRow, seeded(api).core.son.id)
        assert son is not None
        return Snapshot(
            last_change=int(
                await session.scalar(select(func.coalesce(func.max(StateChangeRow.id), 0)).where(StateChangeRow.table_name.not_in(BACKGROUND_TABLES))) or 0
            ),
            ledger_entries=int(await session.scalar(select(func.count()).select_from(LedgerEntryRow)) or 0),
            action_records=int(await session.scalar(select(func.count()).select_from(ActionRecordRow)) or 0),
            essence=creator.essence,
            contentment=creator.mood_contentment,
            son_status=son.status,
        )


async def test_a_preview_of_a_nested_act_leaves_the_world_as_it_was(will: ApiWorld) -> None:
    before = await snapshot(will)
    wanted = 3 if before.contentment != 3 else 7
    preview = await CatalogPlayer(will.services).preview("creator:mood", {"contentment": wanted})
    assert preview["ok"] is True, preview
    assert any(line["field"] == "mood_contentment" and line["after"] == wanted for line in preview["changes"]), preview["changes"]
    assert preview["destructive"] is False
    assert preview["ledger_entry_id"] is None
    assert await snapshot(will) == before


async def test_a_preview_of_a_killing_is_destructive_and_costly_and_undone(will: ApiWorld) -> None:
    before = await snapshot(will)
    son_id = seeded(will).core.son.id
    preview = await CatalogPlayer(will.services).preview("kill:son", {"son_id": son_id, "reason": "A test."})
    assert preview["ok"] is True, preview
    assert preview["destructive"] is True
    assert preview["costly"] is True
    assert preview["reason"] == "both"
    assert preview["essence"] > 0
    assert any(line["node_id"] == son_id and line["after"] == SonStatus.DEAD.value for line in preview["ended"]), preview["ended"]
    assert await snapshot(will) == before


async def test_a_job_act_is_not_rehearsed_and_shows_its_declared_cost(will: ApiWorld) -> None:
    before = await snapshot(will)
    preview = await CatalogPlayer(will.services).preview("summon_son", {})
    assert preview["ok"] is True, preview
    assert preview["job"] is True
    assert preview["essence"] == will.services.rules.current.costs.summon_son
    assert preview["costly"] is True
    assert preview["changes"] == []
    assert await snapshot(will) == before


async def test_a_preview_with_a_wrong_input_is_refused_without_change(will: ApiWorld) -> None:
    before = await snapshot(will)
    preview = await CatalogPlayer(will.services).preview("kill:son", {"son_id": "nobody"})
    assert preview["ok"] is False
    assert preview["error"]
    assert await snapshot(will) == before


async def test_perform_runs_the_act_through_the_ledger(will: ApiWorld) -> None:
    before = await snapshot(will)
    wanted = 3 if before.contentment != 3 else 7
    done = await CatalogPlayer(will.services).perform("creator:mood", {"contentment": wanted})
    assert done["ok"] is True, done
    assert done["ledger_entry_id"] is not None
    after = await snapshot(will)
    assert after.contentment == wanted
    assert after.ledger_entries == before.ledger_entries + 1
    undone = await CatalogPlayer(will.services).undo(int(done["ledger_entry_id"]))
    assert undone["ok"] is True, undone
    assert (await snapshot(will)).contentment == before.contentment
