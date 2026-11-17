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


def apply[Row](row: Row, values: dict[str, object]) -> Row:
    for key, value in values.items():
        setattr(row, key, value)
    return row


async def edit_thing(ctx, thing_id: int, values: dict[str, object]) -> ThingRow:
    return apply(await found(ctx, ThingRow, thing_id), values)
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


def test_a_row_handed_to_a_generic_editor_is_known_as_edited() -> None:
    control = checker()
    code = control.Code({"aerona.db.tables.things": ast.parse(TABLES), "aerona.engine.things": ast.parse(LEVERS)})
    node = code.defs[("aerona.engine.things", "edit_thing")][0]
    assert code.verbs("aerona.engine.things", node)["edit"] == {"things"}


PART_LEVERS = """
from aerona.db.tables.things import ThingRow

PARTS = {"thing": ThingRow}


async def thing_part_edit(ctx, part: str, part_id: int, values: dict[str, object]) -> None:
    await edit_part(ctx, PARTS, part, part_id, values)


async def thing_part_delete(ctx, part: str, part_id: int) -> None:
    await delete_part(ctx, PARTS, part, part_id)
"""


def test_a_part_lever_handed_a_table_of_row_classes_edits_and_deletes_those_tables() -> None:
    control = checker()
    code = control.Code({"aerona.db.tables.things": ast.parse(TABLES), "aerona.services.things": ast.parse(PART_LEVERS)})
    edit = code.defs[("aerona.services.things", "thing_part_edit")][0]
    delete = code.defs[("aerona.services.things", "thing_part_delete")][0]
    assert code.verbs("aerona.services.things", edit)["edit"] == {"things"}
    assert code.verbs("aerona.services.things", delete)["delete"] == {"things"}
