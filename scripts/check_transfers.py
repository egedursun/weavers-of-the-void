import ast
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "backend" / "src" / "aerona"
HELPER = "move_amount"


@dataclass(frozen=True)
class Transfer:
    path: Path
    line: int
    function: str
    column: str
    payer: str
    payee: str


def augmented(function: ast.AST) -> tuple[dict[tuple[str, str], list[ast.AugAssign]], dict[tuple[str, str], list[ast.AugAssign]]]:
    taken: dict[tuple[str, str], list[ast.AugAssign]] = {}
    given: dict[tuple[str, str], list[ast.AugAssign]] = {}
    for node in ast.walk(function):
        if not isinstance(node, ast.AugAssign) or not isinstance(node.target, ast.Attribute):
            continue
        key = (node.target.attr, ast.dump(node.value))
        if isinstance(node.op, ast.Sub):
            taken.setdefault(key, []).append(node)
        elif isinstance(node.op, ast.Add):
            given.setdefault(key, []).append(node)
    return taken, given


def owner(node: ast.AugAssign) -> str:
    target = node.target
    return ast.unparse(target.value) if isinstance(target, ast.Attribute) else ""


def scan(path: Path) -> list[Transfer]:
    found: list[Transfer] = []
    for function in ast.walk(ast.parse(path.read_text())):
        if not isinstance(function, ast.FunctionDef | ast.AsyncFunctionDef) or function.name == HELPER:
            continue
        taken, given = augmented(function)
        for key, debits in taken.items():
            for debit in debits:
                credit = next((node for node in given.get(key, []) if owner(node) != owner(debit)), None)
                if credit is not None:
                    found.append(Transfer(path, debit.lineno, function.name, key[0], owner(debit), owner(credit)))
                    break
    return found


def main() -> int:
    findings = [finding for path in sorted(SOURCE.rglob("*.py")) for finding in scan(path)]
    for finding in findings:
        print(
            f"{finding.path.relative_to(ROOT)}:{finding.line}: {finding.function} moves {finding.column} from {finding.payer} to {finding.payee} by hand;"
            f" use {HELPER} so a locked or held side never creates or destroys the amount"
        )
    if findings:
        print(f"{len(findings)} hand-written transfer(s)")
        return 1
    print("transfers: every two-sided amount moves through move_amount")
    return 0


if __name__ == "__main__":
    sys.exit(main())
