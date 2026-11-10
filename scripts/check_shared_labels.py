import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend" / "src"
SHARED_ROOT = FRONTEND / "features" / "entity" / "sections" / "ThingSections.tsx"
GENERIC = ("Name", "Kind", "Type")
LABELLED = re.compile(r"""\b(?:label|aria-label)=['"](%s)['"]""" % "|".join(GENERIC))
LABEL_TEXT = re.compile(r"<Label\b[^>]*>\s*(%s)\s*</Label>" % "|".join(GENERIC))
IMPORTED = re.compile(r"""from ['"]((?:@/|\./|\.\./)[^'"]+)['"]""")


@dataclass(frozen=True)
class Generic:
    path: Path
    line: int
    label: str


def resolved(base: Path, spec: str) -> Path | None:
    stem = FRONTEND / spec[2:] if spec.startswith("@/") else (base.parent / spec).resolve()
    for candidate in (stem.with_suffix(".tsx"), stem.with_suffix(".ts"), stem / "index.tsx", stem / "index.ts"):
        if candidate.exists():
            return candidate
    return None


def shared_files() -> list[Path]:
    seen: set[Path] = set()
    queue = [SHARED_ROOT]
    while queue:
        path = queue.pop()
        if path in seen:
            continue
        seen.add(path)
        for spec in IMPORTED.findall(path.read_text(encoding="utf-8")):
            found = resolved(path, spec)
            if found is not None and found.is_relative_to(FRONTEND / "features") and found.suffix == ".tsx" and ".test." not in found.name:
                queue.append(found)
    return sorted(seen)


def generics_in(path: Path) -> list[Generic]:
    text = path.read_text(encoding="utf-8")
    found = [Generic(path, text.count("\n", 0, match.start()) + 1, match.group(1)) for match in LABELLED.finditer(text)]
    found += [Generic(path, text.count("\n", 0, match.start()) + 1, match.group(1)) for match in LABEL_TEXT.finditer(text)]
    return found


def main() -> int:
    found = [item for path in shared_files() for item in generics_in(path)]
    for item in found:
        print(
            f"{item.path.relative_to(ROOT)}:{item.line}: the field label '{item.label}' is drawn in every node drawer and clashes with the "
            "drawer's own fields; name what it is"
        )
    print(f"shared labels: {len(found)}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
