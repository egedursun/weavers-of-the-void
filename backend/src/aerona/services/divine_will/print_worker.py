import importlib
import sys
from pathlib import Path

EMBEDDED_ONLY = ("data",)
ARGUMENTS = 3
PRINTER = "weasyprint"
FETCHERS = "weasyprint.urls"


def main() -> int:
    if len(sys.argv) != ARGUMENTS:
        return 2
    printer, fetchers = importlib.import_module(PRINTER), importlib.import_module(FETCHERS)
    source, target = Path(sys.argv[1]), Path(sys.argv[2])
    document = printer.HTML(string=source.read_text(encoding="utf-8"), url_fetcher=fetchers.URLFetcher(allowed_protocols=EMBEDDED_ONLY))
    document.write_pdf(str(target))
    return 0


if __name__ == "__main__":
    sys.exit(main())
