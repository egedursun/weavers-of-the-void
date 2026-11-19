import hashlib
from typing import Any

from aerona.core.random import RandomKey, SeededRandom

ORDER_STREAM = "schema.order"


def order_for(text: str) -> SeededRandom:
    return SeededRandom(RandomKey(0, 0, f"{ORDER_STREAM}/{hashlib.blake2b(text.encode('utf-8'), digest_size=8).hexdigest()}"))


def unordered(node: Any, rng: SeededRandom) -> Any:
    if isinstance(node, dict):
        mixed = {key: unordered(value, rng) for key, value in node.items()}
        choices = node.get("enum")
        if isinstance(choices, list) and all(isinstance(item, str) for item in choices):
            mixed["enum"] = rng.shuffled(choices)
        return mixed
    if isinstance(node, list):
        return [unordered(item, rng) for item in node]
    return node
