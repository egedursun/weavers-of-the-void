import asyncio
from typing import Any

import pytest
from sqlalchemy import select

from aerona.db.session import Database
from aerona.db.tables.agency import AgentTurnRow
from aerona.db.tables.ledger import LedgerChangeRow, LedgerEntryRow
from aerona.db.tables.sons import SonRow
from aerona.db.tables.warfare import CaptiveRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.rarity import Rarity
from aerona.domain.enums.son import SonStatus
from aerona.domain.enums.war import CaptiveStatus
from aerona.domain.enums.world import LoreLanguage
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult
from aerona.rules.registry import Rules
from aerona.tools.framework.actors import SonToolRuntime
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import EmptyInput, clean_identity, match_choice
from aerona.tools.framework.ports import BornChild, ToolPorts
from aerona.tools.framework.runtime import RuntimeSettings
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.turn import start_turn
from aerona.tools.framework.validation import fail
from aerona.tools.son.kin import CallSiblingInput, SpokenIntent
from tests.tools.factories import EPOCH, SEED, count_rows, mortal_toolkit, seed_realm, son_toolkit


async def son_row(database: Database, son_id: int) -> SonRow:
    async with database.read() as session:
        son = await session.get(SonRow, son_id)
        assert son is not None
        return son


async def action_points(database: Database, node_id: int) -> int | None:
    async with database.read() as session:
        row = await session.get(AgentTurnRow, node_id)
        return row.action_points_left if row is not None else None


def test_identity_and_choice_sanitation() -> None:
    assert clean_identity("#12", optional=False) == 12
    assert clean_identity("son#3", optional=False) == 3
    assert clean_identity(" id 7 ", optional=False) == 7
    assert clean_identity(0, optional=False) == 0
    assert match_choice("Friend", [item.value for item in SpokenIntent]) == "friendship"
    assert match_choice("THREAT", [item.value for item in SpokenIntent]) == "threat"
    parsed = CallSiblingInput.model_validate({"son_id": "#4", "intent": "Mock", "message": "you are small"})
    assert parsed.son_id == 4
    assert parsed.intent is SpokenIntent.MOCKERY


async def test_validation_errors_name_the_field(database: Database) -> None:
    realm = await seed_realm(database)
    toolkit = await son_toolkit(database, realm.son_id)
    outcome = await toolkit.runtime.call("call_sibling", {"son_id": "nobody", "intent": "love", "message": "hello sibling"})
    assert outcome.is_error
    assert outcome.text.startswith("REJECTED: son_id")
    outcome = await toolkit.runtime.call("write_plan", {"plan": "short"})
    assert "plan is too short" in outcome.text


async def test_rarity_gates_hide_tools(database: Database) -> None:
    realm = await seed_realm(database, rarity=Rarity.COMMON)
    toolkit = await son_toolkit(database, realm.son_id)
    names = set(toolkit.catalogue.names)
    assert "create_place" in names
    assert "birth_world" not in names
    assert "transform" not in names
    outcome = await toolkit.runtime.call("transform", {})
    assert outcome.is_error
    assert "not available" in outcome.text
    tools = toolkit.tools()
    assert {tool.name for tool in tools} == names
    assert all(tool.description for tool in tools)


async def test_read_only_tools_do_not_write(database: Database) -> None:
    realm = await seed_realm(database)
    toolkit = await son_toolkit(database, realm.son_id)
    before = await action_points(database, realm.son_id)
    outcome = await toolkit.runtime.call("inspect_entity", {"id": realm.people_id})
    assert not outcome.is_error
    assert "Kessar Folk" in outcome.text
    outcome = await toolkit.runtime.call("search_entities", {"query": "Kessar"})
    assert "Kessar" in outcome.text
    assert await count_rows(database, LedgerEntryRow) == 0
    assert await action_points(database, realm.son_id) == before
    assert toolkit.done[0].read_only


def _runtime(database: Database, son_id: int, specs: list[ToolSpec[SonCall, Any]], ports: ToolPorts | None = None) -> SonToolRuntime:
    settings = RuntimeSettings(Rules(), EPOCH, SEED, LoreLanguage.ENGLISH, son_id)
    return SonToolRuntime(database, settings, specs, ports or ToolPorts())


@pytest.mark.tool_failure_expected
async def test_failure_refunds_essence_and_actions(database: Database) -> None:
    realm = await seed_realm(database)
    async with database.write() as session:
        await start_turn(session, realm.son_id, AgentKind.SON, EPOCH, 3)

    async def broken(call: SonCall, _args: EmptyInput) -> str:
        call.spend_essence(50)
        call.charge_actions(1)
        raise RuntimeError("the loom snapped")

    async def refused(call: SonCall, _args: EmptyInput) -> str:
        call.spend_essence(50)
        fail(SonResult.EXHAUSTED)

    meta = ToolMeta(ActionKind.OTHER, son_standard_action)
    runtime = _runtime(
        database,
        realm.son_id,
        [ToolSpec(SonToolId.REBEL, AgentKind.SON, EmptyInput, meta, broken), ToolSpec(SonToolId.WRITE_PLAN, AgentKind.SON, EmptyInput, meta, refused)],
    )
    essence = (await son_row(database, realm.son_id)).essence
    outcome = await runtime.call("rebel", {})
    assert outcome.is_error
    assert "the loom snapped" in outcome.text
    assert "refunded" in outcome.text
    outcome = await runtime.call("write_plan", {})
    assert outcome.text == "REJECTED: The resource is exhausted."
    assert (await son_row(database, realm.son_id)).essence == essence
    assert await action_points(database, realm.son_id) == 3
    assert await count_rows(database, LedgerEntryRow) == 0


async def test_calls_are_serialised(database: Database) -> None:
    realm = await seed_realm(database)
    async with database.write() as session:
        await start_turn(session, realm.son_id, AgentKind.SON, EPOCH, 5)
    running = 0
    peak = 0

    async def slow(call: SonCall, _args: EmptyInput) -> str:
        nonlocal running, peak
        running += 1
        peak = max(peak, running)
        await asyncio.sleep(0.01)
        running -= 1
        call.waive_actions()
        return "done"

    runtime = _runtime(
        database, realm.son_id, [ToolSpec(SonToolId.WRITE_PLAN, AgentKind.SON, EmptyInput, ToolMeta(ActionKind.OTHER, son_standard_action), slow)]
    )
    outcomes = await asyncio.gather(*[runtime.call("write_plan", {}) for _ in range(3)])
    assert all(not outcome.is_error for outcome in outcomes)
    assert peak == 1
    assert await count_rows(database, LedgerEntryRow) == 3


async def test_success_records_ledger_status_and_actions(database: Database) -> None:
    realm = await seed_realm(database)
    toolkit = await son_toolkit(database, realm.son_id, action_points=3)
    outcome = await toolkit.runtime.call("call_sibling", {"son_id": realm.sibling_id, "intent": "friendship", "message": "Peace to you, sister"})
    assert not outcome.is_error, outcome.text
    assert "Remaining actions: 3" in outcome.text
    async with database.read() as session:
        entry = await session.scalar(select(LedgerEntryRow))
        assert entry is not None
        assert entry.action_kind is ActionKind.SPEAK_TO_SIBLING
        assert entry.actor_node_id == realm.son_id
        changes = list(await session.scalars(select(LedgerChangeRow).where(LedgerChangeRow.entry_id == entry.id)))
        assert any(change.table_name == "messages" for change in changes)


async def test_asleep_son_is_gated(database: Database) -> None:
    realm = await seed_realm(database)
    toolkit = await son_toolkit(database, realm.son_id)
    async with database.write() as session:
        son = await session.get(SonRow, realm.son_id)
        assert son is not None
        son.status = SonStatus.ASLEEP
        son.sleep_epochs_left = 2
    outcome = await toolkit.runtime.call("call_sibling", {"son_id": realm.sibling_id, "intent": "love", "message": "do you hear me"})
    assert outcome.is_error
    assert "asleep" in outcome.text
    assert await action_points(database, realm.son_id) == 0


async def test_captive_mortal_may_only_escape(database: Database) -> None:
    realm = await seed_realm(database)
    async with database.write() as session:
        session.add(CaptiveRow(captive_entity_id=realm.mortal_id, captor_entity_id=realm.faction_id, status=CaptiveStatus.HELD, taken_epoch=1))
    toolkit = await mortal_toolkit(database, realm.mortal_id)
    outcome = await toolkit.runtime.call("adopt", {"child_id": realm.mortal_id, "reason": "a lonely captive"})
    assert outcome.is_error
    assert "holds you prisoner" in outcome.text


class FakeBirth:
    def __init__(self, fail_with: str | None = None) -> None:
        self.fail_with = fail_with

    async def birth_child(self, parent_son_id: int, inspiration: str, co_parent_son_id: int | None) -> BornChild:
        if self.fail_with:
            raise RuntimeError(self.fail_with)
        return BornChild(son_id=parent_son_id + 1000, name="Ashkin", title="the Young", rarity_label="Epic")


@pytest.mark.tool_failure_expected
async def test_long_job_success_and_refund(database: Database) -> None:
    realm = await seed_realm(database)
    toolkit = await son_toolkit(database, realm.son_id, action_points=4, ports=ToolPorts(child_birth=FakeBirth()))
    essence = (await son_row(database, realm.son_id)).essence
    outcome = await toolkit.runtime.call("birth_child", {"inspiration": "From the salt of my tears a child shall rise"})
    assert not outcome.is_error, outcome.text
    assert "Ashkin" in outcome.text
    rules = Rules()
    assert (await son_row(database, realm.son_id)).essence == essence - rules.costs.bear_child
    assert await action_points(database, realm.son_id) == 4 - rules.son_tools.bear_child_ap
    failing = await son_toolkit(database, realm.sibling_id, action_points=4, ports=ToolPorts(child_birth=FakeBirth("the womb of stars closed")))
    assert "birth_child" not in failing.catalogue.names
    async with database.write() as session:
        son = await session.get(SonRow, realm.son_id)
        assert son is not None
        son.essence = 300
    retry = await son_toolkit(database, realm.son_id, action_points=4, ports=ToolPorts(child_birth=FakeBirth("the womb of stars closed")))
    outcome = await retry.runtime.call("birth_child", {"inspiration": "Again, from the salt of my tears a child"})
    assert outcome.is_error
    assert "womb of stars closed" in outcome.text
    assert (await son_row(database, realm.son_id)).essence == 300
    await retry.settle_long_jobs()


async def test_sdk_tool_wraps_runtime(database: Database) -> None:
    realm = await seed_realm(database)
    toolkit = await son_toolkit(database, realm.son_id)
    tool = next(item for item in toolkit.tools() if item.name == "inspect_entity")
    assert isinstance(tool.input_schema, dict)
    assert tool.input_schema["properties"]["id"]["type"] == ["integer", "string"]
    reply = await tool.handler({"id": f"#{realm.people_id}"})
    assert reply["is_error"] is False
    assert "Kessar" in reply["content"][0]["text"]
    reply = await tool.handler({"id": 999999})
    assert reply["is_error"] is True
