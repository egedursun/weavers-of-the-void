import importlib.util
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

TWO_ACTIONS = """
export function Customs() {
  return (
    <div>
      <Button onClick={() => kin.mutate()}>
        <Users />
        Set them
      </Button>
      <Button onClick={() => union.mutate()}>
        <Heart />
        Set them
      </Button>
    </div>
  )
}
"""

NAMED = """
export function Customs() {
  return (
    <div>
      <Button onClick={() => kin.mutate()}>Set their ways of kin</Button>
      <StepButton label='Set their customs of union' onClick={() => union.mutate()} />
    </div>
  )
}

function Row() {
  return <StepButton label='Set their ways of kin' onClick={() => other.mutate()} />
}
"""


def guard() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_duplicate_buttons", REPOSITORY_ROOT / "scripts" / "check_duplicate_buttons.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_two_buttons_of_one_name_in_one_component_are_found() -> None:
    checker = guard()
    found = [label for _, body in checker.components(TWO_ACTIONS) for label in checker.duplicates(body)]
    assert found == ["Set them"]


def test_buttons_named_for_their_action_pass_even_across_components() -> None:
    checker = guard()
    assert not [label for _, body in checker.components(NAMED) for label in checker.duplicates(body)]
