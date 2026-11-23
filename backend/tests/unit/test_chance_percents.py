import ast
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[2] / "src" / "aerona"
PERCENT_NAMES = frozenset({"PERCENT", "_PERCENT"})
PERCENT_SUFFIXES = ("_pct", "_chance")

SAMPLE = """
def roll(ctx, table):
    first = ctx.rng("a").chance(table.raid_pct / PERCENT)
    second = ctx.rng("b").chance(ctx.rules.convoys.stranded_pct)
    third = ctx.rng("c").chance(table.harm_pct * density / PERCENT)
    return first, second, third
"""


def rule_name(node: ast.expr) -> str:
    if isinstance(node, ast.Attribute):
        return node.attr
    return node.id if isinstance(node, ast.Name) else ""


def fractions(tree: ast.AST) -> list[int]:
    found: list[int] = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "chance" and len(node.args) == 1):
            continue
        argument = node.args[0]
        if (
            isinstance(argument, ast.BinOp)
            and isinstance(argument.op, ast.Div)
            and rule_name(argument.right) in PERCENT_NAMES
            and rule_name(argument.left).endswith(PERCENT_SUFFIXES)
        ):
            found.append(node.lineno)
    return found


def test_a_percent_rule_shrunk_to_a_fraction_before_a_chance_is_flagged() -> None:
    assert fractions(ast.parse(SAMPLE)) == [3]


def test_every_chance_takes_its_percent_whole() -> None:
    flagged = [
        f"{path.relative_to(SOURCE_ROOT)}:{line}" for path in sorted(SOURCE_ROOT.rglob("*.py")) for line in fractions(ast.parse(path.read_text(), str(path)))
    ]
    assert flagged == [], f"chance() takes a percent; these pass a percent rule divided down to a fraction, so the roll almost never succeeds: {flagged}"
