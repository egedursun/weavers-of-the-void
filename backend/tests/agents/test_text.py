from aerona.agents.text import (
    clean_fate_note,
    epoch_mentions,
    extract_word,
    replace_name,
    sanitize,
    shorten_rationale,
    strip_meta_sentences,
    without_engine_prefix,
)


def test_extract_word_prefers_guillemets_then_label() -> None:
    assert extract_word("I made them. «Salt remembers.» Done.") == "Salt remembers."
    assert extract_word('Thinking...\nWord: "The sea is mine"') == "The sea is mine"
    assert extract_word("no word here") == ""


def test_sanitize_removes_game_marks() -> None:
    text = "[thread#4] The son#3 Ithren raised thread#7's banner (#795) (P7) ★★"
    assert sanitize(text) == "The Ithren raised a story's banner"


def test_fate_note_drops_internal_reasoning_and_shortens() -> None:
    note = clean_fate_note("PRE-SCREEN warning ignored. However the salt holds; it is bound to the river.")
    assert note == "The salt holds; it is bound to the river."
    assert shorten_rationale("one two three four five six seven eight", 4) == "One two three four…"


def test_meta_sentences_names_and_prefix() -> None:
    assert strip_meta_sentences("Fate rewrote this record. It stands.") == "It stands."
    assert replace_name("Ilva met Ilvane at Ilva's gate.", "Ilva", "Orra", ("Ilvane",)) == "Orra met Ilvane at Orra's gate."
    assert without_engine_prefix("[World engine] A tale.") == "A tale."


def test_epoch_mentions_count_only_age_numbers() -> None:
    assert epoch_mentions("In Age 3 the salt rose; in Age 4 it fell. 900 souls sang, 1.5 tides.", 10) == 2
