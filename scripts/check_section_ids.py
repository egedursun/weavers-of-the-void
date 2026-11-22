import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend" / "src"
SECTION_ID = re.compile(r"""(?:\bid=\{?|\bsection:\s*)['"](section-[a-z0-9-]+)['"]""")
NODE_PAGES = re.compile(r"<(EntityView|WorldWikiView|StarWikiView|GalaxyView|ClusterView|DimensionView|SonPage|ForeignGodPage|CreatorPage)\b")
PANE = FRONTEND / "features" / "atlas"


def owners() -> dict[str, set[str]]:
    found: dict[str, set[str]] = defaultdict(set)
    for path in sorted(FRONTEND.rglob("*.ts*")):
        if ".test." in path.name or "generated" in path.parts:
            continue
        for match in SECTION_ID.finditer(path.read_text(encoding="utf-8")):
            found[match.group(1)].add(str(path.relative_to(ROOT)))
    return found


def main() -> int:
    problems = [
        f"{section} is the id of a section in {', '.join(sorted(files))}; a jump lands on whichever comes first"
        for section, files in owners().items()
        if len(files) > 1
    ]
    problems += [
        f"{path.relative_to(ROOT)}: the atlas renders a node page behind the drawer; a node is shown only in its drawer"
        for path in sorted(PANE.rglob("*.tsx"))
        if ".test." not in path.name and NODE_PAGES.search(path.read_text(encoding="utf-8"))
    ]
    print("\n".join(problems))
    print(f"section ids: {len(problems)}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
