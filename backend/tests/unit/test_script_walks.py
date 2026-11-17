import ast
import importlib.util
import re
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = REPOSITORY_ROOT / "scripts"
WALK = re.compile(r"\.rglob\(\"\*\"\)")
FILE_TEST = re.compile(r"is_file\(\)|is_dir\(\)")
WALK_WINDOW = 4


def script(name: str) -> ModuleType:
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def screenshot_tree(root: Path) -> Path:
    (root / "feature" / "__screenshots__" / "screen.test.tsx").mkdir(parents=True)
    (root / "feature" / "named.tsx").mkdir()
    (root / "feature" / "screen.tsx").write_text("export const shown = 'kept'\n", encoding="utf-8")
    return root


def test_a_folder_named_like_a_source_file_is_skipped(tmp_path: Path) -> None:
    root = screenshot_tree(tmp_path)
    assert script("check_kind_layers").source_text(root, (".ts", ".tsx")) == "export const shown = 'kept'\n"
    assert script("check_scene_colors").findings(root) == []


def file_checks(text: str) -> re.Pattern[str]:
    helpers = [
        node.name for node in ast.walk(ast.parse(text)) if isinstance(node, ast.FunctionDef) and FILE_TEST.search(ast.get_source_segment(text, node) or "")
    ]
    return re.compile("|".join([FILE_TEST.pattern, *(rf"\b{name}\(" for name in helpers)]))


def test_every_script_walk_reads_files_only() -> None:
    unguarded: list[str] = []
    for path in sorted(SCRIPTS.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        checked = file_checks(text)
        lines = text.splitlines()
        for number, line in enumerate(lines):
            if WALK.search(line) and not checked.search("\n".join(lines[number : number + WALK_WINDOW])):
                unguarded.append(f"{path.name}:{number + 1}")
    assert unguarded == []
