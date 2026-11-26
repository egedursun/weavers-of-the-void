import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE_ROOT = ROOT / "frontend" / "src"
CSS_RULE = re.compile(r"([^{}]+)\{([^{}]*)\}")
CSS_FIXED = re.compile(r"background(-attachment)?\s*:[^;]*\bfixed\b")
APPLY_FIXED = re.compile(r"@apply[^;]*(?<![\w-])bg-fixed(?![\w-])")
CLASS_FIXED = re.compile(r"(?<![\w-])bg-fixed(?![\w-])")
STYLE_FIXED = re.compile(r"backgroundAttachment\s*:\s*['\"`][^'\"`]*\bfixed\b")


def sources(suffixes: tuple[str, ...]) -> list[Path]:
    if not SOURCE_ROOT.exists():
        return []
    return sorted(path for path in SOURCE_ROOT.rglob("*") if path.suffix in suffixes and "node_modules" not in path.parts and "generated" not in path.parts)


def fixed_in_css(css: str) -> list[str]:
    found: list[str] = []
    for selectors, body in CSS_RULE.findall(re.sub(r"/\*.*?\*/", "", css, flags=re.S)):
        if CSS_FIXED.search(body) or APPLY_FIXED.search(body):
            found.append(" ".join(selectors.split()).split("}")[-1].strip())
    return found


def fixed_in_markup(code: str) -> list[int]:
    return [number for number, line in enumerate(code.splitlines(), start=1) if CLASS_FIXED.search(line) or STYLE_FIXED.search(line)]


def problems() -> list[str]:
    found = [f"{path.relative_to(ROOT)}: {selector}" for path in sources((".css",)) for selector in fixed_in_css(path.read_text(encoding="utf-8"))]
    found.extend(f"{path.relative_to(ROOT)}:{line}" for path in sources((".ts", ".tsx")) for line in fixed_in_markup(path.read_text(encoding="utf-8")))
    return found


def main() -> int:
    found = problems()
    for problem in found:
        print(
            f"{problem} pins a background to the viewport with background-attachment: fixed."
            " The browser then repaints the whole screen on every scrolled frame, so scrolling stutters."
            " Paint the background on a position: fixed layer instead (see body::before in styles/chrome.css)."
        )
    print(f"fixed backgrounds: {len(found)} problem(s)")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
