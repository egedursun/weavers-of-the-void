import re

from aerona.constants.agents import ENGINE_DESCRIPTION_PREFIX, LEGACY_ENGINE_DESCRIPTION_PREFIX

ENGINE_DESCRIPTION_PREFIXES = (ENGINE_DESCRIPTION_PREFIX, LEGACY_ENGINE_DESCRIPTION_PREFIX)

WORD_QUOTED = re.compile(r"«([^»]+)»")
WORD_LABEL = re.compile(r"\b(?:word|saying)(?:\s*\(to the chronicle\))?\s*:", re.IGNORECASE)
EDGE_QUOTES = "\"\u201c\u201d'\u2018\u2019 \n\t"
THREAD_TAG = re.compile(r"\[\s*(?:thread|story)\s*#\s*\d+\s*\]", re.IGNORECASE)
PAREN_ID = re.compile(r"\(\s*(?:thread|story|son|foreign|entity|record)?\s*#\s*\d+[^)]*\)", re.IGNORECASE)
THREAD_POSSESSIVE = re.compile(r"\b(?:thread|story)\s*#\s*\d+(?:'s)?\s+story's\b", re.IGNORECASE)
THREAD_MENTION = re.compile(r"\b(?:thread|story)\s*#\s*\d+('s)?", re.IGNORECASE)
SON_MENTION = re.compile(r"\bson\s*#\s*\d+\s+(?=[A-Z])")
SON_NUMBER = re.compile(r"\bson\s*#\s*\d+('s)?", re.IGNORECASE)
RECORD_MENTION = re.compile(r"\b(?:entity|record|foreign)\s*#\s*\d+", re.IGNORECASE)
HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
NOTE_LINE = re.compile(r"^\s*note:\s*this record.*$", re.IGNORECASE | re.MULTILINE)
POWER_CLASS = re.compile(r"\s*\(?\bclassified as P\d+\)?|\s*\(P\d+\)", re.IGNORECASE)
DICE_SCORE = re.compile("\\(\\s*\\d+\\s*[\u2013-]\\s*\\d+\\s*\\)")
STRAY_ID = re.compile(r"#\d+")
STARS = re.compile(r"[★☆]+")
SPACES = re.compile(r"[ \t]{2,}")
SPACE_BEFORE_PUNCTUATION = re.compile(r"\s+([,.;:!?])")
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
CLAUSE_SPLIT = re.compile(r"\s*;\s*")
INTERNAL_REASONING = re.compile(
    r"pre-?screen|unbound|tired (?:image|motif)|motif ban|clich[eé] (?:ban|name)|accepted with (?:a )?rationale|\bwarnings?\b|criterion\s*\(?[a-e]\)?",
    re.IGNORECASE,
)
LEADING_CONTRAST = re.compile(r"^(?:however|but|yet|still)[,\s]+", re.IGNORECASE)
META_SENTENCE = re.compile(r"\bfate\b[^.!?]*\b(?:rewrote|re-wrote|fixed|changed|corrected|amended)\b|\bthe first telling\b", re.IGNORECASE)
LETTER = re.compile(r"[^\W\d_]")
TRAILING_JOINERS = " ,;:"
ELLIPSIS = "…"
NUMBER_TOKEN = re.compile(r"(?<![\w.])\d+(?![\w.])")


def extract_word(text: str | None) -> str:
    if not text:
        return ""
    quoted = WORD_QUOTED.search(text)
    if quoted:
        return quoted.group(1).strip()
    labelled = WORD_LABEL.search(text)
    if labelled:
        return text[labelled.end() :].strip().strip(EDGE_QUOTES).strip()
    return ""


def sanitize(text: str | None) -> str:
    if not text:
        return ""
    cleaned = HTML_COMMENT.sub("", text)
    cleaned = NOTE_LINE.sub("", cleaned)
    cleaned = THREAD_TAG.sub("", cleaned)
    cleaned = THREAD_POSSESSIVE.sub("a story's", cleaned)
    cleaned = THREAD_MENTION.sub(lambda match: "a story's" if match.group(1) else "a story", cleaned)
    cleaned = SON_MENTION.sub("", cleaned)
    cleaned = SON_NUMBER.sub(lambda match: "a son's" if match.group(1) else "a son", cleaned)
    cleaned = PAREN_ID.sub("", cleaned)
    cleaned = RECORD_MENTION.sub("a record", cleaned)
    cleaned = POWER_CLASS.sub("", cleaned)
    cleaned = DICE_SCORE.sub("", cleaned)
    cleaned = STRAY_ID.sub("", cleaned)
    cleaned = STARS.sub("", cleaned)
    cleaned = SPACES.sub(" ", cleaned)
    cleaned = SPACE_BEFORE_PUNCTUATION.sub(r"\1", cleaned)
    return "\n".join(line.strip() for line in cleaned.strip().split("\n"))


def sentences(text: str) -> list[str]:
    return [part for part in SENTENCE_SPLIT.split(text.strip()) if part]


def capitalised(text: str) -> str:
    return text[:1].upper() + text[1:] if text else text


def clean_fate_note(text: str | None) -> str | None:
    kept: list[str] = []
    for sentence in sentences(sanitize(text)):
        clauses = [clause for clause in CLAUSE_SPLIT.split(sentence) if clause and not INTERNAL_REASONING.search(clause)]
        if clauses:
            kept.append("; ".join(clauses))
    joined = capitalised(LEADING_CONTRAST.sub("", " ".join(kept)).strip())
    return joined if LETTER.search(joined) else None


def shorten_rationale(text: str | None, word_limit: int) -> str | None:
    cleaned = clean_fate_note(text)
    if cleaned is None:
        return None
    words = cleaned.split()
    if len(words) <= word_limit:
        return cleaned
    first = sentences(cleaned)[0]
    if len(first.split()) <= word_limit:
        return first
    return " ".join(words[:word_limit]).rstrip(TRAILING_JOINERS) + ELLIPSIS


def strip_meta_sentences(text: str | None) -> str:
    lines = [" ".join(sentence for sentence in sentences(line) if not META_SENTENCE.search(sentence)) for line in (text or "").split("\n")]
    return "\n".join(lines).strip()


def without_engine_prefix(text: str | None) -> str:
    value = (text or "").strip()
    for prefix in ENGINE_DESCRIPTION_PREFIXES:
        if value.startswith(prefix):
            value = value[len(prefix) :].strip()
    return value


def replace_name(text: str | None, old: str, new: str, protected: tuple[str, ...] = ()) -> str:
    if not text or not old or old == new:
        return text or ""
    guards = {f"\x00{index}\x00": name for index, name in enumerate(sorted(protected, key=len, reverse=True)) if old in name and name != old}
    shielded = text
    for token, name in guards.items():
        shielded = shielded.replace(name, token)
    replaced = re.sub(rf"(?<![^\W\d_]){re.escape(old)}(?![^\W\d_])", new, shielded)
    for token, name in guards.items():
        replaced = replaced.replace(token, name)
    return replaced


def epoch_mentions(text: str, last_epoch: int) -> int:
    return sum(1 for token in NUMBER_TOKEN.findall(text) if 1 <= int(token) <= last_epoch)
