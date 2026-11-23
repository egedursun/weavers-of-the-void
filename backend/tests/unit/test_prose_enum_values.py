import ast
import re
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[2] / "src" / "aerona"
KEY_BEFORE = frozenset("_'\"{./=:#-[")
KEY_AFTER = frozenset("_'\"}/=]")
WORDING = frozenset({"replace", "title", "capitalize", "lower", "upper"})
ARTICLED = frozenset({"an"})
RENDERERS = frozenset({"result", "fail"})


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


def member_text(node: ast.expr) -> bool:
    worded = isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in WORDING
    return enum_text(node) and (worded or (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Attribute)))


def raw_names(function: ast.AST) -> frozenset[str]:
    return frozenset(
        target.id
        for node in ast.walk(function)
        if isinstance(node, ast.Assign) and member_text(node.value)
        for target in node.targets
        if isinstance(target, ast.Name)
    )


CASED = frozenset({"title", "capitalize", "upper"})


TEMPLATE_WORDING = re.compile(r"\.value\s*\|\s*(?:replace|title|capitalize|upper|lower)\b")


def hand_wording(node: ast.stmt) -> bool:
    if not (isinstance(node, ast.FunctionDef) and len(node.args.args) == 1 and len(node.body) == 1 and isinstance(node.body[0], ast.Return)):
        return False
    returned = node.body[0].value
    param = node.args.args[0].arg
    return returned is not None and any(
        isinstance(part, ast.Call)
        and isinstance(part.func, ast.Attribute)
        and isinstance(part.func.value, ast.Name)
        and part.func.value.id == param
        and part.func.attr == "replace"
        and bool(part.args)
        and isinstance(part.args[0], ast.Constant)
        and "_" in str(part.args[0].value)
        for part in ast.walk(returned)
    )


def module_name(path: Path) -> str:
    return ".".join(("aerona", *path.relative_to(SOURCE).with_suffix("").parts))


def wording_helpers() -> frozenset[tuple[str, str]]:
    return frozenset((module_name(path), node.name) for path in sorted(SOURCE.rglob("*.py")) for node in ast.parse(path.read_text()).body if hand_wording(node))


def imported_helpers(tree: ast.Module, helpers: frozenset[tuple[str, str]]) -> set[str]:
    return {
        alias.asname or alias.name
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module
        for alias in node.names
        if (node.module, alias.name) in helpers
    }


def worded_values(text: str, helpers: frozenset[tuple[str, str]] = frozenset()) -> list[str]:
    found: list[str] = []
    tree = ast.parse(text)
    helpers_here = {node.name for node in tree.body if hand_wording(node)} | imported_helpers(tree, helpers)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in helpers_here:
            if any(isinstance(arg, ast.Attribute) and arg.attr == "value" for arg in node.args):
                found.append(f"{node.lineno}: {ast.unparse(node)}")
            continue
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        receiver = node.func.value
        if not (isinstance(receiver, ast.Attribute) and receiver.attr == "value"):
            continue
        underscored = node.func.attr == "replace" and bool(node.args) and isinstance(node.args[0], ast.Constant) and "_" in str(node.args[0].value)
        if underscored or node.func.attr in CASED:
            found.append(f"{node.lineno}: {ast.unparse(node)}")
    return found


def worded_in_template(text: str) -> list[str]:
    return [f"{number}: {line.strip()}" for number, line in enumerate(text.splitlines(), start=1) if TEMPLATE_WORDING.search(line)]


def raw_arguments(text: str) -> list[str]:
    found: list[str] = []
    for function in ast.walk(ast.parse(text)):
        if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        held = raw_names(function)
        for node in ast.walk(function):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in RENDERERS):
                continue
            for keyword in node.keywords:
                named = isinstance(keyword.value, ast.Name) and keyword.value.id in held
                if member_text(keyword.value) or named:
                    found.append(f"{keyword.value.lineno}: {keyword.arg}={ast.unparse(keyword.value)}")
    return sorted(set(found))


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


def test_a_raw_enum_value_handed_to_a_tool_sentence_is_found_while_numbers_named_value_are_kept() -> None:
    assert raw_arguments("def f():\n    return result(R.DONE, kind=args.kind.value, level=level)")
    assert raw_arguments("def f():\n    fail(R.NO, court=row.to_court.value.replace('_', ' '))")
    assert raw_arguments("def f():\n    told = args.response.value.replace('_', ' ')\n    return result(R.DONE, response=told)")
    assert not raw_arguments("def f():\n    return result(R.DONE, kind=spoken(args.kind), value=gift.value)")


def test_no_tool_sentence_is_handed_an_enum_by_its_raw_value() -> None:
    found = [f"{path.relative_to(SOURCE)}:{line}" for path in sorted(SOURCE.rglob("*.py")) for line in raw_arguments(path.read_text())]
    assert not found, found


def test_an_enum_value_worded_by_hand_is_found_while_spoken_words_are_kept() -> None:
    assert worded_values('label = command.kind.value.replace("_", " ")')
    assert worded_values('parts.append(row.school.value.replace("_", " "))')
    assert worded_values("LABELS = {job.value: job.value.capitalize() for job in Job}")
    assert worded_values('name = f"{material.value.title()} of {place.name}"')
    assert worded_values('label = school.value.replace("elemental_", "")')
    assert not worded_values("label = spoken(command.kind)")
    assert not worded_values("LABELS = {job.value: spoken(job).capitalize() for job in Job}")
    assert not worded_values('key = f"{kind.value}_cost"')
    assert not worded_values('text = row.text.replace("_", " ")')


def test_an_enum_value_worded_by_a_local_helper_is_found_while_plain_text_through_it_is_kept() -> None:
    helper = 'def words(value: str) -> str:\n    return value.replace("_", " ")\n\n\n'
    assert worded_values(helper + 'line = f"a tale of {words(row.archetype.value)}"')
    assert worded_values(helper.replace("words", "label") + "names = [label(kind.value) for kind in Kind]")
    assert worded_values('def school(value: str) -> str:\n    return value.replace("elemental_", "").replace("_", " ")\n\n\nx = school(gift.value)')
    assert not worded_values(helper + "line = words(row.taboo_target)")
    assert not worded_values(helper + 'line = f"a tale of {spoken(row.archetype)}"')
    imported = frozenset({("aerona.agents.context.cycle_lines", "words")})
    assert worded_values("from aerona.agents.context.cycle_lines import named, words\n\nline = words(row.kind.value)", imported)
    assert not worded_values("from aerona.agents.context.cycle_lines import named, words\n\nline = words(row.kind.value)")


def test_an_enum_value_worded_by_hand_in_a_template_is_found_while_spoken_words_are_kept() -> None:
    assert worded_in_template('{{ route.method.value | replace("_", " ") }}')
    assert worded_in_template("*{{ war.war.cause.value|title }}*")
    assert worded_in_template("{{ god.status.value | lower }}")
    assert not worded_in_template("{{ route.method | spoken }}")
    assert not worded_in_template('{% if article.entity.status.value in ("dead", "destroyed") %} †{% endif %}')
    assert not worded_in_template("{{ fact.value | cell }}")


def test_no_enum_value_is_worded_by_hand() -> None:
    helpers = wording_helpers()
    found = [f"{path.relative_to(SOURCE)}:{line}" for path in sorted(SOURCE.rglob("*.py")) for line in worded_values(path.read_text(), helpers)]
    assert not found, found


def test_no_template_words_an_enum_value_by_hand() -> None:
    found = [f"{path.relative_to(SOURCE)}:{line}" for path in sorted(SOURCE.rglob("*.j2")) for line in worded_in_template(path.read_text())]
    assert not found, found
