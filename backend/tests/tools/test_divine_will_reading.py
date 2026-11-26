import asyncio
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

from sqlalchemy import func, select

from aerona.db.profile_guard import table_name
from aerona.db.session import Database
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.changes import StateChangeRow
from aerona.db.tables.cosmos import CreatorRow
from aerona.db.tables.divine_will import DivineWillConfirmationRow, DivineWillCycleRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.team import QueuedActRow
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.divine_will import ConfirmationReason, ConfirmationStatus, CycleStatus, DivineWillMode
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.job import JobKind
from aerona.domain.enums.meta import LedgerOperation
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.team import QueuedActStatus
from aerona.engine.primitives.stats import set_stats
from aerona.epoch.concurrency import WORLD_GROUP
from aerona.events.bus import EventBus
from aerona.jobs.context import JobContext
from aerona.jobs.manager import JobManager
from aerona.prompts.tools.divine_will_ids import DivineWillToolId
from aerona.rules.registry import Rules
from aerona.tools.divine_will.framework import WillCall, WillResult
from aerona.tools.divine_will.read import unknown_kind
from aerona.tools.divine_will.rows import every_table
from tests.tools.every_divine_will_tool import call_tool, harness_player, will_call, will_world
from tests.tools.factories import make_entity

W = DivineWillToolId
SMALL_PAGES = replace(Rules(), divine_will=replace(Rules().divine_will, page_tokens=500))


def head(result: WillResult) -> dict[str, Any]:
    found: dict[str, Any] = json.loads(result.text.split("\n", 1)[0])
    return found


async def every_page(call: WillCall, tool: DivineWillToolId, arguments: dict[str, Any]) -> list[WillResult]:
    pages = [await call_tool(call, tool, arguments)]
    while head(pages[-1])["next"]:
        pages.append(await call_tool(call, W.READ_MORE, {"handle": pages[-1].handle}))
        assert not pages[-1].is_error, pages[-1].text
    return pages


def listed(pages: list[WillResult]) -> list[str]:
    return [line for page in pages for line in page.text.splitlines() if line.startswith("- ")]


async def test_enumerate_pages_reach_every_record_once(database: Database, tmp_path: Path) -> None:
    world = await will_world(database)
    async with database.write() as session:
        for number in range(80):
            await make_entity(session, f"Walker {number:03d}", EntityType.MORTAL, world_id=world.realm.cosmos.world_id, location_id=world.realm.settlement_id)
    call = will_call(database, world, DivineWillMode.ASK_LORE, tmp_path, rules=SMALL_PAGES)
    pages = await every_page(call, W.ENUMERATE, {"kind": "mortal", "sort": ["name"]})
    lines = listed(pages)
    names = [line.split("name: ", 1)[1].split(" · ", 1)[0] for line in lines]
    assert len(pages) > 3
    assert names == sorted(names) and len(names) == len(set(names)) == 81
    assert head(pages[0])["total"] == 81
    assert [head(page)["page"] for page in pages] == list(range(1, len(pages) + 1))


async def test_paged_lists_reach_every_table(database: Database, tmp_path: Path) -> None:
    world = await will_world(database)
    call = will_call(database, world, DivineWillMode.ASK_LORE, tmp_path, rules=SMALL_PAGES)
    pages = await every_page(call, W.ENUMERATE, {"kind": "tables"})
    shown = [line[2:].split(":", 1)[0] for line in listed(pages)]
    assert shown == [table_name(mapper) for mapper in every_table()]
    assert sum(head(page)["shown"] for page in pages) == head(pages[0])["total"]


async def test_a_page_past_the_end_says_so(database: Database, tmp_path: Path) -> None:
    world = await will_world(database)
    call = will_call(database, world, DivineWillMode.ASK_LORE, tmp_path)
    result = await call_tool(call, W.CHRONICLE, {"page": 40})
    assert not result.is_error and head(result)["next"] is False
    result = await call_tool(call, W.ENUMERATE, {"kind": "mortal", "page": 9})
    assert "There is no page 9" in result.text and head(result)["shown"] == 0


async def test_read_more_continues_a_handle_only_while_its_exchange_is_remembered(database: Database, tmp_path: Path) -> None:
    world = await will_world(database)
    first = await call_tool(will_call(database, world, DivineWillMode.ASK_LORE, tmp_path, rules=SMALL_PAGES), W.ENUMERATE, {"kind": "tables"})
    async with database.write() as session:
        cycle = await session.get(DivineWillCycleRow, world.cycle_id)
        assert cycle is not None
        cycle.status = CycleStatus.DONE
        for ordinal in (2, 3):
            session.add(
                DivineWillCycleRow(session_id=world.session_id, ordinal=ordinal, mode=DivineWillMode.ASK_LORE, epoch=3, status=CycleStatus.DONE, player_text="")
            )
        latest = DivineWillCycleRow(session_id=world.session_id, ordinal=4, mode=DivineWillMode.ASK_LORE, epoch=3, status=CycleStatus.RUNNING, player_text="")
        session.add(latest)
        await session.flush()
        world.cycle_id = latest.id
    remembered = replace(SMALL_PAGES, divine_will=replace(SMALL_PAGES.divine_will, remembered_cycles=3))
    forgotten = replace(SMALL_PAGES, divine_will=replace(SMALL_PAGES.divine_will, remembered_cycles=2))
    kept = await call_tool(will_call(database, world, DivineWillMode.ASK_LORE, tmp_path, rules=remembered), W.READ_MORE, {"handle": first.handle})
    assert not kept.is_error and head(kept)["page"] == 2
    lost = await call_tool(will_call(database, world, DivineWillMode.ASK_LORE, tmp_path, rules=forgotten), W.READ_MORE, {"handle": first.handle})
    assert lost.is_error and "beyond memory" in lost.text


async def test_a_destructive_act_waits_for_the_player_and_changes_nothing(database: Database, tmp_path: Path) -> None:
    world = await will_world(database)
    async with database.read() as session:
        bond = await session.scalar(select(BondRow).where(BondRow.source_node_id == world.realm.people_id).order_by(BondRow.id).limit(1))
        assert bond is not None
        bonds = int(await session.scalar(select(func.count()).select_from(BondRow)) or 0)
    call = will_call(database, world, DivineWillMode.COMMAND, tmp_path)
    result = await call_tool(call, W.PERFORM_ACTION, {"action_id": "record_row:delete", "input": {"table": "bonds", "key": {"id": bond.id}}})
    assert result.pause and not result.is_error, result.text
    async with database.read() as session:
        waiting = list(await session.scalars(select(DivineWillConfirmationRow)))
        assert int(await session.scalar(select(func.count()).select_from(BondRow)) or 0) == bonds
    assert len(waiting) == 1 and waiting[0].status is ConfirmationStatus.PENDING
    assert waiting[0].reason is ConfirmationReason.DESTRUCTIVE and waiting[0].cycle_id == world.cycle_id
    assert result.payload["confirmation_id"] == waiting[0].id


async def test_an_act_at_the_costly_threshold_asks_first(database: Database, tmp_path: Path) -> None:
    world = await will_world(database)
    eager = replace(Rules(), divine_will=replace(Rules().divine_will, costly_essence=0))
    result = await call_tool(
        will_call(database, world, DivineWillMode.COMMAND, tmp_path, rules=eager), W.PERFORM_ACTION, {"action_id": "creator:mood", "input": {"anger": 90}}
    )
    assert result.pause and result.payload["reason"] == ConfirmationReason.COSTLY.value
    async with database.read() as session:
        creator = await session.scalar(select(CreatorRow))
    assert creator is not None and creator.mood_anger != 90


async def test_an_act_made_while_the_world_lives_an_epoch_waits_in_the_queue(database: Database, tmp_path: Path) -> None:
    world = await will_world(database)
    release = asyncio.Event()

    async def epoch(_context: JobContext) -> dict[str, Any]:
        await release.wait()
        return {}

    jobs = JobManager(database, EventBus())
    await jobs.submit(JobKind.EPOCH, epoch, exclusive_group=WORLD_GROUP)
    try:
        call = will_call(database, world, DivineWillMode.COMMAND, tmp_path, player=harness_player(database, tmp_path, jobs))
        result = await call_tool(call, W.PERFORM_ACTION, {"action_id": "creator:mood", "input": {"anger": 90}})
        assert not result.is_error and "waits in the queue" in result.text
        assert result.payload["ledger_entry_id"] is None
        async with database.read() as session:
            queued = list(await session.scalars(select(QueuedActRow)))
            creator = await session.scalar(select(CreatorRow))
        assert [(row.action_id, row.status) for row in queued] == [("creator:mood", QueuedActStatus.QUEUED)]
        assert creator is not None and creator.mood_anger != 90
    finally:
        release.set()
        await jobs.shutdown()
    async with database.read() as session:
        creator = await session.scalar(select(CreatorRow))
    assert creator is not None and creator.mood_anger != 90


async def test_an_unfit_input_names_the_problem(database: Database, tmp_path: Path) -> None:
    world = await will_world(database)
    call = will_call(database, world, DivineWillMode.COMMAND, tmp_path)
    result = await call_tool(call, W.PERFORM_ACTION, {"action_id": "creator:mood", "input": {"wrath": 4}})
    assert result.is_error and "describe_action" in result.text
    result = await call_tool(call, W.PERFORM_ACTION, {"action_id": "creator:moo", "input": {}})
    assert result.is_error and "creator:mood" in result.text


def test_an_unknown_kind_names_the_tables_that_hold_the_word() -> None:
    text = unknown_kind("war").text
    assert "Tables whose names hold this word" in text and "wars" in text.split("Use an entity type")[0]


async def test_enumerate_sorts_and_filters_by_a_things_stats(database: Database, tmp_path: Path) -> None:
    world = await will_world(database)
    async with database.write() as session:
        for number, people in enumerate((300, 9000, 1200)):
            town = await make_entity(session, f"Town {number}", EntityType.SETTLEMENT, world_id=world.realm.cosmos.world_id)
            set_stats(town, population=people)
    call = will_call(database, world, DivineWillMode.ASK_LORE, tmp_path)
    result = await call_tool(call, W.ENUMERATE, {"kind": "settlement", "sort": ["-population"], "contains": "Town"})
    lines = listed([result])
    assert [line.split("name: ", 1)[1].split(" · ", 1)[0] for line in lines][:3] == ["Town 1", "Town 2", "Town 0"]
    chosen = await call_tool(call, W.ENUMERATE, {"kind": "settlement", "filters": {"population": 1200}})
    assert "Town 2" in chosen.text and "Town 1" not in chosen.text


async def test_read_node_reads_every_change_of_its_records_page_by_page(database: Database, tmp_path: Path) -> None:
    world = await will_world(database)
    people = world.realm.people_id
    async with database.write() as session:
        line = ChronicleRow(epoch=2, year=70, kind=ChronicleKind.WORLD, world_id=world.realm.cosmos.world_id, text="The Kessar Folk held a great fair.")
        session.add(line)
        await session.flush()
        fair = IncidentRow(kind="player.history", epoch=2, year=70, world_id=world.realm.cosmos.world_id, chronicle_id=line.id, magnitude=5, locked=[])
        session.add(fair)
        await session.flush()
        for step in range(60):
            session.add(
                StateChangeRow(
                    epoch=2,
                    year=70,
                    table_name="entities",
                    row_key=f'{{"id": {people}}}',
                    node_id=people,
                    operation=LedgerOperation.UPDATE,
                    field="power_level",
                    before_number=float(step),
                    after_number=float(step + 1),
                    actor_kind=ActorKind.ENGINE,
                    incident_id=fair.id,
                )
            )
    call = will_call(database, world, DivineWillMode.ASK_LORE, tmp_path, rules=SMALL_PAGES)
    pages = await every_page(call, W.READ_NODE, {"node_id": people, "part": "changes"})
    told = [line for line in listed(pages) if "power level of entities of Kessar Folk" in line]
    assert len(pages) > 1
    assert [line.split(": ", 2)[2].split(" by ", 1)[0] for line in told] == [f"{step} → {step + 1}" for step in range(60)]
    assert all("during: The Kessar Folk held a great fair." in line for line in told)
