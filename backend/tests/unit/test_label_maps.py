import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

SHORT = """
export const PROCESSES: Record<string, Named> = {
  farming: { label: 'Farming', icon: Wheat, tone: 'success' },
  fishing: { label: 'Fishing', icon: Fish, tone: 'info' },
  logging: { label: 'Logging', icon: Trees, tone: 'success' },
  mining: { label: 'Mining', icon: Pickaxe, tone: 'muted' },
}
"""

SUBSET = """
export const WAR_GOODS: Record<string, Named> = {
  farming: { label: 'Farming', icon: Wheat, tone: 'success' },
  fishing: { label: 'Fishing', icon: Fish, tone: 'info' },
  logging: { label: 'Logging', icon: Trees, tone: 'success' },
}
"""


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_label_maps", REPOSITORY_ROOT / "scripts" / "check_label_maps.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_label_maps"] = module
    spec.loader.exec_module(module)
    return module


def test_a_map_that_labels_nearly_every_value_of_an_enum_must_label_them_all(tmp_path: Path) -> None:
    module = checker()
    enums = {"processKind": frozenset({"farming", "fishing", "logging", "mining", "milking"})}
    short = tmp_path / "labels.ts"
    short.write_text(SHORT, encoding="utf-8")
    subset = tmp_path / "war.ts"
    subset.write_text(SUBSET, encoding="utf-8")
    assert [(gap.name, gap.missing) for gap in module.gaps_in(short, enums)] == [("PROCESSES", ("milking",))]
    assert module.gaps_in(subset, enums) == []


def test_no_frontend_label_map_leaves_out_a_value_of_its_enum() -> None:
    module = checker()
    enums = module.enum_values(module.SCHEMA.read_text(encoding="utf-8"))
    paths = [path for path in sorted(module.FRONTEND.rglob("*.ts*")) if "generated" not in path.parts and ".test." not in path.name]
    assert [gap for path in paths for gap in module.gaps_in(path, enums)] == []
