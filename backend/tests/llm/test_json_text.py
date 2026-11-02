import json

import pytest

from aerona.llm.json_text import first_json_value


def test_plain_json_is_parsed_as_a_whole() -> None:
    assert first_json_value('{"name": "Aral"}') == {"name": "Aral"}


def test_the_first_json_block_is_taken_from_free_text() -> None:
    text = 'Here is the record:\n```json\n{"name": "Aral", "power": 30}\n```\nThat is all.'
    assert first_json_value(text) == {"name": "Aral", "power": 30}


def test_a_broken_opener_is_skipped_for_the_next_value() -> None:
    assert first_json_value("{oops [1, 2, 3] tail") == [1, 2, 3]


def test_text_without_json_raises() -> None:
    with pytest.raises(json.JSONDecodeError):
        first_json_value("no structure here")
