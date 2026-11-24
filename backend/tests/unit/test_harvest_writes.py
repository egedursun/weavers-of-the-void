import ast
from pathlib import Path

from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.engine.environment.harvest_harm import HARVEST_CEILING, harm_harvest, shift_harvest
from aerona.rules.model import EPOCH_YEARS

SOURCE = Path(__file__).resolve().parents[2] / "src" / "aerona"
WRITERS = frozenset({Path("engine/environment/harvest_harm.py"), Path("engine/phases/environment.py")})


def harvest_writes(text: str) -> list[int]:
    found: list[int] = []
    for node in ast.walk(ast.parse(text)):
        targets = node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, (ast.AugAssign, ast.AnnAssign)) else []
        found.extend(node.lineno for target in targets if isinstance(target, ast.Attribute) and target.attr == "harvest_pct")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "setattr" and len(node.args) > 1:
            name = node.args[1]
            if isinstance(name, ast.Constant) and name.value == "harvest_pct":
                found.append(node.lineno)
    return found


def land(harvest: int, *, locked: list[str] | None = None) -> RegionEnvironmentRow:
    return RegionEnvironmentRow(entity_id=10**9, harvest_pct=harvest, locked=locked or [])


def test_only_the_harvest_roll_and_its_helpers_write_a_lands_harvest() -> None:
    offenders = [
        f"{path.relative_to(SOURCE)}:{line}"
        for path in sorted(SOURCE.rglob("*.py"))
        if path.relative_to(SOURCE) not in WRITERS
        for line in harvest_writes(path.read_text())
    ]
    assert offenders == []


def test_a_season_of_foraging_costs_the_epoch_one_years_share_and_keeps_a_rich_harvest() -> None:
    ground = land(171)
    lost = harm_harvest(ground, 25)
    assert lost == round(171 * 0.25 / EPOCH_YEARS)
    assert ground.harvest_pct > 160


def test_a_whole_years_loss_costs_a_fiftieth_and_never_falls_below_nothing() -> None:
    ground = land(100)
    assert harm_harvest(ground, 100) == 100 // EPOCH_YEARS
    bare = land(0)
    assert harm_harvest(bare, 100) == 0 and bare.harvest_pct == 0


def test_shifts_keep_the_harvest_inside_its_range_and_spare_a_locked_land() -> None:
    ground = land(190)
    assert shift_harvest(ground, 40) == HARVEST_CEILING - 190
    assert shift_harvest(ground, -500) == -HARVEST_CEILING and ground.harvest_pct == 0
    locked = land(120, locked=["harvest_pct"])
    assert harm_harvest(locked, 100) == 0 and shift_harvest(locked, -50) == 0 and locked.harvest_pct == 120
