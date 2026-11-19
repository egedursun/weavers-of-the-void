import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "backend" / "src" / "aerona"
FRONTEND = ROOT / "frontend" / "src"
COUNT_NAMES = frozenset({"count", "total", "made", "closed", "n", "found", "cleared", "seats", "inhabited", "most", "loyal", "elapsed"})
IRREGULAR = frozenset({"people", "children", "men", "women", "were", "are"})
NOT_PLURAL = frozenset({"its", "this", "was", "has", "is", "as", "us", "yes", "plus", "always", "perhaps", "less", "unless", "across", "towards", "thus"})
WORD = re.compile(r"^ ([a-z][a-z-]*)")
SECOND_WORD = re.compile(r"^ ([a-z][a-z-]*) ([a-z][a-z-]*)")
LINKS = frozenset({"in", "of", "for", "to", "at", "on", "by", "from", "with", "per", "into", "than", "and", "or", "out"})
INT_CALLS = frozenset({"len", "sum", "round", "int", "min", "max", "round_half_up", "clamp_int"})
TEMPLATE = re.compile(r"\{(count|total|n)\} ([a-z][a-z-]*)")
TEMPLATE_PAIR = re.compile(r"\{(count|total|n)\} ([a-z][a-z-]*) ([a-z][a-z-]*)")
NUMBER_FIELDS = frozenset(
    {"count", "total", "n", "epochs", "remaining", "cap", "limit", "steps", "legs", "length"}
    | {"attendance", "wait", "tonnage", "found", "stall", "minimum", "keeps", "caught", "purged"}
)
SINGLE_SAME = re.compile(r"(?<!\{)\{([a-z_]+)\}((?: [a-z-]+)?) \1\b")
JINJA_SAME = re.compile(r"\{\{ ([a-z_]+) \}\}((?: [a-z-]+)?) \1\b")
SPEC = re.compile(r"\{\w+:[a-z -]+\|[a-z -]+\}")
TESTS = ROOT / "backend" / "tests"
SCREEN = re.compile(r"\$\{([^{}`]+)\} ([a-z][a-z-]*)")
COUNTED = re.compile(r"(length|count|Count|total|Total|size)$|^(formatNumber|formatInteger|formatCompact)\(|\.toLocaleString\(")
PLURAL_VERB = re.compile(r"^((?: of [^{}]*?)? (?:were|are|have|remain))\b")
SCREEN_VERB = re.compile(r"plural\((?:[^()]|\([^()]*\))*\)\}((?: of [^`$]*?)? (?:were|are|have|remain))\b")
LAST_NAME = re.compile(r"(\w+)\s*$")


@dataclass(frozen=True)
class Count:
    path: Path
    line: int
    text: str


def plural(word: str) -> bool:
    if word in IRREGULAR:
        return True
    return len(word) > 3 and word.endswith("s") and not word.endswith("ss") and word not in NOT_PLURAL


def int_returning(tree: ast.Module) -> frozenset[str]:
    return frozenset(
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and isinstance(node.returns, ast.Name) and node.returns.id == "int"
    )


def yields_int(node: ast.expr, ints: frozenset[str]) -> bool:
    inner = node.value if isinstance(node, ast.Await) else node
    if isinstance(inner, ast.Constant):
        return isinstance(inner.value, int) and not isinstance(inner.value, bool)
    if isinstance(inner, ast.Call):
        called = inner.func.id if isinstance(inner.func, ast.Name) else inner.func.attr if isinstance(inner.func, ast.Attribute) else None
        return called in INT_CALLS or called in ints
    return False


def counted_names(function: ast.AST, ints: frozenset[str]) -> frozenset[str]:
    names: set[str] = set()
    for node in ast.walk(function):
        if isinstance(node, ast.Assign) and yields_int(node.value, ints):
            names.update(target.id for target in node.targets if isinstance(target, ast.Name))
        elif isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name) and isinstance(node.op, ast.Add):
            names.add(node.target.id)
        elif isinstance(node, ast.arg) and isinstance(node.annotation, ast.Name) and node.annotation.id == "int":
            names.add(node.arg)
    return frozenset(names)


SCOPE: dict[str, frozenset[str]] = {"names": frozenset(), "several": frozenset()}


def several_names(function: ast.AST) -> frozenset[str]:
    return frozenset(
        target.id
        for node in ast.walk(function)
        if isinstance(node, ast.Assign) and counted_by(node.value)
        for target in node.targets
        if isinstance(target, ast.Name)
    )


def counting(node: ast.expr) -> bool:
    if isinstance(node, ast.Call):
        return isinstance(node.func, ast.Name) and node.func.id == "len"
    if isinstance(node, ast.Name):
        return node.id in COUNT_NAMES or node.id.endswith("_count") or node.id in SCOPE["names"]
    if isinstance(node, ast.Attribute):
        base = node.value
        tallied = isinstance(base, ast.Name) and base.id == "tally"
        return tallied or node.attr in COUNT_NAMES or node.attr.endswith("_count")
    return False


def named_alike(node: ast.expr, word: str) -> bool:
    if isinstance(node, ast.Name):
        return node.id == word
    if isinstance(node, ast.Attribute):
        return node.attr == word
    return False


def in_joined(node: ast.JoinedStr) -> list[str]:
    found: list[str] = []
    parts = node.values
    for index, part in enumerate(parts[:-1]):
        after = parts[index + 1]
        if not isinstance(part, ast.FormattedValue) or not isinstance(after, ast.Constant) or not isinstance(after.value, str):
            continue
        match = WORD.match(after.value)
        if match and plural(match.group(1)) and (counting(part.value) or named_alike(part.value, match.group(1))):
            found.append(f"{{{ast.unparse(part.value)}}} {match.group(1)}")
            continue
        pair = SECOND_WORD.match(after.value)
        if pair and not plural(pair.group(1)) and pair.group(1) not in IRREGULAR | LINKS and plural(pair.group(2)) and counting(part.value):
            found.append(f"{{{ast.unparse(part.value)}}} {pair.group(1)} {pair.group(2)}")
    return found


def counted_by(node: ast.expr) -> bool:
    if isinstance(node, ast.Name):
        return node.id in SCOPE["several"]
    return isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "several"


def verbs_after(node: ast.JoinedStr) -> list[str]:
    found: list[str] = []
    for index, part in enumerate(node.values[:-1]):
        after = node.values[index + 1]
        if isinstance(part, ast.FormattedValue) and counted_by(part.value) and isinstance(after, ast.Constant) and isinstance(after.value, str):
            match = PLURAL_VERB.match(after.value)
            if match:
                found.append(f"{{{ast.unparse(part.value)}}}{match.group(1)}")
    return found


def in_template(node: ast.Constant) -> list[str]:
    if not isinstance(node.value, str):
        return []
    found = [f"{{{name}}} {word}" for name, word in TEMPLATE.findall(node.value) if plural(word)]
    pairs = TEMPLATE_PAIR.findall(node.value)
    found += [f"{{{name}}} {first} {second}" for name, first, second in pairs if not plural(first) and first not in IRREGULAR | LINKS and plural(second)]
    found += [f"{{{{ {name} }}}} {word}" for name, word in TEMPLATE_COUNT.findall(node.value) if plural(word) and numeric(name)]
    found += [f"{{{name}}}{between} {name}" for name, between in SINGLE_SAME.findall(node.value) if plural(name)]
    return found + [f"{{{{ {name} }}}}{between} {name}" for name, between in JINJA_SAME.findall(node.value) if plural(name)]


def counts(files: dict[Path, str]) -> list[Count]:
    found: list[Count] = []
    for path, text in files.items():
        tree = ast.parse(text)
        ints = int_returning(tree)
        joined_parts = {id(value) for node in ast.walk(tree) if isinstance(node, ast.JoinedStr) for value in node.values}
        scopes = [node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
        owner = {id(inner): scope for scope in scopes for inner in ast.walk(scope)}
        for node in ast.walk(tree):
            if isinstance(node, ast.JoinedStr):
                scope = owner.get(id(node))
                SCOPE["names"] = counted_names(scope, ints) if scope is not None else frozenset()
                SCOPE["several"] = several_names(scope) if scope is not None else frozenset()
                found.extend(Count(path, node.lineno, item) for item in in_joined(node) + verbs_after(node))
            elif isinstance(node, ast.Constant) and id(node) not in joined_parts:
                found.extend(Count(path, node.lineno, item) for item in in_template(node))
    return found


def spec_templates(files: dict[Path, str]) -> set[str]:
    names: set[str] = set()
    for text in files.values():
        for node in ast.parse(text).body:
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str) and SPEC.search(node.value.value):
                names.update(target.id for target in node.targets if isinstance(target, ast.Name))
    return names


def formatted(files: dict[Path, str], names: set[str]) -> list[Count]:
    found: list[Count] = []
    for path, text in files.items():
        for node in ast.walk(ast.parse(text)):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute) or node.func.attr != "format":
                continue
            target = node.func.value
            name = target.id if isinstance(target, ast.Name) else target.attr if isinstance(target, ast.Attribute) else None
            if name in names:
                found.append(Count(path, node.lineno, f"{name}.format()"))
    return found


def counted_on_screen(expression: str, word: str) -> bool:
    text = expression.strip()
    last = LAST_NAME.search(text)
    return bool(COUNTED.search(text)) or (last is not None and last.group(1) == word)


def on_screen(files: dict[Path, str]) -> list[Count]:
    found: list[Count] = []
    for path, text in files.items():
        for number, line in enumerate(text.splitlines(), start=1):
            found.extend(Count(path, number, f"${{{name}}} {word}") for name, word in SCREEN.findall(line) if plural(word) and counted_on_screen(name, word))
            found.extend(Count(path, number, f"plural(…){verb}") for verb in SCREEN_VERB.findall(line))
    return found


def screens() -> dict[Path, str]:
    return {path: path.read_text(encoding="utf-8") for path in sorted(FRONTEND.rglob("*.ts*")) if ".test." not in path.name}


TEMPLATES = SOURCE / "prompts" / "templates"
TEMPLATE_COUNT = re.compile(r"\{\{ ([a-z_][a-z_0-9.]*) \}\} ([a-z][a-z-]*)")
NAMED_FIELDS = frozenset({"captor", "patron", "people"})


def named(field: str) -> bool:
    last = field.rsplit(".", maxsplit=1)[-1]
    return last.endswith("name") or last in NAMED_FIELDS


def numeric(field: str) -> bool:
    last = field.rsplit(".", maxsplit=1)[-1]
    return field.startswith("rules.") or last in NUMBER_FIELDS or last.endswith(("_count", "_epochs", "_ap", "_max", "_min"))


def template_counts() -> list[Count]:
    found: list[Count] = []
    for path in sorted(TEMPLATES.rglob("*.j2")):
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for field, word in TEMPLATE_COUNT.findall(line):
                if plural(word) and not named(field):
                    found.append(Count(path, line_number, f"{{{{ {field} }}}} {word}"))
    return found


def main() -> int:
    source = {path: path.read_text(encoding="utf-8") for path in sorted(SOURCE.rglob("*.py"))}
    tests = {path: path.read_text(encoding="utf-8") for path in sorted(TESTS.rglob("*.py"))}
    misfilled = formatted({**source, **tests}, spec_templates(source))
    for item in misfilled:
        print(f"{item.path.relative_to(ROOT)}:{item.line}: {item.text} cannot read a {{count:one|many}} template; fill it with fill()")
    found = counts(source) + on_screen(screens()) + template_counts()
    for item in found:
        where = f"{item.path.relative_to(ROOT)}:{item.line}"
        print(f"{where}: '{item.text}' reads wrong for a count of one; count through several() and agree(), or plural() and agree() on screen")
    print(f"count words: {len(found) + len(misfilled)}")
    return 1 if found or misfilled else 0


if __name__ == "__main__":
    sys.exit(main())
