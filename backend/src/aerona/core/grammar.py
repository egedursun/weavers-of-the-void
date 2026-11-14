from string import Formatter
from typing import Any

VOWELS = "aeiou"
ARTICLE_SPECS = {"an": False, "An": True}


VOWEL_NUMBER_PREFIXES = ("11", "18")
VOWEL_NUMBER_LENGTHS = frozenset({2, 5, 8})


def sounds_like_vowel(word: str) -> bool:
    digits = len(word) - len(word.lstrip("0123456789"))
    if digits:
        return word.startswith("8") or (word.startswith(VOWEL_NUMBER_PREFIXES) and digits in VOWEL_NUMBER_LENGTHS)
    return word[:1].lower() in VOWELS


def an(noun: object, *, capital: bool = False) -> str:
    word = str(noun)
    article = "an" if sounds_like_vowel(word) else "a"
    return f"{article.capitalize() if capital else article} {word}"


UNCHANGED_PLURALS = frozenset({"species", "series", "news", "means", "remains", "arms", "goods", "thanks", "data", "kin", "folk", "cosmos", "chaos"})
IRREGULAR_ENDINGS = (
    ("lives", "life"),
    ("wives", "wife"),
    ("knives", "knife"),
    ("wolves", "wolf"),
    ("halves", "half"),
    ("selves", "self"),
    ("crises", "crisis"),
    ("theses", "thesis"),
    ("oases", "oasis"),
    ("analyses", "analysis"),
    ("prostheses", "prosthesis"),
    ("biases", "bias"),
    ("statuses", "status"),
    ("viruses", "virus"),
    ("bonuses", "bonus"),
    ("censuses", "census"),
)
PLURAL_ENDINGS = (("ies", "y"), ("sses", "ss"), ("shes", "sh"), ("ches", "ch"), ("xes", "x"), ("zzes", "zz"), ("oes", "o"))


def singular(plural: str) -> str:
    head, _, last = plural.rpartition(" ")
    lead = f"{head} " if head else ""
    if last in UNCHANGED_PLURALS or last.endswith(("ss", "us", "is")):
        return plural
    for ending, replacement in (*IRREGULAR_ENDINGS, *PLURAL_ENDINGS):
        if last.endswith(ending):
            return lead + last.removesuffix(ending) + replacement
    return lead + last.removesuffix("s")


def agree(count: int | None, one: str, many: str) -> str:
    return one if count == 1 else many


def several(count: int | None, one: str, many: str) -> str:
    if count is None:
        return f"an unknown number of {many}"
    return f"{count} {agree(count, one, many)}"


class ArticleFormatter(Formatter):
    def format_field(self, value: Any, format_spec: str) -> str:
        if format_spec in ARTICLE_SPECS:
            return an(str(value), capital=ARTICLE_SPECS[format_spec])
        if "|" in format_spec and isinstance(value, int):
            one, many = format_spec.split("|", 1)
            return several(value, one, many)
        formatted: str = super().format_field(value, format_spec)
        return formatted


ARTICLES = ArticleFormatter()


def fill(template: str, **fields: object) -> str:
    return ARTICLES.format(template, **fields)
