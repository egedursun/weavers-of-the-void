ERROR_REASON_CHARS = 160
SESSION_ERROR_CHARS = 120
TOOL_RESULT_CHARS = 400
WORD_CHRONICLE_CHARS = 900
MORTAL_WORD_CHRONICLE_CHARS = 600
INSPIRATION_SUMMARY_CHARS = 200
CHRONICLER_NAME_CHARS = 80
CHRONICLER_IDENTITY_CHARS = 240
AGE_NAME_ORDINALS = ("Second", "Third", "Fourth", "Fifth")
ENGINE_DESCRIPTION_PREFIX = "[World engine]"
LEGACY_U_DIAERESIS = 0xFC
LEGACY_ENGINE_DESCRIPTION_PREFIX = f"[D{chr(LEGACY_U_DIAERESIS)}nya motoru]"
CREATOR_PSEUDO_SON_ID = 0
SMALL_REGION_RATIO = 0.75
LARGE_REGION_RATIO = 1.25
TIC_MIN_WORD_LETTERS = 4
TIC_STEM_LETTERS = 5
COMMON_WORDS = frozenset(
    {
        "about",
        "after",
        "again",
        "against",
        "also",
        "always",
        "among",
        "another",
        "because",
        "been",
        "before",
        "being",
        "between",
        "both",
        "came",
        "come",
        "could",
        "down",
        "each",
        "even",
        "ever",
        "every",
        "from",
        "have",
        "here",
        "into",
        "just",
        "know",
        "like",
        "made",
        "make",
        "many",
        "more",
        "most",
        "much",
        "must",
        "never",
        "nothing",
        "once",
        "only",
        "other",
        "over",
        "same",
        "shall",
        "should",
        "since",
        "some",
        "still",
        "such",
        "than",
        "that",
        "their",
        "them",
        "then",
        "there",
        "these",
        "they",
        "thing",
        "this",
        "those",
        "through",
        "till",
        "time",
        "under",
        "until",
        "upon",
        "very",
        "want",
        "were",
        "what",
        "when",
        "where",
        "which",
        "while",
        "will",
        "with",
        "within",
        "without",
        "would",
        "your",
        "yours",
        "mine",
        "father",
        "brother",
        "brothers",
    }
)
FUNCTION_WORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "but",
        "of",
        "in",
        "on",
        "at",
        "to",
        "by",
        "for",
        "from",
        "with",
        "as",
        "was",
        "were",
        "is",
        "had",
        "his",
        "her",
        "its",
        "their",
        "that",
        "this",
    }
)
AGE_WORD = "age"
CLICHE_NAME_PATTERN = r"dark lord|ancient forest|dragon mountain|crystal cave|land of shadows|valley of death|black tower|shadow realm|eternal flame"
CHOSEN_TAG = "chosen"
PLACEHOLDER_VALUES = frozenset({"x", "placeholder", "tbd", "todo", "-", "…", "...", "n/a", "none"})
EMBEDDED_SECTION_PATTERN = r"^\s*(?:#+\s*)?(rumou?rs|sayings|details|hidden truth|special)\s*:?\s*$|^\s*(rumou?rs|sayings|details|hidden truth|special)\s*:"
TEMPLATE_TAG_LINE_PATTERN = r"^\s*<+[^\n]{0,60}>+"
TEMPLATE_WORD_PATTERN = r"placeholder|dummy|do_not_use"
TEMPLATE_NOTE_LINE_PATTERN = r"^\s*\((?:hidden truth|rumou?rs|sayings|details)[^)]{0,60}\)\s*$"
TEMPLATE_SHORT_LINE = 100
FILLER_WORDS = frozenset(
    {
        "the",
        "and",
        "with",
        "this",
        "that",
        "for",
        "like",
        "which",
        "who",
        "every",
        "more",
        "but",
        "until",
        "its",
        "their",
        "them",
        "they",
        "from",
        "into",
        "onto",
        "over",
        "under",
        "among",
        "between",
        "after",
        "before",
        "within",
        "without",
        "only",
        "just",
        "because",
        "where",
        "when",
        "while",
        "were",
        "was",
        "has",
        "have",
        "had",
        "not",
        "all",
        "each",
        "also",
        "than",
        "then",
    }
)
