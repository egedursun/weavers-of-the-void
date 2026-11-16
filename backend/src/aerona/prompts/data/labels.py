from aerona.domain.enums.world import LoreLanguage

LORE_LANGUAGE_NAMES: dict[LoreLanguage, str] = {
    LoreLanguage.ENGLISH: "English",
    LoreLanguage.TURKISH: "Turkish",
}

MOOD_LEVELS: tuple[str, ...] = ("almost none", "low", "moderate", "high", "near its peak")

DEGREE_BANDS: tuple[tuple[float, str], ...] = (
    (80, "very {adjective}"),
    (60, "{adjective}"),
    (40, "moderately {adjective}"),
    (20, "slightly {adjective}"),
    (0, "hardly {adjective} at all"),
)

COUNT_WORDS: tuple[str, ...] = (
    "none",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "eleven",
    "twelve",
    "thirteen",
    "fourteen",
    "fifteen",
)
