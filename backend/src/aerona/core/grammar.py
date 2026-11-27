import re
from enum import Enum
from functools import cache
from string import Formatter
from typing import Any

VOWELS = "aeiou"
ARTICLE_SPECS = {"an": False, "An": True}
PERCENT_SPEC = "%"


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


def plural(noun: str) -> str:
    if " of " in noun:
        head, rest = noun.split(" of ", 1)
        return f"{plural(head)} of {rest}"
    head, _, last = noun.rpartition(" ")
    lead = f"{head} " if head else ""
    for many, one in IRREGULAR_ENDINGS:
        if last.endswith(one):
            return lead + last.removesuffix(one) + many
    if last in UNCHANGED_PLURALS or (last.endswith("s") and not last.endswith(("ss", "us", "is"))):
        return noun
    if last.endswith("y") and last[-2:-1] not in VOWELS:
        return lead + last.removesuffix("y") + "ies"
    if last.endswith(("ss", "sh", "ch", "x", "z")):
        return lead + last + "es"
    return lead + last + "s"


def agree(count: int | None, one: str, many: str) -> str:
    return one if count == 1 else many


def several(count: int | None, one: str, many: str) -> str:
    if count is None:
        return f"an unknown number of {many}"
    return f"{count} {agree(count, one, many)}"


NUMBER_TEXT = re.compile(r"-?\d+(\.\d+)?")


COUNTED_FORMS = 3
SPANS = frozenset({"epoch", "age", "year", "season", "month", "round", "day", "hour", "generation"})
COUNT_MARK = "#"
OPTIONAL_MARK = "?"


class ArticleFormatter(Formatter):
    def format_field(self, value: Any, format_spec: str) -> str:
        if format_spec.startswith(OPTIONAL_MARK):
            text = format(value, "")
            return format_spec[len(OPTIONAL_MARK) :].replace(COUNT_MARK, text) if text.strip() else ""
        if format_spec in ARTICLE_SPECS or format_spec == PERCENT_SPEC:
            return f"{value}%" if format_spec == PERCENT_SPEC else an(str(value), capital=ARTICLE_SPECS[format_spec])
        if "|" in format_spec and isinstance(value, str) and NUMBER_TEXT.fullmatch(value.strip()):
            value = float(value)
        if "|" in format_spec and isinstance(value, (int, float)) and not isinstance(value, bool):
            return counted(int(value) if float(value).is_integer() else value, format_spec)
        formatted: str = super().format_field(value, format_spec)
        return formatted


def counted(count: float, format_spec: str) -> str:
    forms = format_spec.split("|")
    if len(forms) == COUNTED_FORMS:
        none, one, many = forms
        return (none if count == 0 else one if count == 1 else many).replace(COUNT_MARK, str(count))
    one, many = format_spec.split("|", 1)
    if count == 0:
        return f"less than one {one}" if one in SPANS else f"no {many}"
    return f"{count} {agree(1 if count == 1 else 0, one, many)}"


ARTICLES = ArticleFormatter()


def fill(template: str, **fields: object) -> str:
    return ARTICLES.format(template, **fields)


ORDINAL_WORDS = ("First", "Second", "Third", "Fourth", "Fifth", "Sixth", "Seventh", "Eighth", "Ninth", "Tenth")
ORDINAL_SUFFIXES = {1: "st", 2: "nd", 3: "rd"}
TEEN_LOW = 11
TEEN_HIGH = 13
HUNDRED = 100
TEN = 10


def ordinal_word(number: int) -> str:
    if 1 <= number <= len(ORDINAL_WORDS):
        return ORDINAL_WORDS[number - 1]
    if TEEN_LOW <= number % HUNDRED <= TEEN_HIGH:
        return f"{number}th"
    return f"{number}{ORDINAL_SUFFIXES.get(number % TEN, 'th')}"


AGE_NEUTRAL: dict[tuple[str, str], str] = {
    ("VeteranGrant", "none"): "no grant",
    ("MortalRole", "scribe"): "clerk",
    ("DangerSource", "volcanic"): "volcanic ground",
    ("MovementMode", "boat"): "by boat",
    ("MovementMode", "wheeled"): "on wheels",
    ("DangerSource", "avalanche"): "avalanches",
    ("SocialClass", "scribe"): "clerk",
    ("SocialClass", "serf_or_slave"): "bonded",
    ("OrderLabour", "serf"): "tied to the land",
    ("ClergyFunction", "scribe"): "clerk",
    ("ServitorRole", "scribe"): "keeper of accounts",
    ("Profession", "smith"): "metalworker",
    ("SkillKind", "smithing"): "metalworking",
    ("ProcessKind", "smithing"): "metalworking",
    ("WorkshopKind", "scriptorium"): "copying house",
    ("MethodKind", "scriptorium"): "copying house",
    ("CourtLevel", "guild"): "trade court",
    ("FactionKind", "craft_guild"): "craft association",
    ("FactionKind", "merchant_guild"): "trade association",
    ("FactionKind", "thieves_guild"): "thieves' ring",
    ("FactionKind", "peasant_league"): "farmers' league",
    ("OwnerClass", "guild"): "craft association",
    ("HeraldryHolderKind", "guild"): "association",
    ("SociolectKind", "guild"): "trade",
    ("TitleTier", "guild"): "association",
    ("JurisdictionClaim", "guild"): "association",
    ("LawKind", "guild_charter"): "association charter",
    ("StructureKind", "guildhall"): "trade hall",
    ("StructureKind", "alchemist_lab"): "reagent laboratory",
    ("PeaceTermKind", "throne"): "rule",
    ("StepAction", "crown"): "raise to rule",
    ("WorkshopKind", "alchemist"): "chemical works",
    ("Technique", "guilds"): "craft associations",
    ("OathBreach", "the_throne_was_seized"): "rule was seized",
    ("CoupCause", "a_subject_turned_their_power_base_on_the_throne"): "a subject turned their power base on the ruler",
    ("CoupCause", "the_marshal_turned_the_army_on_the_throne"): "the marshal turned the army on the ruler",
    ("CoupCause", "the_regent_took_the_crown"): "the regent took power",
    ("GodGoalKind", "hold_thrones"): "hold thrones of power",
    ("GatheringKind", "coronation"): "accession",
    ("CollectionKind", "coronation"): "accession",
    ("DivinationQuestion", "coronation"): "accession",
    ("EngineKind", "coronation"): "accession",
    ("ItemDeed", "coronation"): "accession",
    ("GuestRole", "crowned"): "new ruler",
    ("EntryBarrier", "guild_right"): "chartered right",
    ("RuleMaker", "guild"): "trade association",
}


def fact_word(enum_name: str | None, value: str) -> str:
    return AGE_NEUTRAL.get((enum_name or "", value), value.replace("_", " "))


def spoken(value: object) -> str:
    if isinstance(value, Enum):
        return spoken_member(value)
    raw = str(getattr(value, "value", value))
    return fact_word(type(value).__name__, raw) if hasattr(value, "value") else raw.replace("_", " ")


@cache
def spoken_member(member: Enum) -> str:
    return fact_word(type(member).__name__, str(member.value))
