import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend" / "src"
SECTION_ID = re.compile(r"""(?:\bid=\{?|\bsection:\s*|\bsectionId=\{?)['"](section-[a-z0-9_-]+)['"]""")
NODE_PAGES = re.compile(r"<(EntityView|WorldWikiView|StarWikiView|GalaxyView|ClusterView|DimensionView|SonPage|ForeignGodPage|CreatorPage)\b")
ENTRY_PAGES = FRONTEND / "config" / "entryPages.ts"
PAGE_IMPORT = re.compile(r"import\('@/([^']+)'\)")


def owners() -> dict[str, set[str]]:
    found: dict[str, set[str]] = defaultdict(set)
    for path in sorted(FRONTEND.rglob("*.ts*")):
        if ".test." in path.name or "generated" in path.parts:
            continue
        for match in SECTION_ID.finditer(path.read_text(encoding="utf-8")):
            found[match.group(1)].add(str(path.relative_to(ROOT)))
    return found


def page_files() -> set[Path]:
    found: set[Path] = set()
    for spec in PAGE_IMPORT.findall(ENTRY_PAGES.read_text(encoding="utf-8")):
        base = FRONTEND / spec
        found |= {path for path in (base.with_suffix(".tsx"), base.with_suffix(".ts")) if path.is_file()}
    return found


def duplicated_pages() -> list[str]:
    pages = page_files()
    return [
        f"{path.relative_to(ROOT)}: renders a node page outside the entry window; a node is shown only in its entry window"
        for path in sorted(FRONTEND.rglob("*.tsx"))
        if ".test." not in path.name and path not in pages and NODE_PAGES.search(path.read_text(encoding="utf-8"))
    ]


def main() -> int:
    problems = [
        f"{section} is the id of a section in {', '.join(sorted(files))}; a jump lands on whichever comes first"
        for section, files in owners().items()
        if len(files) > 1
    ]
    problems += duplicated_pages()
    print("\n".join(problems))
    print(f"section ids: {len(problems)}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
