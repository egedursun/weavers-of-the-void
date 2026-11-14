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
TEMPLATE = re.compile(r"\{(count|total|n)\} ([a-z][a-z-]*)")
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


def counting(node: ast.expr) -> bool:
    if isinstance(node, ast.Call):
        return isinstance(node.func, ast.Name) and node.func.id == "len"
    if isinstance(node, ast.Name):
        return node.id in COUNT_NAMES or node.id.endswith("_count")
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
    return found


def counted_by(node: ast.expr) -> bool:
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
    return [f"{{{name}}} {word}" for name, word in TEMPLATE.findall(node.value) if plural(word)]


def counts(files: dict[Path, str]) -> list[Count]:
    found: list[Count] = []
    for path, text in files.items():
        tree = ast.parse(text)
        joined_parts = {id(value) for node in ast.walk(tree) if isinstance(node, ast.JoinedStr) for value in node.values}
        for node in ast.walk(tree):
            if isinstance(node, ast.JoinedStr):
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


def main() -> int:
    source = {path: path.read_text(encoding="utf-8") for path in sorted(SOURCE.rglob("*.py"))}
    tests = {path: path.read_text(encoding="utf-8") for path in sorted(TESTS.rglob("*.py"))}
    misfilled = formatted({**source, **tests}, spec_templates(source))
    for item in misfilled:
        print(f"{item.path.relative_to(ROOT)}:{item.line}: {item.text} cannot read a {{count:one|many}} template; fill it with fill()")
    found = counts(source) + on_screen(screens())
    for item in found:
        where = f"{item.path.relative_to(ROOT)}:{item.line}"
        print(f"{where}: '{item.text}' reads wrong for a count of one; count through several() and agree(), or plural() and agree() on screen")
    print(f"count words: {len(found) + len(misfilled)}")
    return 1 if found or misfilled else 0


if __name__ == "__main__":
    sys.exit(main())
