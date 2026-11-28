from pathlib import Path

import pytest
from sqlalchemy import func, select

from aerona.agents.tool_ports import AgentReadViews
from aerona.db.session import Database
from aerona.db.tables.changes import StateChangeRow
from aerona.db.tables.mind import PressureRow
from aerona.domain.enums.mind import PressureKind
from aerona.domain.enums.node import ActorKind
from aerona.prompts.tools.divine_will_ids import DivineWillToolId
from aerona.tools.divine_will.catalogue import tool_by_name
from aerona.tools.divine_will.framework import MODE_TOOLSETS
from aerona.tools.framework.ports import BornChild, BornWorld, ToolPorts, WorldBirthOrder
from aerona.tools.mortal.registry import mortal_specs
from aerona.tools.son.registry import son_specs
from tests.tools.every_divine_will_tool import WILL_CASES, run_will_case
from tests.tools.every_mortal_tool import COMMUNITY_CASES, MORTAL_CASES
from tests.tools.every_son_tool import SON_CASES
from tests.tools.every_tool import Case, complete
from tests.tools.factories import Realm, mortal_toolkit, seed_realm, son_toolkit

SON_SPECS = {spec.name: spec for spec in son_specs()}
MORTAL_SPECS = {spec.name: spec for spec in mortal_specs()}


class ChildBirth:
    async def birth_child(self, parent_son_id: int, inspiration: str, co_parent_son_id: int | None) -> BornChild:
        return BornChild(son_id=parent_son_id, name="Lumen", title="of the Roads", rarity_label="Rare")


class WorldBirth:
    async def birth_world(self, order: WorldBirthOrder) -> BornWorld:
        return BornWorld(world_id=order.parent_world_id or 1, name="Valen", type_label="Terrestrial")


PORTS = ToolPorts(views=AgentReadViews(), child_birth=ChildBirth(), world_birth=WorldBirth())


async def staged(database: Database, case: Case) -> tuple[Realm, dict[str, int]]:
    realm = await seed_realm(database)
    async with database.write() as session:
        ids = await case.setup(session, realm)
    for step in case.prelude:
        if step.actor is None:
            toolkit = await son_toolkit(database, realm.son_id, action_points=case.action_points, ports=PORTS)
            arguments = complete(SON_SPECS[step.tool].input_model, step.arguments(realm, ids))
        else:
            toolkit = await mortal_toolkit(database, step.actor(realm, ids), action_points=case.action_points, ports=PORTS)
            arguments = complete(MORTAL_SPECS[step.tool].input_model, step.arguments(realm, ids))
        outcome = await toolkit.runtime.call(step.tool, arguments)
        assert not outcome.is_error, f"prelude {step.tool}: {outcome.text}"
        async with database.write() as session:
            ids = await case.lookup(session, realm, ids)
    return realm, ids


async def last_change(database: Database) -> int:
    async with database.read() as session:
        return int(await session.scalar(select(func.coalesce(func.max(StateChangeRow.id), 0))) or 0)


async def unowned_changes(database: Database, mark: int) -> list[str]:
    async with database.read() as session:
        rows = await session.execute(
            select(StateChangeRow.table_name, StateChangeRow.field).where(
                StateChangeRow.id > mark, (StateChangeRow.actor_kind == ActorKind.SYSTEM) | (StateChangeRow.epoch == 0)
            )
        )
    return sorted({f"{table}.{field}" for table, field in rows})


async def undated_changes(database: Database, mark: int) -> list[str]:
    async with database.read() as session:
        rows = await session.execute(select(StateChangeRow.table_name, StateChangeRow.field).where(StateChangeRow.id > mark, StateChangeRow.year.is_(None)))
    return sorted({f"{table}.{field}" for table, field in rows})


def test_every_son_tool_has_a_working_case() -> None:
    assert sorted(SON_CASES) == sorted(SON_SPECS)


def test_every_mortal_tool_has_a_working_case() -> None:
    assert sorted(MORTAL_CASES) == sorted(MORTAL_SPECS)


def test_every_divine_will_tool_has_a_working_case() -> None:
    assert sorted(WILL_CASES) == sorted(DivineWillToolId)


@pytest.mark.parametrize("tool", sorted(WILL_CASES))
async def test_divine_will_tool_runs(database: Database, tmp_path: Path, tool: DivineWillToolId) -> None:
    case = WILL_CASES[tool]
    found = tool_by_name(tool.value)
    assert found is not None and found.toolsets & MODE_TOOLSETS[case.mode], f"{tool} is not offered in {case.mode} mode"
    result = await run_will_case(database, tool, case, tmp_path)
    assert not result.is_error, result.text
    assert result.pause is case.pause, result.text
    missing = [text for text in case.expect if text not in result.text]
    assert not missing, f"{tool} result lacks {missing}: {result.text}"


@pytest.mark.parametrize("name", sorted(SON_CASES))
async def test_son_tool_runs(database: Database, name: str) -> None:
    case = SON_CASES[name]
    realm, ids = await staged(database, case)
    actor = case.actor(realm, ids) if case.actor is not None else realm.son_id
    toolkit = await son_toolkit(database, actor, action_points=case.action_points, ports=PORTS)
    assert name in toolkit.catalogue.names, f"{name} is not offered to the son"
    mark = await last_change(database)
    outcome = await toolkit.runtime.call(name, complete(SON_SPECS[name].input_model, case.arguments(realm, ids)))
    assert not outcome.is_error, outcome.text
    assert await unowned_changes(database, mark) == []
    assert await undated_changes(database, mark) == []


@pytest.mark.parametrize("name", sorted(MORTAL_CASES))
async def test_mortal_tool_runs(database: Database, name: str) -> None:
    case = MORTAL_CASES[name]
    realm, ids = await staged(database, case)
    actor = case.actor(realm, ids) if case.actor is not None else realm.mortal_id
    toolkit = await mortal_toolkit(database, actor, action_points=case.action_points, ports=PORTS)
    assert name in toolkit.catalogue.names, f"{name} is not offered to this actor"
    mark = await last_change(database)
    outcome = await toolkit.runtime.call(name, complete(MORTAL_SPECS[name].input_model, case.arguments(realm, ids)))
    assert not outcome.is_error, outcome.text
    assert await unowned_changes(database, mark) == []
    assert await undated_changes(database, mark) == []


@pytest.mark.parametrize("label", sorted(COMMUNITY_CASES))
async def test_a_community_runs_the_tools_it_is_offered(database: Database, label: str) -> None:
    case = COMMUNITY_CASES[label]
    name = label.split(" ", 1)[0]
    realm, ids = await staged(database, case)
    assert case.actor is not None
    toolkit = await mortal_toolkit(database, case.actor(realm, ids), action_points=case.action_points, ports=PORTS)
    assert name in toolkit.catalogue.names, f"{name} is not offered to this community"
    outcome = await toolkit.runtime.call(name, complete(MORTAL_SPECS[name].input_model, case.arguments(realm, ids)))
    assert not outcome.is_error, outcome.text


async def test_a_pressure_that_is_not_felt_is_refused_with_what_is(database: Database) -> None:
    realm = await seed_realm(database)
    async with database.write() as session:
        session.add(PressureRow(entity_id=realm.mortal_id, pressure=PressureKind.HUNGER, value=40))
    toolkit = await mortal_toolkit(database, realm.mortal_id, action_points=4, ports=PORTS)
    outcome = await toolkit.runtime.call("ease_pressure", complete(MORTAL_SPECS["ease_pressure"].input_model, {"pressure": PressureKind.POVERTY.value}))
    assert outcome.is_error and "what weighs on you: hunger 40" in outcome.text
