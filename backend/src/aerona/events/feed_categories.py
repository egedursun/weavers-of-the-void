import re
from types import MappingProxyType

from aerona.domain.enums.chronicle import FeedCategory

TEMPLATE_SEPARATOR = "."

TEMPLATE_PREFIX_CATEGORIES: MappingProxyType[str, FeedCategory] = MappingProxyType(
    {
        "travel": FeedCategory.VOYAGE,
        "journey": FeedCategory.VOYAGE,
        "migration": FeedCategory.VOYAGE,
        "exploration": FeedCategory.VOYAGE,
        "routes": FeedCategory.GATE,
        "gate": FeedCategory.GATE,
        "horror": FeedCategory.LEAK,
        "leak": FeedCategory.LEAK,
        "war": FeedCategory.WAR,
        "warfare": FeedCategory.WAR,
        "campaigns": FeedCategory.WAR,
        "siege": FeedCategory.WAR,
        "tribute": FeedCategory.WAR,
        "prisoners": FeedCategory.WAR,
        "disasters": FeedCategory.DISASTER,
        "climate": FeedCategory.DISASTER,
        "plague": FeedCategory.DISASTER,
        "sky": FeedCategory.SKY,
        "stars": FeedCategory.SKY,
        "births": FeedCategory.LIFE,
        "mortals": FeedCategory.LIFE,
        "death": FeedCategory.LIFE,
        "aging": FeedCategory.LIFE,
        "succession": FeedCategory.LIFE,
        "creatures": FeedCategory.LIFE,
        "heroes": FeedCategory.LIFE,
        "civilization": FeedCategory.CIVILIZATION,
        "society": FeedCategory.CIVILIZATION,
        "trade": FeedCategory.CIVILIZATION,
        "factions": FeedCategory.CIVILIZATION,
        "diplomacy": FeedCategory.CIVILIZATION,
    }
)

TEXT_STEMS: tuple[tuple[FeedCategory, tuple[str, ...]], ...] = (
    (FeedCategory.VOYAGE, ("ship", "voyage", "expedition", "set out", "arrived", "stowaway", "caravan", "migrated", "colony")),
    (FeedCategory.GATE, ("gate", "seal", "bridge", "route", "path opened", "pass", "slingshot")),
    (FeedCategory.LEAK, ("leak", "outer being", "void", "sanity", "madness", "clouded", "forbidden knowledge", "whisper")),
    (FeedCategory.WAR, ("war", "battle", "siege", "army", "conquered", "plunder", "raid")),
    (FeedCategory.DISASTER, ("flood", "earthquake", "plague", "epidemic", "drought", "storm", "famine", "disaster")),
    (FeedCategory.SKY, ("eclipse", "comet", "star", "sky", "moon", "alignment", "meteor")),
    (FeedCategory.LIFE, ("was born", "died", "death", "aged", "heir", "resurrected", "domesticated", "chimera", "mutation")),
    (FeedCategory.CIVILIZATION, ("tier", "federation", "independent", "empire", "kingdom", "trade")),
)

WORD_START = r"(?<![^\W_])"
WORD_END = r"(?:s|es|d|ed|ing)?(?![^\W_])"

TEXT_PATTERNS: tuple[tuple[FeedCategory, re.Pattern[str]], ...] = tuple(
    (category, re.compile(WORD_START + "(?:" + "|".join(re.escape(stem) for stem in stems) + ")" + WORD_END, re.IGNORECASE)) for category, stems in TEXT_STEMS
)


def category_for_template(template_key: str | None) -> FeedCategory | None:
    if not template_key:
        return None
    prefix = template_key.split(TEMPLATE_SEPARATOR, 1)[0]
    return TEMPLATE_PREFIX_CATEGORIES.get(prefix)


def category_for_text(text: str) -> FeedCategory:
    for category, pattern in TEXT_PATTERNS:
        if pattern.search(text):
            return category
    return FeedCategory.WORLD


def feed_category(template_key: str | None, text: str) -> FeedCategory:
    return category_for_template(template_key) or category_for_text(text)
