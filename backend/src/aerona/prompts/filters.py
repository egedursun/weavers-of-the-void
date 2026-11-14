from collections.abc import Iterable, Sequence

from aerona.core.grammar import an, several
from aerona.domain.enums.world import LoreLanguage
from aerona.prompts.budget import ELLIPSIS, BudgetSection, budget, sectioned_budget
from aerona.prompts.data.deepening import special_section
from aerona.prompts.data.labels import COUNT_WORDS, DEGREE_BANDS, LORE_LANGUAGE_NAMES, MOOD_LEVELS

PERCENT = 100
STAR_GLYPH = "★"
TEEN_ORDINALS = range(11, 14)
ORDINAL_SUFFIXES = {1: "st", 2: "nd", 3: "rd"}


def mood_level(value: float) -> str:
    index = int(value * len(MOOD_LEVELS) // PERCENT)
    return MOOD_LEVELS[max(0, min(len(MOOD_LEVELS) - 1, index))]


def degree(value: float, adjective: str) -> str:
    for threshold, template in DEGREE_BANDS:
        if value >= threshold:
            return template.format(adjective=adjective)
    return DEGREE_BANDS[-1][1].format(adjective=adjective)


def share_of(base: float, percent: float) -> int:
    return max(1, round(base * percent / PERCENT))


def percent_complement(percent: float) -> int:
    return round(PERCENT - percent)


def ratio(value: float, decimals: int = 1) -> str:
    return f"{value / PERCENT:.{decimals}f}"


def stars(count: int) -> str:
    return STAR_GLYPH * max(0, count)


def count_word(count: int) -> str:
    return COUNT_WORDS[count] if 0 <= count < len(COUNT_WORDS) else str(count)


def cut(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[:limit] + ELLIPSIS


def cut_at_word(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    head = text[:limit]
    boundary = head.rfind(" ")
    return (head[:boundary] if boundary > 0 else head).rstrip() + ELLIPSIS


def language_name(language: LoreLanguage) -> str:
    return LORE_LANGUAGE_NAMES[language]


def offered(available: Sequence[str] | None, clauses: Iterable[tuple[str, str]]) -> list[str]:
    return [text for tool, text in clauses if available is None or tool in available]


def budget_text(text: str, limit: int, hint: str, trim_min: int) -> str:
    return budget(text, limit, hint, trim_min)


def sectioned(sections: Iterable[tuple[str, int, str]], limit: int, trim_min: int) -> str:
    return sectioned_budget([BudgetSection(text, floor, hint) for text, floor, hint in sections], limit, trim_min)


def fair_shares(lengths: Sequence[int], total: int) -> list[int]:
    order = sorted(range(len(lengths)), key=lambda index: lengths[index])
    shares = [0] * len(lengths)
    remaining = total
    for position, index in enumerate(order):
        share = min(lengths[index], remaining // (len(order) - position))
        shares[index] = share
        remaining -= share
    return shares


def ordinal(number: int) -> str:
    if number % 100 in TEEN_ORDINALS:
        return f"{number}th"
    return f"{number}{ORDINAL_SUFFIXES.get(number % 10, 'th')}"


def signed(value: int) -> str:
    return f"+{value}" if value > 0 else str(value)


FILTERS = {
    "an": an,
    "several": several,
    "mood_level": mood_level,
    "degree": degree,
    "share_of": share_of,
    "percent_complement": percent_complement,
    "ratio": ratio,
    "stars": stars,
    "count_word": count_word,
    "cut": cut,
    "cut_at_word": cut_at_word,
    "language_name": language_name,
    "signed": signed,
    "ordinal": ordinal,
}

GLOBALS = {
    "offered": offered,
    "budget": budget_text,
    "sectioned": sectioned,
    "fair_shares": fair_shares,
    "special_section": special_section,
}
