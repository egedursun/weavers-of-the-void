import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "backend" / "src" / "aerona"
REGISTRY = SOURCE / "rules" / "registry"
YEARLY = re.compile(r"\(% per year\)|\bper year\b|\beach year\b|\bin a year\b|\ba year\b", re.IGNORECASE)
PARTS_OF_A_YEAR = re.compile(
    r"share of a year|days in a year|a year's|young a year|months of ice a year|yearly happenings|per year of adult life", re.IGNORECASE
)
SCALED = re.compile(r"per_epoch|over_epoch|\.epochs\(|epoch_chance|years_per_epoch|world_years|EPOCH_YEARS|epochs_in|sampled_years")
OUTSIDE_ENGINE = ("rules/", "api/", "services/", "tools/", "agents/")


@dataclass(frozen=True)
class UnscaledRead:
    path: Path
    line: int
    table: str
    name: str
    description: str


def table_names(init: str) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for node in ast.walk(ast.parse(init)):
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and isinstance(node.annotation, ast.Name):
            found.setdefault(node.annotation.id, []).append(node.target.id)
    return found


def yearly_rules(registry: dict[Path, str], tables: dict[str, list[str]]) -> dict[tuple[str, str], str]:
    found: dict[tuple[str, str], str] = {}
    for text in registry.values():
        for table in ast.walk(ast.parse(text)):
            if not isinstance(table, ast.ClassDef):
                continue
            for item in table.body:
                if not (isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name) and isinstance(item.value, ast.Call)):
                    continue
                if getattr(item.value.func, "id", "") not in {"rule", "span"}:
                    continue
                words = [part.value for part in item.value.args if isinstance(part, ast.Constant) and isinstance(part.value, str)]
                if words and YEARLY.search(words[-1]) and not PARTS_OF_A_YEAR.search(words[-1]):
                    for name in tables.get(table.name, []):
                        found[(name, item.target.id)] = words[-1]
    return found


def rule_tables(function: ast.FunctionDef | ast.AsyncFunctionDef) -> dict[str, str]:
    found: dict[str, str] = {}
    for node in ast.walk(function):
        if (
            isinstance(node, ast.Assign)
            and isinstance(node.value, ast.Attribute)
            and isinstance(node.value.value, ast.Attribute)
            and node.value.value.attr == "rules"
        ):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    found[target.id] = node.value.attr
    return found


def table_of(base: ast.expr, tables: dict[str, str]) -> str | None:
    if isinstance(base, ast.Attribute) and isinstance(base.value, ast.Attribute) and base.value.attr == "rules":
        return base.attr
    if isinstance(base, ast.Name):
        return tables.get(base.id)
    return None


def unscaled_reads(files: dict[Path, str], yearly: dict[tuple[str, str], str]) -> list[UnscaledRead]:
    found: list[UnscaledRead] = []
    for path, text in files.items():
        for function in ast.walk(ast.parse(text)):
            if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if SCALED.search(ast.get_source_segment(text, function) or ""):
                continue
            tables = rule_tables(function)
            for node in ast.walk(function):
                if not (isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Load)):
                    continue
                table = table_of(node.value, tables)
                if table is not None and (table, node.attr) in yearly:
                    found.append(UnscaledRead(path, node.lineno, table, node.attr, yearly[(table, node.attr)]))
    return found


def engine_files() -> dict[Path, str]:
    files: dict[Path, str] = {}
    for path in sorted(SOURCE.rglob("*.py")):
        if not path.relative_to(SOURCE).as_posix().startswith(OUTSIDE_ENGINE):
            files[path] = path.read_text(encoding="utf-8")
    return files


def main() -> int:
    tables = table_names((REGISTRY / "__init__.py").read_text(encoding="utf-8"))
    yearly = yearly_rules({path: path.read_text(encoding="utf-8") for path in sorted(REGISTRY.glob("*.py"))}, tables)
    found = unscaled_reads(engine_files(), yearly)
    for item in found:
        where = f"{item.path.relative_to(ROOT)}:{item.line}: rules.{item.table}.{item.name}"
        print(f"{where} is a yearly rule ({item.description}) read where nothing turns it into an epoch; scale it or say what it is counted by")
    print(f"unscaled yearly rules: {len(found)}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
