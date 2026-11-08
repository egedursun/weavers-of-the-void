import re
from pathlib import Path

from aerona.engine.primitives.words import names_word

ENGINE = Path(__file__).resolve().parents[2] / "src" / "aerona" / "engine"
SUBSTRING_SCAN = re.compile(r"any\((\w+) in (?:text|name|label|title|body|subtype|lowered)\w* for \1 in")


def test_a_word_matches_whole_words_and_their_plurals_only() -> None:
    assert names_word("The Great Play", ("play",))
    assert not names_word("The Great Play", ("lay",))
    assert names_word("songs of the hill", ("song",))
    assert names_word("a War Dance", ("war dance",))
    assert not names_word("scarf", ("scar",))
    assert not names_word("", ("song",))


def test_the_engine_never_finds_a_name_by_a_word_hidden_inside_another() -> None:
    found = [
        f"{path.relative_to(ENGINE)}:{number}"
        for path in sorted(ENGINE.rglob("*.py"))
        for number, line in enumerate(path.read_text().splitlines(), 1)
        if SUBSTRING_SCAN.search(line)
    ]
    assert found == [], f"use names_word from engine/primitives/words.py: {found}"
