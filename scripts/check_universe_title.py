import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOOKS = ROOT / "backend" / "src" / "aerona" / "services" / "books"
TITLED = (*sorted((BOOKS / "templates").glob("*.j2")), ROOT / "backend" / "src" / "aerona" / "api" / "routers" / "books.py")
WORLD_NAME = "cosmos.name"


def misnamed(text: str) -> list[int]:
    return [number for number, line in enumerate(text.splitlines(), start=1) if WORLD_NAME in line]


def main() -> int:
    problems = [f"{path.relative_to(ROOT)}:{line}" for path in TITLED for line in misnamed(path.read_text(encoding="utf-8"))]
    for problem in problems:
        print(
            f"{problem} titles the book with cosmos.name, which is the first world's name."
            " Use book.title in a template and universe_title() in code: the universe is named in the library."
        )
    print(f"universe title: {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
