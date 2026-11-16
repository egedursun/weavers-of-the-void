import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "backend" / "src" / "aerona"
MODEL_FACING = ("agents/context", "prompts/contexts", "tools")
RAW_VALUE = re.compile(r"\{([A-Za-z_][A-Za-z0-9_.()\[\]]*)\.value\}")


def raw_values(text: str) -> list[str]:
    return [match.group(1) for match in RAW_VALUE.finditer(text)]


def main() -> int:
    found = 0
    for folder in MODEL_FACING:
        for path in sorted((PACKAGE / folder).rglob("*.py")):
            for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                for name in raw_values(line):
                    print(f"{path.relative_to(ROOT)}:{line_number}: {name}.value reaches the model as a raw key; write it through spoken()")
                    found += 1
    print(f"model enum text: {found}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
