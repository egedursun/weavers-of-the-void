import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

GENERIC = """
export function Form() {
  return (
    <>
      <MindPicker label='Kind' value={kind} table={KINDS} />
      <Label as='label' htmlFor='name'>
        Name
      </Label>
    </>
  )
}
"""

NAMED = """
export function Form() {
  return (
    <>
      <MindPicker label='Kind of history' value={kind} table={KINDS} />
      <Label as='label' htmlFor='name'>
        History name
      </Label>
    </>
  )
}
"""


def script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_shared_labels", REPOSITORY_ROOT / "scripts" / "check_shared_labels.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_shared_labels"] = module
    spec.loader.exec_module(module)
    return module


def test_a_generic_field_label_is_found(tmp_path: Path) -> None:
    check = script()
    view = tmp_path / "Form.tsx"
    view.write_text(GENERIC, encoding="utf-8")
    assert sorted(item.label for item in check.generics_in(view)) == ["Kind", "Name"]


def test_a_named_field_label_passes(tmp_path: Path) -> None:
    check = script()
    view = tmp_path / "Form.tsx"
    view.write_text(NAMED, encoding="utf-8")
    assert check.generics_in(view) == []


def test_the_sections_every_drawer_renders_name_their_fields() -> None:
    check = script()
    shared = check.shared_files()
    assert any(path.name == "DominionSection.tsx" for path in shared)
    assert [item for path in shared for item in check.generics_in(path)] == []
