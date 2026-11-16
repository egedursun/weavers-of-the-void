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


GENERATED = """
export const processKindValues: ReadonlyArray<
  FlattenedDeepRequired<components>['schemas']['ProcessKind']
> = [
  'farming',
  'fishing',
  "mining",
]
"""

BULK = """
export const PROCESSES: Record<string, Named> = {
  farming: { label: 'Farming', icon: Wheat, tone: 'success' },
  fishing: { label: 'Fishing', icon: Fish, tone: 'info' },
  logging: { label: 'Logging', icon: Trees, tone: 'success' },
  mining: { label: 'Mining', icon: Pickaxe, tone: 'muted' },
  milking: { label: 'Milking', icon: Milk, tone: 'info' },
}
"""


DECLARED = """
export const SOME: Record<Exclude<Schemas['ProcessKind'], 'milking'>, Named> = {
  farming: { label: 'Farming', icon: Wheat, tone: 'success' },
  fishing: { label: 'Fishing', icon: Fish, tone: 'info' },
  logging: { label: 'Logging', icon: Trees, tone: 'success' },
  mining: { label: 'Mining', icon: Pickaxe, tone: 'muted' },
}
"""


def test_a_map_that_declares_what_it_leaves_out_is_not_a_gap(tmp_path: Path) -> None:
    module = checker()
    enums = {"processKind": frozenset({"farming", "fishing", "logging", "mining", "milking"})}
    declared = tmp_path / "declared.ts"
    declared.write_text(DECLARED, encoding="utf-8")
    assert module.gaps_in(declared, enums) == []


SHORTHAND = """
const MAKERS: Record<ProcessKind, Maker> = {
  farming: farm,
  fishing,
  logging,
  mining: mine,
  milking,
}
"""


def test_shorthand_keys_count_as_labelled(tmp_path: Path) -> None:
    module = checker()
    enums = {"processKind": frozenset({"farming", "fishing", "logging", "mining", "milking"})}
    shorthand = tmp_path / "shorthand.ts"
    shorthand.write_text(SHORTHAND, encoding="utf-8")
    assert module.gaps_in(shorthand, enums) == []


def test_enum_values_read_from_generated_types_carry_no_quotes() -> None:
    module = checker()
    assert module.enum_values(GENERATED) == {"processKind": frozenset({"farming", "fishing", "mining"})}


def test_a_map_left_behind_when_many_values_arrive_at_once_is_still_caught(tmp_path: Path) -> None:
    module = checker()
    enums = {"processKind": frozenset({"farming", "fishing", "logging", "mining", "milking", "brewing", "salting"})}
    bulk = tmp_path / "bulk.ts"
    bulk.write_text(BULK, encoding="utf-8")
    assert [(gap.name, gap.missing) for gap in module.gaps_in(bulk, enums)] == [("PROCESSES", ("brewing", "salting"))]


def test_no_frontend_label_map_leaves_out_a_value_of_its_enum() -> None:
    module = checker()
    enums = module.enum_values(module.SCHEMA.read_text(encoding="utf-8"))
    paths = [path for path in sorted(module.FRONTEND.rglob("*.ts*")) if "generated" not in path.parts and ".test." not in path.name]
    assert [gap for path in paths for gap in module.gaps_in(path, enums)] == []


SIGN_PICKER = """
type SignKind = components['schemas']['CreatorSignKind']

const SIGNS: {
  key: SignKind
  label: string
}[] = [
  { key: 'wrath', label: 'Wrath' },
  { key: 'grace', label: 'Grace' },
]
"""


def test_an_option_list_typed_over_an_enum_must_offer_every_value(tmp_path: Path) -> None:
    module = checker()
    enums = {"CreatorSignKind": frozenset({"wrath", "grace", "omen", "warning"})}
    picker = tmp_path / "GodPanel.tsx"
    picker.write_text(SIGN_PICKER, encoding="utf-8")
    gaps = module.option_gaps_in(picker, enums)
    assert [(gap.name, gap.missing) for gap in gaps] == [("SIGNS", ("omen", "warning"))]
    full = tmp_path / "Full.tsx"
    full.write_text(SIGN_PICKER.replace("]\n", "  { key: 'omen', label: 'Omen' },\n  { key: 'warning', label: 'Warning' },\n]\n"), encoding="utf-8")
    assert module.option_gaps_in(full, enums) == []
