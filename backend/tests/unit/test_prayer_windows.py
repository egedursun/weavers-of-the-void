import ast
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[2] / "src" / "aerona" / "engine"
WINDOW = {"judged_in_run", "overdue_in_run", "judged_epoch", "still_awaiting"}


def readers_of_answers() -> list[tuple[str, str, set[str]]]:
    found: list[tuple[str, str, set[str]]] = []
    for path in sorted(ENGINE.rglob("*.py")):
        if path.name == "prayer_window.py":
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            names = {item.id for item in ast.walk(node) if isinstance(item, ast.Name)}
            attributes = {item.attr for item in ast.walk(node) if isinstance(item, ast.Attribute)}
            if "MessageRow" in names and "answered" in attributes:
                found.append((str(path.relative_to(ENGINE)), node.name, names & WINDOW))
    return found


def test_the_engine_reads_a_prayer_answer_only_once_the_player_could_give_it() -> None:
    readers = readers_of_answers()
    assert readers
    blind = [f"{path}:{name}" for path, name, window in readers if not window]
    assert not blind, f"these steps read whether a prayer was answered without the answer window of engine/divine/prayer_window.py: {blind}"
