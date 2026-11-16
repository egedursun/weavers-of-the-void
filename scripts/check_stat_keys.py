import importlib
import inspect
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "backend" / "src" / "aerona"

STAT_CALL = re.compile(
    r"\b(?:stat|stat_or|shift_stat|set_stat)\(\s*[\w.\[\]]+\s*,\s*\"([a-z_]+)\""
)


def known_keys() -> set[str]:
    sys.path.insert(0, str(ROOT / "backend" / "src"))
    entity_stats = importlib.import_module("aerona.domain.models.entity_stats")
    base = importlib.import_module("pydantic").BaseModel
    return {
        name
        for value in vars(entity_stats).values()
        if inspect.isclass(value) and issubclass(value, base)
        for name in value.model_fields
    }


def unknown_keys(text: str, keys: set[str]) -> list[str]:
    return [
        match.group(1)
        for match in STAT_CALL.finditer(text)
        if match.group(1) not in keys
    ]


def main() -> int:
    keys = known_keys()
    found = 0
    for path in sorted(PACKAGE.rglob("*.py")):
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            for key in unknown_keys(line, keys):
                print(
                    f"{path.relative_to(ROOT)}:{line_number}: no thing holds a stat named {key}; read the column or profile that holds it"
                )
                found += 1
    print(f"stat keys: {found}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
