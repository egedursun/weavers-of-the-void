import re
import unicodedata
from collections.abc import Callable, Sequence

WORD = re.compile(r"[^\W_]+")
EXACT = 2
PHRASE_BONUS = 3


def folded(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def words(text: str) -> list[str]:
    return WORD.findall(folded(text))


def score(query: str, fields: Sequence[tuple[str, int]]) -> int:
    wanted = words(query)
    if not wanted:
        return 0
    prepared = [(set(words(text)), folded(text), weight) for text, weight in fields]
    total = 0
    for word in wanted:
        best = 0
        for found, whole, weight in prepared:
            if word in found:
                best = max(best, weight * EXACT)
            elif word in whole:
                best = max(best, weight)
        total += best
    phrase = folded(query).strip()
    if len(wanted) > 1 and any(phrase in whole for _, whole, _ in prepared):
        total += PHRASE_BONUS * len(wanted)
    return total


def ranked[ItemT](query: str, items: Sequence[ItemT], fields: Callable[[ItemT], Sequence[tuple[str, int]]]) -> list[ItemT]:
    if not words(query):
        return list(items)
    scored = [(score(query, fields(item)), index, item) for index, item in enumerate(items)]
    return [item for _, _, item in sorted((entry for entry in scored if entry[0] > 0), key=lambda entry: (-entry[0], entry[1]))]
