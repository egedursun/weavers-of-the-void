import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend" / "src"
WRAPPED = re.compile(r"className=['\"][^'\"]*\bflex-wrap\b[^'\"]*['\"][^>]*>\s*\{\(?([A-Za-z_][\w.?\[\]]*)\)?\.map\(")
PAGED_MARKS = ("visible", "shown")
LOADER = re.compile(r"const (\w+) = useCallback\(\(\) => \{?[^}]*fetchNextPage")


@dataclass(frozen=True)
class Unpaged:
    path: Path
    line: int
    source: str


def bounded(source: str) -> bool:
    tail = source.rsplit(".", maxsplit=1)[-1].split("?", maxsplit=1)[0]
    constant = source.replace("_", "").replace(".", "").isupper()
    return constant or tail.endswith("Values") or any(mark in source for mark in PAGED_MARKS)


def scroll_only(text: str) -> bool:
    if "IntersectionObserver" not in text or "fetchNextPage" not in text:
        return False
    loaders = {"fetchNextPage", *LOADER.findall(text)}
    return not any(re.search(rf"onClick=\{{(\(\) => )?(void )?{name}\b", text) for name in loaders)


def unpaged_in(path: Path) -> list[Unpaged]:
    text = path.read_text(encoding="utf-8")
    found = [Unpaged(path, text.count("\n", 0, match.start()) + 1, match.group(1)) for match in WRAPPED.finditer(text) if not bounded(match.group(1))]
    if scroll_only(text):
        found.append(Unpaged(path, text.count("\n", 0, text.index("IntersectionObserver")) + 1, "fetchNextPage"))
    elif "IntersectionObserver" in text and "fetchNextPage" in text and "cancelRefetch: false" not in text:
        found.append(Unpaged(path, text.count("\n", 0, text.index("fetchNextPage")) + 1, "fetchNextPage twice"))
    return found


def sources() -> list[Path]:
    return sorted(path for path in FRONTEND.rglob("*.tsx") if ".test." not in path.name and "generated" not in path.parts)


def main() -> int:
    found = [item for path in sources() for item in unpaged_in(path)]
    for item in found:
        reasons = {
            "fetchNextPage": "loads older pages only on scroll; give it a show-more button too",
            "fetchNextPage twice": "is called by scroll and by a button; pass cancelRefetch: false so one page is never asked for twice",
        }
        reason = reasons.get(item.source, "is drawn in full in a wrapping row; page it with PagedList or useShowMore")
        print(f"{item.path.relative_to(ROOT)}:{item.line}: {item.source} {reason}")
    print(f"unpaged lists: {len(found)}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
