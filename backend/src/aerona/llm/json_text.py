import json
from typing import Any

JSON_OPENERS = ("{", "[")


def first_json_value(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    decoder = json.JSONDecoder()
    for index, character in enumerate(text):
        if character not in JSON_OPENERS:
            continue
        try:
            value, _ = decoder.raw_decode(text, index)
        except json.JSONDecodeError:
            continue
        return value
    raise json.JSONDecodeError("no JSON value in the text", text, 0)
