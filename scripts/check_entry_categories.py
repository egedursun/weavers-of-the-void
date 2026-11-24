import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend" / "src"
REGISTRY = FRONTEND / "components" / "layout" / "entry" / "entryCategories.ts"
ENTRY_PAGES = FRONTEND / "config" / "entryPages.ts"
STYLES = FRONTEND / "styles" / "chrome.css"
SCANNED = (FRONTEND / "features", FRONTEND / "config", FRONTEND / "components" / "domain", FRONTEND / "components" / "layout")
SECTION_LITERAL = re.compile(r"""['"`](section-[a-z0-9_-]+)['"`]""")
REGISTERED = re.compile(r"""^\s*'(section-[a-z0-9_-]+)':\s*'([a-z]+)',?$""", re.MULTILINE)
CATEGORY_KEY = re.compile(r"""key:\s*'([a-z]+)'""")
IMPORTS = re.compile(r"""(?:from|import\()\s*['"]([^'"]+)['"]""")
SECTION_TAG = re.compile(r"<Section\b(.*?)>", re.DOTALL)


def registry() -> tuple[dict[str, list[str]], set[str]]:
    text = REGISTRY.read_text(encoding="utf-8")
    entries: dict[str, list[str]] = {}
    for section, category in REGISTERED.findall(text):
        entries.setdefault(section, []).append(category)
    return entries, set(CATEGORY_KEY.findall(text))


def literals() -> dict[str, str]:
    found: dict[str, str] = {}
    for folder in SCANNED:
        for path in sorted(folder.rglob("*.ts*")):
            if ".test." in path.name or path == REGISTRY:
                continue
            for section in SECTION_LITERAL.findall(path.read_text(encoding="utf-8")):
                found.setdefault(section, str(path.relative_to(ROOT)))
    return found


def resolve(spec: str, origin: Path) -> Path | None:
    if spec.startswith("@/"):
        base = FRONTEND / spec[2:]
    elif spec.startswith("."):
        base = (origin.parent / spec).resolve()
    else:
        return None
    return next((path for path in (base.with_suffix(".tsx"), base.with_suffix(".ts"), base / "index.ts", base / "index.tsx") if path.is_file()), None)


def reachable() -> set[Path]:
    seen: set[Path] = set()
    todo = [ENTRY_PAGES]
    while todo:
        path = todo.pop()
        if path in seen:
            continue
        seen.add(path)
        for spec in IMPORTS.findall(path.read_text(encoding="utf-8")):
            found = resolve(spec, path)
            if found is not None and "generated" not in found.parts and ".test." not in found.name:
                todo.append(found)
    return seen


def anonymous_sections() -> list[str]:
    problems: list[str] = []
    for path in sorted(reachable()):
        if path.suffix != ".tsx" or path.is_relative_to(FRONTEND / "components" / "ui"):
            continue
        text = path.read_text(encoding="utf-8")
        for match in SECTION_TAG.finditer(text):
            if not re.search(r"\bid=", match.group(1)):
                line = text[: match.start()].count("\n") + 1
                problems.append(f"{path.relative_to(ROOT)}:{line}: a section an entry page renders has no id, so the entry window cannot place or reach it")
    return problems


def problems() -> list[str]:
    entries, categories = registry()
    used = literals()
    found = [f"{section} is placed in {len(kinds)} categories; give it exactly one" for section, kinds in sorted(entries.items()) if len(kinds) > 1]
    found += [f"{section} names a category '{kinds[0]}' the entry window does not have" for section, kinds in sorted(entries.items()) if kinds[0] not in categories]
    found += [f"{section} ({path}) belongs to no category of the entry window; add it to entryCategories.ts" for section, path in sorted(used.items()) if section not in entries]
    found += [f"{section} is in entryCategories.ts but no screen uses it any more" for section in sorted(entries) if section not in used]
    styles = STYLES.read_text(encoding="utf-8")
    found += [f"the category '{key}' has no filter rule in chrome.css, so choosing it hides nothing" for key in sorted(categories) if f"[data-entry-filter='{key}']" not in styles]
    return found + anonymous_sections()


def main() -> int:
    found = problems()
    for problem in found:
        print(problem)
    print(f"entry categories: {len(found)} problem(s)")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
