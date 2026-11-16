import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_spec_depth", REPOSITORY_ROOT / "scripts" / "check_spec_depth.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_spec_depth"] = module
    spec.loader.exec_module(module)
    return module


def test_a_section_that_names_only_its_idea_is_thin(tmp_path: Path) -> None:
    module = checker()
    spec = tmp_path / "spec.md"
    spec.write_text(
        "\n\n".join(
            (
                "## Part 9",
                "### 9.9 A new idea",
                "Peoples come to like it.",
                "### 9.10 A full idea",
                "**State.** `idea_rows` table.",
                "**Behaviour.** Each epoch the engine reads it.",
                "**Rules namespace** `ideas`.",
                "**Tools and control.** God levers `idea:*` in the drawer.",
            )
        )
    )
    roots = module.parse(spec)
    module.gather(roots)
    found = {root.number: module.missing(root) for root in roots}
    assert found["9.9"]
    assert found["9.10"] == []


def test_every_section_of_the_specs_names_its_depth() -> None:
    assert checker().main() == 0
