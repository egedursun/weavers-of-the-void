import sys
from pathlib import Path

from weasyprint import HTML

ARGUMENTS = 3


def main() -> int:
    if len(sys.argv) != ARGUMENTS:
        return 2
    source, target = Path(sys.argv[1]), Path(sys.argv[2])
    HTML(filename=str(source), base_url=str(source.parent)).write_pdf(str(target), optimize_images=False, presentational_hints=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
