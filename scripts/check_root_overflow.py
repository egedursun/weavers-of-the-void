import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STYLE_ROOTS = (ROOT / "frontend" / "src",)
RULE = re.compile(r"([^{}]+)\{([^{}]*)\}")
ROOT_SELECTOR = re.compile(r"^(html|:root)([.:\[][^\s>+~]*)?$")
CLIPPING = re.compile(r"overflow(-[xy])?\s*:\s*(hidden|clip|scroll|auto)|@apply[^;]*\boverflow(-[xy])?-(hidden|clip|scroll|auto)\b")


def stylesheets() -> list[Path]:
    return sorted(path for root in STYLE_ROOTS if root.exists() for path in root.rglob("*.css") if "node_modules" not in path.parts)


def clipped_roots(css: str) -> list[str]:
    found: list[str] = []
    for selectors, body in RULE.findall(re.sub(r"/\*.*?\*/", "", css, flags=re.S)):
        roots = [item.strip() for item in selectors.split(",") if ROOT_SELECTOR.match(item.strip())]
        if roots and CLIPPING.search(body):
            found.extend(roots)
    return found


def main() -> int:
    problems = [f"{path.relative_to(ROOT)}: {selector}" for path in stylesheets() for selector in clipped_roots(path.read_text(encoding="utf-8"))]
    for problem in problems:
        print(
            f"{problem} sets an overflow on the root element. A Radix dialog or menu locks scrolling by hiding the body's overflow,"
            " which then no longer reaches the viewport, so the sticky top bar scrolls away. Set it on body instead."
        )
    print(f"root overflow: {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
