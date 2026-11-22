import ast
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "backend" / "src" / "aerona"
HOMES = frozenset(
    {"catalog/movement.py", "catalog/terrain.py", "engine/environment/profile.py"}
)
SKIPPED = ("db/alembic/", "catalog/kinds/")
ENUM = "CalendarSlot"


@dataclass(frozen=True)
class Special:
    path: str
    line: int
    text: str


def aliases_of(tree: ast.Module) -> set[str]:
    names = {ENUM}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            names.update(
                alias.asname or alias.name for alias in node.names if alias.name == ENUM
            )
        if (
            isinstance(node, ast.Assign)
            and isinstance(node.value, ast.Name)
            and node.value.id in names
        ):
            names.update(
                target.id for target in node.targets if isinstance(target, ast.Name)
            )
    return names


def is_member(node: ast.AST, names: set[str]) -> bool:
    if isinstance(node, ast.Attribute) and node.attr == "value":
        node = node.value
    return (
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id in names
        and node.attr.isupper()
    )


def specials_in(relative: str, text: str) -> list[Special]:
    tree = ast.parse(text)
    names = aliases_of(tree)
    found: list[Special] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and any(
            is_member(side, names) for side in (node.left, *node.comparators)
        ):
            found.append(Special(relative, node.lineno, ast.unparse(node)))
        if (
            isinstance(node, ast.Set | ast.List | ast.Tuple)
            and sum(is_member(item, names) for item in node.elts) >= 2
        ):
            found.append(Special(relative, node.lineno, ast.unparse(node)))
    return found


def special_cases() -> list[Special]:
    found: list[Special] = []
    for path in sorted(SOURCE.rglob("*.py")):
        relative = str(path.relative_to(SOURCE))
        if relative in HOMES or relative.startswith(SKIPPED):
            continue
        text = path.read_text(encoding="utf-8")
        if ENUM in text:
            found.extend(specials_in(relative, text))
    return sorted(set(found), key=lambda item: (item.path, item.line))


def main() -> int:
    found = special_cases()
    for item in found:
        print(
            f"backend/src/aerona/{item.path}:{item.line}: {item.text} special-cases a calendar slot outside the slot catalogue; "
            "ask slot_open in engine/lore/calendar_slots.py or read SLOTS in catalog/calendar_slots.py"
        )
    print(f"calendar slot special cases: {len(found)}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
