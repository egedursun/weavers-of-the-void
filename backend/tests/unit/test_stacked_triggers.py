import importlib.util
from pathlib import Path
from types import ModuleType

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "check_stacked_triggers.py"


def guard() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_stacked_triggers", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SCREEN = """export function Panel() {
  return (
    <div className='flex min-w-0 flex-col{spacing}'>
      <AdjustPanel trigger='Make a stratum' title='Make' />
      <RaiseSoul regionId={1} blocked={null} />
    </div>
  )
}
"""


def test_two_triggers_stacked_with_no_gap_are_caught_and_a_gap_clears_them(tmp_path: Path) -> None:
    module = guard()
    module.ROOT = tmp_path
    screen = tmp_path / "Panel.tsx"
    screen.write_text(SCREEN.replace("{spacing}", ""), encoding="utf-8")
    known = module.BASE_TRIGGERS | {"RaiseSoul"}
    assert len(module.stacked(screen, known)) == 1
    screen.write_text(SCREEN.replace("{spacing}", " gap-2"), encoding="utf-8")
    assert module.stacked(screen, known) == []
