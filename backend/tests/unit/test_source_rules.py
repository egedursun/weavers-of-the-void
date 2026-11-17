import ast
import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def test_repository_follows_source_rules() -> None:
    script = REPOSITORY_ROOT / "scripts" / "check_source_rules.py"
    completed = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, check=False)
    assert completed.returncode == 0, completed.stdout


def load_rules() -> ModuleType:
    spec = importlib.util.spec_from_file_location("source_rules", REPOSITORY_ROOT / "scripts" / "check_source_rules.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_a_local_named_like_the_hold_guard_is_caught() -> None:
    rules = load_rules()
    shadowing = "from aerona.db.write_guard import held\n\n\ndef weigh(rows):\n    held = {row for row in rows}\n    return held\n"
    clean = "from aerona.db.write_guard import held\n\n\ndef weigh(rows):\n    return [row for row in rows if not held(row)]\n"
    tree = ast.parse(shadowing)
    assert rules.shadowed_guards(tree, rules.guard_imports(tree)) == [(5, "held")]
    tree = ast.parse(clean)
    assert rules.shadowed_guards(tree, rules.guard_imports(tree)) == []


def test_build_caches_of_every_dev_server_are_not_source() -> None:
    module = load_rules()
    for cache in (".vite-cache", "node_modules", "dist"):
        assert cache in module.SKIPPED_DIRS


def test_a_naive_singular_is_caught() -> None:
    rules = load_rules()
    naive = "label = words(target).lower().rstrip(" + repr("s") + ")"
    assert rules.NAIVE_SINGULAR.search(naive)
    assert not rules.NAIVE_SINGULAR.search("label = singular(words(target).lower())")


def test_a_local_or_argument_that_hides_an_import_is_caught_but_a_comprehension_name_is_its_own() -> None:
    rules = load_rules()
    source = (
        "from aerona.engine.recording.record import record\n"
        "from aerona.core.total import total\n"
        "async def write(ctx, total):\n"
        "    record = 1\n"
        "    rows = [record for record in range(3)]\n"
        "    return rows\n"
    )
    assert rules.shadowed_imports(ast.parse(source)) == [(3, "total"), (4, "record")]
    kept = "from aerona.engine.recording.record import record\nasync def write(ctx):\n    return [record for record in range(3)]\n"
    assert rules.shadowed_imports(ast.parse(kept)) == []
