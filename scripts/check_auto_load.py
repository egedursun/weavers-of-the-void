import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE_ROOTS = (ROOT / "frontend" / "src",)
SHARED_HOOK = ROOT / "frontend" / "src" / "hooks" / "useAutoLoad.ts"
OWN_OBSERVER = re.compile(r"new IntersectionObserver\(")
NEXT_PAGE = re.compile(r"\bfetchNextPage\b")
SWAPPED_PLACEHOLDER = re.compile(r"isFetchingNextPage\s*&&\s*\(?\s*<Skeleton")


def sources() -> list[Path]:
    return sorted(
        path
        for root in SOURCE_ROOTS
        if root.exists()
        for path in [*root.rglob("*.ts"), *root.rglob("*.tsx")]
        if "node_modules" not in path.parts and ".test." not in path.name and path != SHARED_HOOK
    )


def problems_in(text: str) -> list[str]:
    found: list[str] = []
    if NEXT_PAGE.search(text) and OWN_OBSERVER.search(text):
        found.append(
            "loads the next page from its own IntersectionObserver; one whose effect depends on the loader is rebuilt after"
            " every page and loads the next at once while the sentinel stays in view. Use useAutoLoad from hooks/useAutoLoad."
        )
    if SWAPPED_PLACEHOLDER.search(text):
        found.append(
            "swaps a placeholder in while the next page loads, so the list jumps on every page. Keep the control in place"
            " and show that it is loading."
        )
    return found


def main() -> int:
    problems = [f"{path.relative_to(ROOT)} {problem}" for path in sources() for problem in problems_in(path.read_text(encoding="utf-8"))]
    for problem in problems:
        print(problem)
    print(f"auto load: {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
