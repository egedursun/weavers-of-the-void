import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_scene_colors", REPOSITORY_ROOT / "scripts" / "check_scene_colors.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_scene_colors"] = module
    spec.loader.exec_module(module)
    return module


def test_a_css_colour_handed_to_three_unresolved_is_found(tmp_path: Path) -> None:
    module = checker()
    (tmp_path / "scene.ts").write_text(
        "const color = new Color()\ncolor.setStyle(value)\nconst sky = new Color(getComputedStyle(root).getPropertyValue('--card'))\n",
        encoding="utf-8",
    )
    (tmp_path / "good.ts").write_text("const sky = new Color(tokenHex('--card'))\n", encoding="utf-8")
    (tmp_path / "scene.test.ts").write_text("color.setStyle(value)\n", encoding="utf-8")
    found = module.findings(tmp_path)
    assert [(item.path.name, item.line) for item in found] == [("scene.ts", 2), ("scene.ts", 3)]


def test_the_frontend_hands_three_only_resolved_colours() -> None:
    assert checker().findings() == []
