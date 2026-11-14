import re
from pathlib import Path

import aerona

SOURCE = Path(aerona.__file__).resolve().parent
TAGS = re.compile(r"(\{%(?:(?!%\}).)*%\}\s*)+")
OLD_LEDGER = (
    "{% for entry in book.ledger %}\n- **Epoch {{ entry.epoch }}.** {{ entry.actor_name }}{% if entry.undone %} *(undone)*{% endif %}\n{% endfor %}\n---\n"
)


def glued_lines(text: str) -> list[int]:
    lines = text.split("\n")
    found = []
    for index, line in enumerate(lines[:-1]):
        stripped = line.strip()
        if not stripped.endswith("%}") or TAGS.fullmatch(stripped) or stripped.startswith(("}", "]")) or '{{ "\\n" }}' in stripped:
            continue
        follower = index + 1
        closes_macro = False
        while follower < len(lines) and TAGS.fullmatch(lines[follower].strip() or "-"):
            closes_macro = closes_macro or "endmacro" in lines[follower]
            follower += 1
        trimmed = follower < len(lines) and lines[index + 1].lstrip().startswith("{%-")
        if not closes_macro and not trimmed and follower < len(lines) and lines[follower].strip():
            found.append(index + 1)
    return found


def test_no_template_line_loses_its_line_end_to_a_closing_tag() -> None:
    glued = [
        f"{path.relative_to(SOURCE)}:{number}"
        for path in sorted(SOURCE.rglob("*.j2"))
        if not path.name.endswith(".html.j2")
        for number in glued_lines(path.read_text())
    ]
    assert not glued, "a line ending in a block tag loses its line end under trim_blocks; leave a blank line after it:\n" + "\n".join(glued)


def test_the_guard_finds_the_ledger_line_that_ran_into_the_next() -> None:
    assert glued_lines(OLD_LEDGER) == [2]
