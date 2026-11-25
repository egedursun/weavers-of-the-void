import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "frontend" / "src"
STYLES = SOURCE / "styles"
MARKUP_SUFFIXES = (".ts", ".tsx")
SKIPPED_AT_RULES = ("@layer", "@keyframes", "@font-face", "@theme", "@utility", "@property", "@custom-variant", "@plugin")
UTILITY_PROPERTIES: dict[str, str] = {
    **{name: "position" for name in ("static", "fixed", "absolute", "relative", "sticky")},
    **{
        name: "display"
        for name in ("block", "inline-block", "inline", "flex", "inline-flex", "grid", "inline-grid", "hidden", "contents", "table", "flow-root")
    },
    **{name: "isolation" for name in ("isolate", "isolation-auto")},
    **{f"overflow{axis}-{value}": "overflow" for axis in ("", "-x", "-y") for value in ("auto", "hidden", "clip", "visible", "scroll")},
}
WATCHED = frozenset(UTILITY_PROPERTIES.values())
LITERAL = re.compile(r"'([^'\n]*)'|\"([^\"\n]*)\"|`([^`$]*)`")
DECLARATION = re.compile(r"(?:^|;)\s*([a-z-]+)\s*:")
SUBJECT_CLASSES = re.compile(r"\.([A-Za-z_][\w-]*)")


@dataclass(frozen=True)
class Override:
    path: Path
    line: int
    custom: str
    utility: str
    prop: str


def watched_properties(body: str) -> set[str]:
    found: set[str] = set()
    for name in DECLARATION.findall(body):
        root = "overflow" if name.startswith("overflow") else name
        if root in WATCHED:
            found.add(root)
    return found


def subject_classes(selector: str) -> set[str]:
    classes: set[str] = set()
    for part in selector.split(","):
        compounds = re.split(r"[\s>+~]+", part.strip())
        subject = compounds[-1] if compounds else ""
        if "::" not in subject:
            classes.update(SUBJECT_CLASSES.findall(subject))
    return classes


def unlayered_rules(text: str) -> list[tuple[str, str]]:
    rules: list[tuple[str, str]] = []
    position = 0
    while position < len(text):
        opening = text.find("{", position)
        if opening < 0:
            break
        head = text[position:opening].strip().split(";")[-1].strip()
        depth, cursor = 1, opening + 1
        while cursor < len(text) and depth:
            depth += {"{": 1, "}": -1}.get(text[cursor], 0)
            cursor += 1
        body = text[opening + 1 : cursor - 1]
        if head.startswith(SKIPPED_AT_RULES):
            pass
        elif head.startswith("@"):
            rules.extend(unlayered_rules(body))
        elif "{" in body:
            rules.extend(unlayered_rules(body))
            rules.append((head, body[: body.find("{")]))
        else:
            rules.append((head, body))
        position = cursor
    return rules


def custom_properties(styles: Path = STYLES) -> dict[str, set[str]]:
    found: dict[str, set[str]] = defaultdict(set)
    for path in sorted(styles.rglob("*.css")):
        for selector, body in unlayered_rules(path.read_text(encoding="utf-8")):
            props = watched_properties(body)
            for name in subject_classes(selector) if props else ():
                found[name] |= props
    return dict(found)


def utility_property(token: str) -> str | None:
    return UTILITY_PROPERTIES.get(token.rsplit(":", maxsplit=1)[-1].lstrip("!"))


def findings(root: Path = SOURCE, styles: Path = STYLES) -> list[Override]:
    customs = custom_properties(styles)
    found: list[Override] = []
    for path in sorted(root.rglob("*")):
        if path.suffix not in MARKUP_SUFFIXES or not path.is_file() or ".test." in path.name or "generated" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        for match in LITERAL.finditer(text):
            tokens = next(group for group in match.groups() if group is not None).split()
            line = text.count("\n", 0, match.start()) + 1
            for custom in (token for token in tokens if token in customs):
                for token in tokens:
                    prop = utility_property(token)
                    if prop is not None and prop in customs[custom]:
                        found.append(Override(path, line, custom, token, prop))
    return found


def main() -> int:
    found = findings()
    for item in found:
        print(
            f"{item.path.relative_to(ROOT)}:{item.line}: the unlayered class {item.custom} sets {item.prop}, so it overrides "
            f"the utility {item.utility} on the same element; set {item.prop} in one place only"
        )
    print(f"css overrides: {len(found)}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
