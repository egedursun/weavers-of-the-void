import json
import re
import shlex
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OVERRIDE = ROOT / ".claude" / "allow-broad-tests"
MAX_TEST_FILES = 6
SEGMENT_SPLIT = re.compile(r"&&|\|\||;|\||\n")
ALWAYS_BROAD = (
    re.compile(r"\bplaywright\b"),
    re.compile(r"\btest:e2e\b"),
    re.compile(r"\bmake\s+(test|check|image-worker-test)\b"),
    re.compile(r"\bnpm\s+(run\s+)?test(?!:lint-rules)\b"),
)
PYTEST = re.compile(r"\bpytest\b")
VITEST = re.compile(r"\bvitest\b")
PY_TEST_FILE = re.compile(
    r"(^|/)test_[\w.-]*\.py(::\S+)?$|(^|/)[\w.-]*_test\.py(::\S+)?$"
)
JS_TEST_FILE = re.compile(r"\.(test|spec)\.(ts|tsx|js|jsx)$")
PARALLEL = re.compile(r"^(-n\S*|--numprocesses(=\S+)?|--last-failed|--lf)$")


def words(segment: str) -> list[str]:
    try:
        return shlex.split(segment)
    except ValueError:
        return segment.split()


def pytest_problem(parts: list[str]) -> str | None:
    start = next(index for index, part in enumerate(parts) if part.endswith("pytest"))
    args = parts[start + 1 :]
    if any(PARALLEL.match(arg) for arg in args):
        return "pytest with -n or a re-run flag is a broad sweep"
    files = [
        arg for arg in args if not arg.startswith("-") and PY_TEST_FILE.search(arg)
    ]
    targets = [
        arg
        for arg in args
        if not arg.startswith("-")
        and ("/" in arg or arg.endswith(".py") or arg == "tests")
    ]
    if not files or len(files) != len(targets):
        return "pytest must name individual test files, never a directory or the whole suite"
    if len(files) > MAX_TEST_FILES:
        return f"pytest may run at most {MAX_TEST_FILES} test files at once"
    return None


def vitest_problem(parts: list[str]) -> str | None:
    start = next(index for index, part in enumerate(parts) if part.endswith("vitest"))
    args = [arg for arg in parts[start + 1 :] if arg not in {"run", "--run"}]
    targets = [arg for arg in args if not arg.startswith("-")]
    files = [arg for arg in targets if JS_TEST_FILE.search(arg)]
    if not files or len(files) != len(targets):
        return "vitest must name individual test files, never a directory or the whole suite"
    if len(files) > MAX_TEST_FILES:
        return f"vitest may run at most {MAX_TEST_FILES} test files at once"
    return None


def problem(command: str) -> str | None:
    for segment in SEGMENT_SPLIT.split(command):
        text = segment.strip()
        if not text:
            continue
        for pattern in ALWAYS_BROAD:
            if pattern.search(text):
                return f"'{pattern.pattern}' runs a broad test suite"
        parts = words(text)
        if PYTEST.search(text) and any(part.endswith("pytest") for part in parts):
            found = pytest_problem(parts)
            if found:
                return found
        if VITEST.search(text) and any(part.endswith("vitest") for part in parts):
            found = vitest_problem(parts)
            if found:
                return found
    return None


def main() -> int:
    payload = json.load(sys.stdin)
    command = str(payload.get("tool_input", {}).get("command", ""))
    found = problem(command)
    if found is None or OVERRIDE.exists():
        return 0
    print(
        f"Blocked by CLAUDE.md rule 1 (no unneeded tests): {found}. "
        "Run only the few test files that directly cover the change. "
        "Broad runs need the user to create .claude/allow-broad-tests themselves.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
