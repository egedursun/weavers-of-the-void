import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

HIDDEN = """
export function Give() {
  return (
    <div>
      {data.kinds.length > 0 ? (
        <Button onClick={() => give.mutate(Number(kind))}>Give the pet</Button>
      ) : (
        <Muted>Their people keep no small tame kind.</Muted>
      )}
    </div>
  )
}
"""

KEPT = """
export function Give() {
  return (
    <div>
      {data.kinds.length === 0 && <Muted>Their people keep no small tame kind.</Muted>}
      <Button disabled={data.kinds.length === 0} onClick={() => give.mutate(Number(kind))}>Give the pet</Button>
      {data.pets.length === 0 ? (
        <EmptyState title='No companion yet' />
      ) : (
        <Paged items={data.pets}>{(row) => <Button onClick={() => free.mutate(row.id)}>Set it free</Button>}</Paged>
      )}
    </div>
  )
}
"""


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_hidden_controls", REPOSITORY_ROOT / "scripts" / "check_hidden_controls.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_hidden_controls"] = module
    spec.loader.exec_module(module)
    return module


def test_a_control_swapped_for_a_note_on_an_empty_list_is_found(tmp_path: Path) -> None:
    module = checker()
    hidden = tmp_path / "Hidden.tsx"
    hidden.write_text(HIDDEN, encoding="utf-8")
    kept = tmp_path / "Kept.tsx"
    kept.write_text(KEPT, encoding="utf-8")
    assert [item.condition for item in module.hidden_in(hidden)] == ["data.kinds.length > 0"]
    assert module.hidden_in(kept) == []


def test_no_screen_hides_a_god_control_behind_an_empty_list() -> None:
    module = checker()
    assert [item for path in sorted(module.FRONTEND.rglob("*.tsx")) if ".test." not in path.name for item in module.hidden_in(path)] == []
