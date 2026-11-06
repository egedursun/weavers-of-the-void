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
REDIRECT = re.compile(r"^(\d*|&)(>>?|<)(&?\d*)?$")
INLINE_REDIRECT = re.compile(r"^(\d*|&)(>>?|<)&?\S+$")
RUNNERS = frozenset({"npx", "pnpm", "yarn", "bunx", "exec", "dlx", "uv", "run", "python", "python3", "-m", "poetry", "env", "time", "nice"})
ENV_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")


def words(segment: str) -> list[str]:
    try:
        parts = shlex.split(segment)
    except ValueError:
        parts = segment.split()
    kept: list[str] = []
    skip = False
    for part in parts:
        if skip:
            skip = False
            continue
        if REDIRECT.match(part):
            skip = not part.endswith(("&1", "&2"))
            continue
        if INLINE_REDIRECT.match(part):
            continue
        kept.append(part)
    return kept


def runner_index(parts: list[str], tool: str) -> int | None:
    for index, part in enumerate(parts):
        if part.endswith(tool) and (part == tool or part.endswith(f"/{tool}")):
            head = parts[:index]
            return index if all(item in RUNNERS or ENV_ASSIGNMENT.match(item) or item.endswith(("/python", "/python3")) for item in head) else None
    return None


def flag_values(args: list[str]) -> set[int]:
    values: set[int] = set()
    for index, arg in enumerate(args[:-1]):
        following = args[index + 1]
        if arg.startswith("-") and "=" not in arg and not following.startswith("-") and not JS_TEST_FILE.search(following) and not PY_TEST_FILE.search(following):
            values.add(index + 1)
    return values


def pytest_problem(parts: list[str], start: int) -> str | None:
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


def vitest_problem(parts: list[str], start: int) -> str | None:
    args = [arg for arg in parts[start + 1 :] if arg not in {"run", "--run"}]
    values = flag_values(args)
    targets = [arg for index, arg in enumerate(args) if not arg.startswith("-") and index not in values]
    files = [arg for arg in targets if JS_TEST_FILE.search(arg)]
    if not files or len(files) != len(targets):
        return "vitest must name individual test files, never a directory or the whole suite"
    if len(files) > MAX_TEST_FILES:
        return f"vitest may run at most {MAX_TEST_FILES} test files at once"
    return None


def problem(command: str) -> str | None:
    for segment in SEGMENT_SPLIT.split(command):
        text = segment.strip().strip("()").strip()
        if not text:
            continue
        for pattern in ALWAYS_BROAD:
            if pattern.search(text):
                return f"'{pattern.pattern}' runs a broad test suite"
        parts = words(text)
        pytest_at = runner_index(parts, "pytest") if PYTEST.search(text) else None
        if pytest_at is not None:
            found = pytest_problem(parts, pytest_at)
            if found:
                return found
        vitest_at = runner_index(parts, "vitest") if VITEST.search(text) else None
        if vitest_at is not None:
            found = vitest_problem(parts, vitest_at)
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
