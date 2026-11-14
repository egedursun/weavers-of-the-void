import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
THEME = ROOT / "frontend" / "src" / "styles" / "theme.css"
UTILS = ROOT / "frontend" / "src" / "lib" / "utils.ts"


TOKEN_SHAPES = {"spacing": "[a-z0-9-]+", "text": "[a-z]+"}


def declared(theme: str, prefix: str) -> set[str]:
    return set(re.findall(rf"--{prefix}-({TOKEN_SHAPES[prefix]}):", theme))


def listed(utils: str, name: str) -> set[str]:
    block = re.search(rf"export const {name} = \[(.*?)\]", utils, re.S)
    return set(re.findall(r"'([a-z0-9-]+)'", block.group(1))) if block else set()


def gaps(theme: str, utils: str) -> list[str]:
    found: list[str] = []
    for prefix, name in (("spacing", "SPACING_TOKENS"), ("text", "TEXT_ROLES")):
        tokens, known = declared(theme, prefix), listed(utils, name)
        found.extend(f"--{prefix}-{token} is in the theme but not in {name}" for token in sorted(tokens - known))
        found.extend(f"{name} lists {token}, which the theme does not declare" for token in sorted(known - tokens))
    return found


def main() -> int:
    found = gaps(THEME.read_text(encoding="utf-8"), UTILS.read_text(encoding="utf-8"))
    for item in found:
        print(f"frontend/src/lib/utils.ts: {item}; class merging drops classes it does not know")
    print(f"theme tokens: {len(found)} gap(s)")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
