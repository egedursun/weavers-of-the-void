import ast
from pathlib import Path

from aerona.catalog.bonds import KNOWN_TYPES
from aerona.domain.enums.entity import EntityType

SOURCE = Path(__file__).resolve().parents[2] / "src" / "aerona"
HELD_BY_OWNING = ("rite",)


def knows(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    name = node.func.attr if isinstance(node.func, ast.Attribute) else node.func.id if isinstance(node.func, ast.Name) else ""
    return name in {"connect", "BondDraft"} and any(isinstance(arg, ast.Attribute) and arg.attr == "KNOWS" for arg in ast.walk(node))


def misplaced(text: str) -> list[int]:
    found: list[int] = []
    for function in ast.walk(ast.parse(text)):
        if not isinstance(function, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        for call in ast.walk(function):
            if knows(call) and any(word in f"{function.name} {ast.unparse(call)}".lower() for word in HELD_BY_OWNING):
                found.append(call.lineno)
    return found


def test_a_rite_is_held_by_owning_it_since_knowing_reaches_only_knowledge_and_places() -> None:
    assert EntityType.RITE not in KNOWN_TYPES
    wrong = [f"{path.relative_to(SOURCE)}:{line}" for path in SOURCE.rglob("*.py") for line in misplaced(path.read_text(encoding="utf-8"))]
    assert wrong == []


def test_the_guard_finds_a_rite_taught_as_knowledge() -> None:
    old = "async def recover_rite(ctx, finder, known):\n    await connect(ctx.session, finder.id, known[0].id, BondKind.KNOWS, ctx.epoch)\n"
    assert misplaced(old) == [2]
