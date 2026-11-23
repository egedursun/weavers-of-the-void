import ast
import inspect
import textwrap
from collections.abc import Callable
from types import ModuleType
from typing import Any

from aerona.db.session import Database
from aerona.domain.enums.modifier import ModifierOp, ModifierSource
from aerona.engine.interconnect.registry import suppression_key
from aerona.engine.interconnect.tool_holds import tool_mechanics
from aerona.engine.primitives.modifiers import ModifierDraft, add_modifier
from aerona.tools.mortal.registry import mortal_specs
from aerona.tools.son.registry import son_specs
from tests.tools.factories import EPOCH, seed_realm, son_toolkit
from tests.tools.test_son_tools import ok, rejected

HOLD_CALLS = frozenset({"held", "unheld", "free_rows"})


def called_names(function: Callable[..., Any]) -> set[str]:
    tree = ast.parse(textwrap.dedent(inspect.getsource(function)))
    return {node.func.id for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}


def reaches_hold(function: Callable[..., Any], module: ModuleType | None, seen: set[Callable[..., Any]]) -> bool:
    if function in seen:
        return False
    seen.add(function)
    names = called_names(function)
    if names & HOLD_CALLS:
        return True
    helpers = [getattr(module, name, None) for name in sorted(names)]
    return any(inspect.isfunction(helper) and inspect.getmodule(helper) is module and reaches_hold(helper, module, seen) for helper in helpers)


def test_every_tool_that_honours_a_hold_belongs_to_a_mechanic_the_god_can_hold() -> None:
    specs = [*mortal_specs(), *son_specs()]
    honouring = [spec.name for spec in specs if reaches_hold(spec.handler, inspect.getmodule(spec.handler), set())]
    assert honouring
    assert [name for name in honouring if not tool_mechanics(name)] == []


async def test_a_son_cannot_mark_the_birth_of_a_mortal_the_god_holds_against_birth_signs(database: Database) -> None:
    realm = await seed_realm(database)
    toolkit = await son_toolkit(database, realm.son_id, action_points=6)
    arguments = {"mortal_id": realm.mortal_id, "dreaded": False, "reason": "to see what the sky says of this child"}
    await ok(toolkit, "mark_birth", arguments)
    assert "astrology" in tool_mechanics("mark_birth")
    async with database.write() as session:
        draft = ModifierDraft(
            realm.mortal_id, suppression_key("astrology"), ModifierOp.ADD, 0, ModifierSource.SUPPRESSION, "player.suppression", start_epoch=EPOCH
        )
        await add_modifier(session, draft)
    text = await rejected(toolkit, "mark_birth", arguments)
    assert "it is held" in text
