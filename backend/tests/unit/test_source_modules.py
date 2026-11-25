import ast
import re
from pathlib import Path

from tests.source_modules import is_skipped, source_modules

BACKEND = Path(__file__).resolve().parents[2]
ROOT = BACKEND.parent
WALKER = BACKEND / "tests" / "source_modules.py"
SCRIPT_WALKER = ROOT / "scripts" / "check_partial_reads.py"
WHOLE_ROOT = frozenset({"SOURCE", "PACKAGE", "aerona.__path__"})
PREFIX_SKIP = re.compile(r'"db/alembic|"db" / "alembic"|"aerona\.db\.alembic"')
SKIP_NAMES = re.compile(r"SKIP|MIGRATIONS")
SEGMENT_SKIP = re.compile(r'"alembic" (?:not )?in ')


def walks_whole_root(call: ast.Call) -> bool:
    if not call.args:
        return False
    target = call.args[0]
    if isinstance(target, ast.List) and target.elts:
        target = target.elts[0]
        if isinstance(target, ast.Call) and target.args:
            target = target.args[0]
    return ast.unparse(target) in WHOLE_ROOT


def own_walkers() -> list[str]:
    found = []
    for folder in (BACKEND / "tests", ROOT / "scripts"):
        for path in sorted(folder.rglob("*.py")):
            if path in (WALKER, SCRIPT_WALKER) or "__pycache__" in path.parts:
                continue
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if isinstance(node, ast.Call) and ast.unparse(node.func).endswith("walk_packages") and walks_whole_root(node):
                    found.append(f"{path.relative_to(ROOT)}:{node.lineno}")
    return found


def test_every_source_module_outside_the_migration_packages_imports() -> None:
    names = [module.__name__ for module in source_modules()]
    assert names
    assert [name for name in names if "alembic" in name.split(".")] == []


def test_a_migration_package_anywhere_in_the_source_is_skipped() -> None:
    assert is_skipped("aerona.db.alembic.env")
    assert is_skipped("aerona.db.library.alembic.env")
    assert is_skipped("aerona.anything.alembic.versions.head")
    assert not is_skipped("aerona.db.library.tables")


def test_no_test_or_script_walks_the_whole_source_with_its_own_skip_list() -> None:
    assert own_walkers() == [], "walk the source through tests.source_modules.source_modules, which skips every migration package"


def skip_constant(node: ast.stmt) -> bool:
    return isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and SKIP_NAMES.search(target.id) for target in node.targets)


def skips_by_prefix(tree: ast.Module) -> bool:
    return any(skip_constant(node) and PREFIX_SKIP.search(ast.unparse(node.value)) for node in tree.body if isinstance(node, ast.Assign))


def prefix_only_skips() -> list[str]:
    return [
        str(path.relative_to(ROOT))
        for path in sorted((ROOT / "scripts").glob("*.py"))
        if skips_by_prefix(ast.parse(text := path.read_text(encoding="utf-8"))) and not SEGMENT_SKIP.search(text)
    ]


def test_a_script_that_skips_the_migrations_skips_every_migration_package() -> None:
    assert prefix_only_skips() == [], "skip any path with an alembic part, so a second database's migrations are skipped too"
