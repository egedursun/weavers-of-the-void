import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

RAW = """
async def honour(ctx, unit):
    named = await ctx.session.scalar(select(NamedUnitRow).where(NamedUnitRow.unit_id == unit.id))
    if named is not None and held(named.id):
        return
    for grant in await ctx.session.scalars(select(VeteranGrantRow)):
        if held(grant.id):
            continue
    hoards = unheld(await ctx.session.scalars(select(HoardRow)))


def guarded(row: SavingRow) -> bool:
    return held(row.id)


async def nodes(ctx, case):
    folk = [row for row in await ctx.session.scalars(select(EntityRow)) if not held(row.id)]
    row = CaseWitnessRow(case_id=case.id)
    return folk, row, held(case.settlement_entity_id)
"""


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_held_ids", REPOSITORY_ROOT / "scripts" / "check_held_ids.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_held_ids"] = module
    spec.loader.exec_module(module)
    return module


def test_a_hold_check_on_the_id_of_a_row_that_is_no_node_is_flagged() -> None:
    found = checker().misheld({Path("module.py"): RAW})
    assert [(item.line, item.table) for item in found] == [(4, "NamedUnitRow"), (7, "VeteranGrantRow"), (9, "HoardRow"), (13, "SavingRow")]


def test_the_backend_asks_the_hold_guard_only_about_nodes() -> None:
    module = checker()
    assert module.misheld({path: path.read_text(encoding="utf-8") for path in sorted(module.SOURCE.rglob("*.py"))}) == []
