import json
import sys
from pathlib import Path
from typing import Any

from weasyprint import HTML
from weasyprint.document import Document

MEASURE = "measure"
PRINT = "print"
MEASURE_ARGUMENTS = 4
PRINT_ARGUMENTS = 5


def bookmarks(document: Document) -> list[list[Any]]:
    return [[level, label, number, place[0], place[1]] for number, page in enumerate(document.pages) for level, label, place, *_state in page.bookmarks]


def laid_out(document: Document) -> dict[str, Any]:
    return {
        "pages": len(document.pages),
        "heights": [page.height for page in document.pages],
        "anchors": {name: [number, place[0], place[1]] for number, page in enumerate(document.pages) for name, place in page.anchors.items()},
        "bookmarks": bookmarks(document),
    }


def render(source: Path) -> Document:
    return HTML(filename=str(source), base_url=str(source.parent)).render(presentational_hints=True)


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == MEASURE and len(sys.argv) == MEASURE_ARGUMENTS:
        document = render(Path(sys.argv[2]))
        Path(sys.argv[3]).write_text(json.dumps(laid_out(document)))
        return 0
    if mode == PRINT and len(sys.argv) == PRINT_ARGUMENTS:
        document = render(Path(sys.argv[2]))
        document.write_pdf(sys.argv[3], optimize_images=False)
        Path(sys.argv[4]).write_text(json.dumps(laid_out(document)))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
