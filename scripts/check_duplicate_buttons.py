import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "frontend" / "src"
COMPONENT = re.compile(r"^(?:export )?function [A-Z]\w*\(", re.MULTILINE)
STEP_LABEL = re.compile(r"<StepButton\b(?:=>|[^>])*?label=['\"]([^'\"]+)['\"]", re.DOTALL)
BUTTON_TEXT = re.compile(
    r"<Button\b(?:=>|[^>])*>\s*(?:<[A-Z]\w*\s*/>\s*)?([A-Za-z][^<{}]*?)\s*</Button>",
    re.DOTALL,
)


def components(text: str) -> list[tuple[str, str]]:
    starts = [match.start() for match in COMPONENT.finditer(text)]
    return [(text[start : text.index("(", start)], text[start:end]) for start, end in zip(starts, [*starts[1:], len(text)], strict=False)]


def duplicates(body: str) -> list[str]:
    labels = STEP_LABEL.findall(body) + [label.strip() for label in BUTTON_TEXT.findall(body)]
    return sorted(label for label, count in Counter(labels).items() if count > 1)


def main() -> int:
    found = 0
    for path in sorted(ROOT.rglob("*.tsx")):
        if ".test." in path.name:
            continue
        for name, body in components(path.read_text(encoding="utf-8")):
            for label in duplicates(body):
                print(
                    f"{path.relative_to(ROOT.parent.parent)}: {name.removeprefix('export ').removeprefix('function ')} shows two buttons named '{label}'; name each action for what it does"
                )
                found += 1
    print(f"duplicate buttons: {found}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
