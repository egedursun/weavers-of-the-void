from pathlib import Path

from aerona.db.base import Base
from aerona.engine.interconnect.catalog import REGISTERED
from aerona.engine.pipeline import PHASE_REGISTRY
from aerona.services.player.catalog import ACTIONS_BY_ID

ROOT = Path(__file__).resolve().parents[3]
MATRIX = ROOT / "docs" / "spec" / "13-coverage.md"
FRONTEND = ROOT / "frontend" / "src"
GENERIC_LEVERS = ("lever:pin", "lever:unpin", "lever:suppress", "lever:unsuppress", "lever:run", "modifier:add", "modifier:remove")


def matrix_ids() -> set[str]:
    return {line.split("|")[1].strip() for line in MATRIX.read_text(encoding="utf-8").splitlines() if line.startswith("| ") and not line.startswith("| ID ")}


def frontend_source() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in FRONTEND.rglob("*.tsx") if path.is_file() and "generated" not in path.parts)


def test_generic_levers_exist_for_every_mechanic() -> None:
    assert [action for action in GENERIC_LEVERS if action not in ACTIONS_BY_ID] == []


def test_every_registered_mechanic_is_traceable_and_complete() -> None:
    ids = matrix_ids()
    source = frontend_source()
    tables = set(Base.metadata.tables)
    problems: list[str] = []
    for key, mechanic in REGISTERED.items():
        if mechanic.spec_item not in ids:
            problems.append(f"{key}: spec item {mechanic.spec_item} is not in the coverage matrix")
        problems.extend(f"{key}: unknown phase {phase}" for phase in mechanic.phases if phase not in PHASE_REGISTRY)
        if not mechanic.surface.keys:
            problems.append(f"{key}: no UI surface")
        problems.extend(f"{key}: UI surface {surface} is not rendered by the frontend" for surface in mechanic.surface.keys if surface not in source)
        if not mechanic.backfill.strip():
            problems.append(f"{key}: no backfill rule")
        problems.extend(f"{key}: unknown table {table}" for table in mechanic.tables if table not in tables)
    assert problems == []


def test_every_engine_step_is_claimed_by_a_registered_mechanic() -> None:
    claimed = {phase for mechanic in REGISTERED.values() for phase in mechanic.phases}
    assert [name for name in PHASE_REGISTRY if name not in claimed] == []
