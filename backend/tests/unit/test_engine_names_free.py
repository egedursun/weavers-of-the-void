import ast
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[2] / "src" / "aerona"
ENGINE_NAMED = ("engine", "agents", "services")
PLAYER_NAMED = ("services/player",)
NAMING_CALLS = {"rename", "claim"}
FREE_CHECKS = {"is_taken", "unique_name", "free_name", "validate_new_name"}


def called(node: ast.AST) -> set[str]:
    names: set[str] = set()
    for call in ast.walk(node):
        if isinstance(call, ast.Call):
            target = call.func
            if isinstance(target, ast.Attribute):
                names.add(target.attr)
            elif isinstance(target, ast.Name):
                names.add(target.id)
    return names


def frees(call: ast.Call) -> bool:
    return any(keyword.arg == "free" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True for keyword in call.keywords)


def unguarded(tree: ast.AST) -> list[int]:
    found: list[int] = []
    for function in ast.walk(tree):
        if not isinstance(function, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        checked = bool(called(function) & FREE_CHECKS)
        for call in ast.walk(function):
            if (
                isinstance(call, ast.Call)
                and isinstance(call.func, ast.Attribute)
                and call.func.attr in NAMING_CALLS
                and len(call.args) >= 2
                and not frees(call)
                and not checked
            ):
                found.append(call.lineno)
    return found


def engine_modules() -> list[Path]:
    return sorted(
        path
        for folder in ENGINE_NAMED
        for path in (SOURCE / folder).rglob("*.py")
        if not any(path.relative_to(SOURCE).as_posix().startswith(f"{player}/") for player in PLAYER_NAMED)
    )


def test_a_name_the_engine_makes_up_never_collides_with_one_already_held() -> None:
    problems = [f"{path.relative_to(SOURCE)}:{line}" for path in engine_modules() for line in unguarded(ast.parse(path.read_text(encoding="utf-8")))]
    assert problems == [], (
        "these engine, agent or repair steps give a record a name they made up without checking that no other record holds it, "
        "so a clash stops the whole step with 'already taken'; pass free=True to rename or claim, or check is_taken first: " + ", ".join(problems)
    )


def test_the_guard_catches_an_unchecked_rename() -> None:
    code = (
        "async def bad(session, node_id, name):\n"
        "    await NameRepository(session).rename(node_id, name)\n"
        "async def good(session, node_id, name):\n"
        "    await NameRepository(session).rename(node_id, name, free=True)\n"
        "async def checked(session, node_id, name):\n"
        "    if not await names.is_taken(name, node_id):\n"
        "        await names.claim(node_id, name)\n"
    )
    assert unguarded(ast.parse(code)) == [2]
