import ast
import sys
from pathlib import Path

from aerona.catalog.invariants import GENERIC, TYPED, GenericCheck
from aerona.services.integrity.invariants import CHECKS, coverage, every_table

ROOT = Path(__file__).resolve().parent.parent
TESTS = ROOT / "backend" / "tests" / "services" / "integrity" / "test_every_invariant.py"


def broken_in_tests() -> set[str]:
    tree = ast.parse(TESTS.read_text()) if TESTS.exists() else ast.Module(body=[], type_ignores=[])
    for node in ast.walk(tree):
        targets = node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, ast.AnnAssign) else []
        named = any(isinstance(target, ast.Name) and target.id == "BREAKERS" for target in targets)
        value = getattr(node, "value", None)
        if named and isinstance(value, ast.Dict):
            return {key.value for key in value.keys if isinstance(key, ast.Constant) and isinstance(key.value, str)}
    return set()


def main() -> int:
    problems: list[str] = []
    covered = coverage()
    tables = every_table()
    problems += [f"table {name} has no row in catalog/invariants.py" for name in tables if not covered.get(name)]
    problems += [f"invariant {spec.key} names table {spec.table}, which does not exist" for spec in TYPED if spec.table not in tables]
    problems += [f"invariant {spec.key} has no check in services/integrity/invariants.py" for spec in TYPED if spec.key not in CHECKS]
    problems += [f"check {key} has no invariant in catalog/invariants.py" for key in CHECKS if key not in {spec.key for spec in TYPED}]
    problems += [f"generic check {check.value} has no text" for check in GenericCheck if check not in GENERIC]
    tested = broken_in_tests()
    problems += [f"invariant {spec.key} is never broken in {TESTS.relative_to(ROOT)}" for spec in TYPED if spec.key not in tested]
    for problem in problems:
        print(problem)
    print(f"integrity coverage: {len(problems)} gap(s) over {len(tables)} tables")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
