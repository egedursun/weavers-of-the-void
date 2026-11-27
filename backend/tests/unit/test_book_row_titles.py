import re
from pathlib import Path

from aerona.services import books

FILLER = re.compile(r"""or ['"](?:no one|nobody)['"]""")


def test_a_book_title_leaves_out_a_missing_person_instead_of_naming_no_one() -> None:
    found = [
        f"{path.name}:{number}"
        for path in Path(books.__file__).parent.glob("*.py")
        for number, line in enumerate(path.read_text().splitlines(), 1)
        if FILLER.search(line)
    ]
    assert found == []
