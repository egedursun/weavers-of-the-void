import ast
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "backend" / "src" / "aerona"
TESTS = ROOT / "backend" / "tests"
TOWN_NAMES = frozenset({"town", "home", "capital", "settlement", "city", "port", "seat"})
SETTLEMENT_MARK = "EntityType.SETTLEMENT"
OTHER_KINDS = ("EntityType.MORTAL", "EntityType.FACTION", "EntityType.ARMY", "EntityType.TITLE", "EntityType.CULT", "mortal_role")


@dataclass(frozen=True)
class Raw:
    path: Path
    line: int
    text: str
    reason: str


def affiliation(node: ast.AST) -> bool:
    return isinstance(node, ast.Attribute) and node.attr == "affiliated_entity_id"


def town_affiliations(tree: ast.AST) -> Iterator[ast.Attribute]:
    for node in ast.walk(tree):
        if affiliation(node) and isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id in TOWN_NAMES:
            yield node


def settlement_queries(tree: ast.AST) -> Iterator[ast.AST]:
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "where"):
            continue
        text = ast.unparse(node)
        townish = SETTLEMENT_MARK in text or ("people" in text and not any(kind in text for kind in OTHER_KINDS))
        for inner in ast.walk(node):
            if townish and affiliation(inner) and isinstance(inner, ast.Attribute) and isinstance(inner.value, ast.Name) and inner.value.id == "EntityRow":
                yield inner


def raw_links(files: dict[Path, str]) -> list[Raw]:
    found: set[Raw] = set()
    for path, text in files.items():
        tree = ast.parse(text)
        found |= {Raw(path, node.lineno, ast.unparse(node), "reads a town's people from its affiliation") for node in town_affiliations(tree)}
        found |= {Raw(path, node.lineno, ast.unparse(node), "finds the towns of a people by affiliation") for node in settlement_queries(tree)}
    return sorted(found, key=lambda item: (str(item.path), item.line))


def main() -> int:
    found = raw_links({path: path.read_text(encoding="utf-8") for root in (SOURCE, TESTS) for path in sorted(root.rglob("*.py")) if path.name != "test_town_people.py"})
    for item in found:
        print(
            f"{item.path.relative_to(ROOT)}:{item.line}: {item.text} {item.reason}; a settlement holds its people by a homeland bond, "
            "use people_of or towns_of_people"
        )
    print(f"raw town-people links: {len(found)}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
