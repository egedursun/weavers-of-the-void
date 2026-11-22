import ast
from pathlib import Path

TESTS = Path(__file__).resolve().parents[1]


def untimed(source: str) -> list[int]:
    found = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Call) and getattr(node.func, "id", getattr(node.func, "attr", "")) == "LifespanManager":
            keywords = {keyword.arg for keyword in node.keywords}
            if not {"startup_timeout", "shutdown_timeout"} <= keywords:
                found.append(node.lineno)
    return found


def test_every_app_started_in_a_test_waits_long_enough_under_a_loaded_gate() -> None:
    missing = [f"{path.relative_to(TESTS)}:{line}" for path in sorted(TESTS.rglob("*.py")) for line in untimed(path.read_text(encoding="utf-8"))]
    assert missing == []


def test_a_lifespan_with_the_default_timeout_is_caught() -> None:
    assert untimed("LifespanManager(app)") == [1]
    assert untimed("LifespanManager(app, startup_timeout=120, shutdown_timeout=120)") == []
