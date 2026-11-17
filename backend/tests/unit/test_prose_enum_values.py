import ast
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[2] / "src" / "aerona"
KEY_BEFORE = frozenset("_'\"{./=:#-[")
KEY_AFTER = frozenset("_'\"}/=]")
WORDING = frozenset({"replace", "title", "capitalize", "lower", "upper"})
ARTICLED = frozenset({"an"})


def enum_text(node: ast.expr) -> bool:
    while isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in WORDING:
        node = node.func.value
    return isinstance(node, ast.Attribute) and node.attr == "value"


def shown(node: ast.expr) -> ast.expr:
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ARTICLED and node.args:
        return node.args[0]
    return node


def literal(part: ast.expr | None) -> str:
    return part.value if isinstance(part, ast.Constant) and isinstance(part.value, str) else ""


def keyed(before: str, after: str) -> bool:
    return (before[-1:] in KEY_BEFORE and before[-1:] != "") or (after[:1] in KEY_AFTER and after[:1] != "") or (after[:1] == "." and after[1:2].isalnum())


def raw_values(text: str) -> list[str]:
    found: list[str] = []
    for node in ast.walk(ast.parse(text)):
        if not isinstance(node, ast.JoinedStr):
            continue
        words = "".join(literal(part) for part in node.values).split()
        if len(words) < 2:
            continue
        for index, part in enumerate(node.values):
            if not isinstance(part, ast.FormattedValue) or part.conversion != -1 or part.format_spec is not None or not enum_text(shown(part.value)):
                continue
            before = literal(node.values[index - 1]) if index > 0 else ""
            after = literal(node.values[index + 1]) if index + 1 < len(node.values) else ""
            if not keyed(before, after):
                found.append(f"{part.value.lineno}: {ast.unparse(shown(part.value))}")
    return found


def test_a_raw_enum_value_in_a_sentence_is_found_while_keys_and_marked_numbers_are_kept() -> None:
    assert raw_values('f"{owner.name} enclosed the common {row.kind.value} of {town.name}."')
    assert raw_values("f\"the {kind.value.replace('_', ' ')} law\"")
    assert raw_values('f"{mortal.name} became {an(role.value)} at last"')
    assert not raw_values('f"the common {spoken(row.kind)} of {town.name}"')
    assert not raw_values('f"rule death.sibling_{kind.value}_cost holds"')
    assert not raw_values("f\"state = '{BondKind.INSIDE.value}' AND role IS NULL\"")
    assert not raw_values('f"The tongues understand each other {row.value:d}%."')
    assert not raw_values('f"star kind {raw!r} read as {found.value!r}"')


def test_no_sentence_prints_an_enum_by_its_raw_value() -> None:
    found = [f"{path.relative_to(SOURCE)}:{line}" for path in sorted(SOURCE.rglob("*.py")) for line in raw_values(path.read_text())]
    assert not found, found
