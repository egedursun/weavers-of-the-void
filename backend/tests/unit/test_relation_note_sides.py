import ast
import re
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[2] / "src" / "aerona"
FIRST_PERSON = re.compile(r"\b(ours|our|us|we|my|me|mine)\b", re.IGNORECASE)


def note_text(node: ast.expr) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(part.value for part in node.values if isinstance(part, ast.Constant) and isinstance(part.value, str))
    return ""


def one_sided_notes() -> list[str]:
    found: list[str] = []
    for path in sorted(SOURCE.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for call in ast.walk(tree):
            if not isinstance(call, ast.Call) or getattr(call.func, "id", getattr(call.func, "attr", None)) != "change_relation":
                continue
            words = {keyword.arg: keyword.value for keyword in call.keywords}
            note = words.get("note")
            if note is not None and FIRST_PERSON.search(note_text(note)) and "reverse_note" not in words:
                found.append(f"{path.relative_to(SOURCE)}:{call.lineno}")
    return found


def test_a_relation_note_told_by_one_side_gives_the_other_side_its_own_words() -> None:
    assert one_sided_notes() == []
