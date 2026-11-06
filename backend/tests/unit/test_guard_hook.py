import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

HOOK = Path(__file__).resolve().parents[3] / ".claude" / "hooks" / "guard_tests.py"


def load_guard() -> ModuleType:
    spec = importlib.util.spec_from_file_location("guard_tests", HOOK)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GUARD = load_guard()

ALLOWED = (
    "npx vitest run src/a.test.tsx src/b.test.tsx 2>&1 | tail -25",
    "npx vitest run src/a.test.tsx --reporter dot",
    "npx vitest run src/a.test.tsx --reporter=dot > out.txt",
    "cd frontend && npx vitest run src/a.test.tsx 2> err.log",
    "(cd frontend && npx vitest run src/a.test.tsx)",
    "uv run pytest -q -p no:cacheprovider tests/a/test_x.py tests/b/test_y.py 2>&1 | tail -5",
    "uv run pytest tests/a/test_x.py::test_one >> log.txt",
    "grep -n vitest -A12 .claude/hooks/guard_tests.py",
    "grep -rn pytest docs | head",
    "cat package.json | grep vitest",
    "AERONA_X=1 uv run pytest tests/a/test_x.py",
    "backend/.venv/bin/pytest tests/a/test_x.py",
)

BLOCKED = (
    "npx vitest run",
    "npx vitest run src/features",
    "npx vitest run src/features 2>&1 | tail",
    "uv run pytest",
    "uv run pytest tests",
    "uv run pytest tests/engine 2>&1",
    "uv run pytest -n 4 tests/a/test_x.py",
    "uv run pytest " + " ".join(f"tests/test_{index}.py" for index in range(7)),
    "npm test",
    "npm run test",
    "make test",
    "npx playwright test",
    "(cd frontend && npx vitest)",
    "uv run python -m pytest tests",
)


@pytest.mark.parametrize("command", ALLOWED)
def test_named_test_files_run_whatever_the_shell_around_them(command: str) -> None:
    assert GUARD.problem(command) is None


@pytest.mark.parametrize("command", BLOCKED)
def test_broad_runs_stay_blocked(command: str) -> None:
    assert GUARD.problem(command) is not None
