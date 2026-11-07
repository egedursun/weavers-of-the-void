import pytest

from aerona.agents.tool_ports import AgentReadViews
from aerona.db.session import Database
from aerona.tools.framework.ports import BornChild, BornWorld, ToolPorts, WorldBirthOrder
from aerona.tools.mortal.registry import mortal_specs
from aerona.tools.son.registry import son_specs
from tests.tools.every_mortal_tool import MORTAL_CASES
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


def test_every_son_tool_has_a_working_case() -> None:
    assert sorted(SON_CASES) == sorted(SON_SPECS)


def test_every_mortal_tool_has_a_working_case() -> None:
    assert sorted(MORTAL_CASES) == sorted(MORTAL_SPECS)


@pytest.mark.parametrize("name", sorted(SON_CASES))
async def test_son_tool_runs(database: Database, name: str) -> None:
    case = SON_CASES[name]
    realm, ids = await staged(database, case)
    actor = case.actor(realm, ids) if case.actor is not None else realm.son_id
    toolkit = await son_toolkit(database, actor, action_points=case.action_points, ports=PORTS)
    assert name in toolkit.catalogue.names, f"{name} is not offered to the son"
    outcome = await toolkit.runtime.call(name, complete(SON_SPECS[name].input_model, case.arguments(realm, ids)))
    assert not outcome.is_error, outcome.text


@pytest.mark.parametrize("name", sorted(MORTAL_CASES))
async def test_mortal_tool_runs(database: Database, name: str) -> None:
    case = MORTAL_CASES[name]
    realm, ids = await staged(database, case)
    actor = case.actor(realm, ids) if case.actor is not None else realm.mortal_id
    toolkit = await mortal_toolkit(database, actor, action_points=case.action_points, ports=PORTS)
    assert name in toolkit.catalogue.names, f"{name} is not offered to this actor"
    outcome = await toolkit.runtime.call(name, complete(MORTAL_SPECS[name].input_model, case.arguments(realm, ids)))
    assert not outcome.is_error, outcome.text
