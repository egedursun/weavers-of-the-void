import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend" / "src"
RAW_ID = re.compile(r"`#\$\{[A-Za-z_.?]*_id\}")
SEARCH_ONLY = "keywords"


def raw_ids_in(text: str) -> list[int]:
    return [index for index, line in enumerate(text.splitlines(), start=1) if RAW_ID.search(line) and SEARCH_ONLY not in line]


def main() -> int:
    found = [
        f"{path.relative_to(ROOT)}:{line}: a record is shown by its raw number; name it or say what it is"
        for path in sorted(FRONTEND.rglob("*.tsx"))
        if ".test." not in path.name and "generated" not in path.parts
        for line in raw_ids_in(path.read_text(encoding="utf-8"))
    ]
    print("\n".join(found))
    print(f"raw ids: {len(found)}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
