import ast
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "backend" / "src" / "aerona"
REALM_WORDS = ("realm", "polity")


@dataclass(frozen=True)
class Raw:
    path: Path
    line: int
    text: str


def names_a_realm(node: ast.AST) -> bool:
    if isinstance(node, ast.Name):
        return any(word in node.id for word in REALM_WORDS)
    if isinstance(node, ast.Attribute):
        return any(word in node.attr for word in REALM_WORDS) or (node.attr == "id" and names_a_realm(node.value))
    return False


def party_field(node: ast.AST) -> bool:
    return isinstance(node, ast.Attribute) and node.attr == "party_node_id" and isinstance(node.value, ast.Name) and node.value.id == "TreatyPartyRow"


def raw_parties(files: dict[Path, str]) -> list[Raw]:
    found: set[Raw] = set()
    for path, text in files.items():
        for node in ast.walk(ast.parse(text)):
            if isinstance(node, ast.Compare) and party_field(node.left) and any(names_a_realm(item) for item in node.comparators):
                found.add(Raw(path, node.lineno, ast.unparse(node)))
    return sorted(found, key=lambda item: (str(item.path), item.line))


def main() -> int:
    found = raw_parties({path: path.read_text(encoding="utf-8") for path in sorted(SOURCE.rglob("*.py"))})
    for item in found:
        print(
            f"{item.path.relative_to(ROOT)}:{item.line}: {item.text} looks for a realm among treaty parties; a realm signs through its core "
            "community, use signatories_of and realm_of_party"
        )
    print(f"raw treaty parties: {len(found)}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
