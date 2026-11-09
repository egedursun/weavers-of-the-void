import ast
import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

TABLES = """
class ThingRow(Base):
    __tablename__ = "things"
    id: Mapped[int] = mapped_column(primary_key=True)
"""

LEVERS = """
from aerona.db.tables.things import ThingRow


async def found[Row](ctx, kind: type[Row], key: object) -> Row:
    return await ctx.session.get(kind, key)


async def remove_thing(ctx, thing_id: int) -> None:
    row = await found(ctx, ThingRow, thing_id)
    await ctx.session.delete(row)
"""


def checker() -> ModuleType:
    scripts = str(REPOSITORY_ROOT / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    spec = importlib.util.spec_from_file_location("check_control", REPOSITORY_ROOT / "scripts" / "check_control.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_control"] = module
    spec.loader.exec_module(module)
    return module


def test_a_row_fetched_through_a_generic_finder_is_known_by_the_class_it_was_given() -> None:
    control = checker()
    code = control.Code({"aerona.db.tables.things": ast.parse(TABLES), "aerona.engine.things": ast.parse(LEVERS)})
    node = code.defs[("aerona.engine.things", "remove_thing")][0]
    assert code.verbs("aerona.engine.things", node)["delete"] == {"things"}
