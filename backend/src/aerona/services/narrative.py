import re
from enum import StrEnum
from typing import Any

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.cosmos import CreatorRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.epochs import EpochRow, EpochWorldNarrativeRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.lore import FolkBeliefRow, HistorianViewRow
from aerona.domain.enums.entity import ENDED_STATUSES, EntityStatus, EntityType
from aerona.domain.enums.world import LoreLanguage

SPACES = re.compile(r"\s+")
SPACE_BEFORE_PUNCTUATION = re.compile(r"\s+([,.;:!?)])")
DANGLING_PUNCTUATION = re.compile(r"[,;:]+(?=[.!?])")
BRACKETED_TAG = re.compile(r"\[[^\]]*#\d+[^\]]*\]")
PARENTHESIZED_ID = re.compile(r"\(\s*(?:[a-z_]+)?[#:]\d+(?:\s+[a-z][\w-]*)?\s*\)", re.IGNORECASE)
PREFIXED_NAME = re.compile(r"\b(?:son|thread|world|route|foreign|star)[#:]\d+\s+(?=[A-Z])")
THREAD_HANDLE = re.compile(r"\bthread[#:]\d+(?:'s)?", re.IGNORECASE)
SON_HANDLE = re.compile(r"\bson[#:]\d+(?:'s)?", re.IGNORECASE)
COSMIC_HANDLE = re.compile(r"\b(?:world|route|foreign|star)[#:]\d+\b", re.IGNORECASE)
BARE_HANDLE = re.compile(r"(?<![\w&])#\d+\b")
STORY_PLACEHOLDER = "a story"
SON_PLACEHOLDER = "a son"

HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
EDITORIAL_LINE = re.compile(r"^\s*note:\s*this record.*$", re.IGNORECASE | re.MULTILINE)
POWER_CLASS = re.compile(r"\bclassified as P\d+\b|\(\s*P\d+\s*\)", re.IGNORECASE)
DICE_SCORE = re.compile(r"\(\s*\d+\s*[-\u2013\u2014]\s*\d+\s*\)|\bwith \d+ (?:to|against) \d+\b", re.IGNORECASE)
STAR_MARK = re.compile(r"\u2605\s*\d*")

STAT_TRANSITION = re.compile(r"\s*\bfrom \d+(?:\.\d+)? to \d+(?:\.\d+)?\b", re.IGNORECASE)
FELL_TO = re.compile(r"\b(fell|dropped|receded|sank|decreased) to \d+(?:\.\d+)?\b", re.IGNORECASE)
ROSE_TO = re.compile(r"\b(rose|increased|grew|climbed) to \d+(?:\.\d+)?\b", re.IGNORECASE)
RESOURCE_AMOUNT = re.compile(r"\b\d+(?:\.\d+)?\s+(hp|essence|fame|renown|xp|faith|actions?|action points?)\b", re.IGNORECASE)

RECORD_TYPE_WORDS = (
    "prophecy",
    "knowledge",
    "language",
    "remnant",
    "remnants",
    "tradition",
    "legend",
    "war",
    "coin",
    "cult",
    "law",
    "army",
    "caravan",
    "uprising",
    "plague",
    "temple",
    "ruin",
    "tale",
    "epic",
    "rite",
)
DUPLICATE_TYPE_WORD = re.compile(r"\b(" + "|".join(RECORD_TYPE_WORDS) + r")\s+\1\b", re.IGNORECASE)

SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
INTERNAL_WARNING = re.compile(
    r"pre-?screen|unbonded|unlinked|tired (?:motif|image|cop(?:y|ies))|motif ban|clich[e\u00e9]"
    r"|accepted with (?:a )?justification|\bwarning\b|criteri(?:on|a) [a-e]\b",
    re.IGNORECASE,
)
LEADING_CONJUNCTION = re.compile(r"^(?:however|but|yet|still|despite this|nevertheless)\s*,?\s*", re.IGNORECASE)
HAS_LETTER = re.compile(r"[^\W\d_]")
META_SENTENCE = re.compile(
    r"\bfate\b[^.!?]*\b(?:rewr[oi]te|rewritten|correct(?:ed|s)?|chang(?:ed|es)|amend(?:ed|s)?|revis(?:ed|es))\b[^.!?]*\b(?:account|description|record|text)\b"
    r"|\bthe first account\b|\bthis record (?:was|has been) (?:corrected|rewritten|amended|revised)\b",
    re.IGNORECASE,
)

MORTAL_AS_SON = re.compile(r"\b(is|was) (an?|the) ((?:[\w-]+ ){0,3})son\b(?! of)", re.IGNORECASE)
MORTAL_WORD = "mortal"


RULER_TITLES: dict[EntityType, str] = {
    EntityType.LAW: "Keeper",
    EntityType.NATURAL_LAW: "Keeper",
    EntityType.SETTLEMENT: "Sovereign",
    EntityType.PEOPLE: "Chieftain",
    EntityType.REGION: "Warden",
    EntityType.PLACE: "Warden",
    EntityType.FACTION: "Leader",
    EntityType.CULT: "High Priest",
    EntityType.ARMY: "Commander",
    EntityType.TRADITION: "Guardian",
    EntityType.KNOWLEDGE: "Custodian",
    EntityType.LANGUAGE: "Custodian",
    EntityType.VESSEL: "Captain",
}
DEFAULT_RULER_TITLE = "Sovereign"


class EndingKind(StrEnum):
    DIED = "died"
    VANISHED = "vanished"
    ENDED = "ended"


ENDING_TEMPLATES: dict[EndingKind, str] = {
    EndingKind.DIED: "Died in Epoch {epoch}.",
    EndingKind.VANISHED: "Vanished in Epoch {epoch}.",
    EndingKind.ENDED: "Came to an end in Epoch {epoch}.",
}
EPOCH_MENTION = "Epoch {epoch}"


def collapse_spaces(text: str) -> str:
    return DANGLING_PUNCTUATION.sub("", SPACE_BEFORE_PUNCTUATION.sub(r"\1", SPACES.sub(" ", text))).strip()


def capitalize_first(text: str) -> str:
    return text[:1].upper() + text[1:] if text else text


def _placeholder(match: re.Match[str], word: str) -> str:
    start = match.start()
    prefix = match.string[:start].rstrip()
    at_sentence_start = not prefix or prefix[-1] in ".!?"
    return capitalize_first(word) if at_sentence_start else word


def scrub_ids(text: str) -> str:
    result = BRACKETED_TAG.sub("", text)
    result = PARENTHESIZED_ID.sub("", result)
    result = PREFIXED_NAME.sub("", result)
    result = THREAD_HANDLE.sub(lambda match: _placeholder(match, STORY_PLACEHOLDER), result)
    result = SON_HANDLE.sub(lambda match: _placeholder(match, SON_PLACEHOLDER), result)
    result = COSMIC_HANDLE.sub("", result)
    result = BARE_HANDLE.sub("", result)
    return collapse_spaces(result)


def collapse_type_repetition(text: str) -> str:
    return DUPLICATE_TYPE_WORD.sub(r"\1", text)


def clean_chronicle_text(text: str) -> str:
    return collapse_type_repetition(scrub_ids(text))


def prompt_safe(text: str) -> str:
    result = STAT_TRANSITION.sub("", text)
    result = FELL_TO.sub(lambda match: f"{match.group(1)}", result)
    result = ROSE_TO.sub(lambda match: f"{match.group(1)}", result)
    result = DICE_SCORE.sub("", result)
    result = RESOURCE_AMOUNT.sub(lambda match: match.group(1), result)
    return collapse_spaces(result)


def clean_narrative(text: str) -> str:
    result = HTML_COMMENT.sub("", text)
    result = EDITORIAL_LINE.sub("", result)
    result = POWER_CLASS.sub("", result)
    result = DICE_SCORE.sub("", result)
    result = STAR_MARK.sub("", result)
    paragraphs = [scrub_ids(paragraph) for paragraph in result.split("\n\n")]
    return "\n\n".join(paragraph for paragraph in paragraphs if paragraph)


def sentences(text: str) -> list[str]:
    return [part.strip() for part in SENTENCE_SPLIT.split(text) if part.strip()]


def _terminated(text: str) -> str:
    stripped = text.strip().rstrip(";,")
    return stripped if stripped.endswith((".", "!", "?")) else f"{stripped}."


def clean_fate_note(text: str | None) -> str | None:
    if not text:
        return None
    kept: list[str] = []
    for sentence in sentences(scrub_ids(text)):
        if not INTERNAL_WARNING.search(sentence):
            kept.append(sentence)
            continue
        clauses = [clause for clause in sentence.split(";") if clause.strip() and not INTERNAL_WARNING.search(clause)]
        kept.extend(_terminated(clause) for clause in clauses)
    joined = collapse_spaces(" ".join(kept))
    joined = capitalize_first(LEADING_CONJUNCTION.sub("", joined))
    return joined if HAS_LETTER.search(joined) else None


def remove_meta_sentences(text: str) -> str:
    paragraphs = []
    for paragraph in text.split("\n\n"):
        kept = [sentence for sentence in sentences(paragraph) if not META_SENTENCE.search(sentence)]
        if kept:
            paragraphs.append(" ".join(kept))
    return "\n\n".join(paragraphs)


def clean_lore(text: str) -> str:
    return remove_meta_sentences(clean_narrative(text))


def clean_lore_value(value: Any) -> Any:
    if isinstance(value, str):
        return clean_lore(value)
    if isinstance(value, list):
        return [clean_lore_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(clean_lore_value(item) for item in value)
    if isinstance(value, dict):
        return {key: clean_lore_value(item) for key, item in value.items()}
    return value


def ending_kind(entity_type: EntityType, destroyed: bool) -> EndingKind:
    if destroyed:
        return EndingKind.VANISHED
    if entity_type is EntityType.MORTAL:
        return EndingKind.DIED
    return EndingKind.ENDED


def default_ending(entity_type: EntityType, destroyed: bool, epoch: int) -> str:
    return ENDING_TEMPLATES[ending_kind(entity_type, destroyed)].format(epoch=epoch)


def fate_note_ending(fate_note: str | None, epoch: int) -> str | None:
    if not fate_note:
        return None
    mention = EPOCH_MENTION.format(epoch=epoch)
    candidates = [sentence for sentence in sentences(fate_note) if mention in sentence]
    return candidates[-1] if candidates else None


def append_ending(description: str, sentence: str) -> str:
    cleaned = clean_lore(sentence)
    if not cleaned or cleaned in description:
        return description
    return f"{description.rstrip()} {cleaned}".strip()


def mentions_epoch(description: str, epoch: int) -> bool:
    return EPOCH_MENTION.format(epoch=epoch) in description


def ruler_title(ruled_type: EntityType) -> str:
    return RULER_TITLES.get(ruled_type, DEFAULT_RULER_TITLE)


def mortal_description(text: str) -> str:
    return MORTAL_AS_SON.sub(lambda match: f"{match.group(1)} {match.group(2)} {match.group(3)}{MORTAL_WORD}", text)


def clean_model[M: BaseModel](model: M | None) -> M | None:
    if model is None:
        return None
    cleaned = clean_lore_value(model.model_dump(mode="python"))
    return type(model).model_validate(cleaned)


def _clean_text_attribute(row: object, attribute: str) -> bool:
    value = getattr(row, attribute)
    if not isinstance(value, str) or not value:
        return False
    cleaned = clean_lore(value)
    if cleaned == value:
        return False
    setattr(row, attribute, cleaned)
    return True


def _clean_model_attribute(row: object, attribute: str) -> bool:
    value = getattr(row, attribute)
    if not isinstance(value, BaseModel):
        return False
    cleaned = clean_model(value)
    if cleaned == value:
        return False
    setattr(row, attribute, cleaned)
    return True


def _sweep_row(row: object, texts: tuple[str, ...], models: tuple[str, ...] = ()) -> bool:
    changed = [_clean_text_attribute(row, attribute) for attribute in texts] + [_clean_model_attribute(row, attribute) for attribute in models]
    return any(changed)


async def _lore_is_english(session: AsyncSession) -> bool:
    cosmos = await CosmosRepository(session).get()
    return cosmos is None or cosmos.lore_language is LoreLanguage.ENGLISH


async def sweep_narratives(session: AsyncSession) -> int:
    if not await _lore_is_english(session):
        return 0
    changed = 0
    for entity in await session.scalars(select(EntityRow).where(EntityRow.status != EntityStatus.REJECTED)):
        changed += _sweep_row(entity, ("description",), ("depth",))
    for epoch in await session.scalars(select(EpochRow)):
        changed += _sweep_row(epoch, ("narrative", "summary"))
    for world_narrative in await session.scalars(select(EpochWorldNarrativeRow)):
        changed += _sweep_row(world_narrative, ("narrative", "summary"))
    for god in await session.scalars(select(ForeignGodRow)):
        changed += _sweep_row(god, ("description",), ("depth", "personality"))
    for view in await session.scalars(select(HistorianViewRow)):
        changed += _sweep_row(view, ("text",))
    for belief in await session.scalars(select(FolkBeliefRow)):
        changed += _sweep_row(belief, ("account", "misconception"))
    for creator in await session.scalars(select(CreatorRow)):
        changed += _sweep_row(creator, (), ("depth", "epic"))
    await session.flush()
    return changed


async def write_ending(session: AsyncSession, entity: EntityRow, sentence: str) -> bool:
    updated = append_ending(entity.description, sentence)
    if updated == entity.description:
        return False
    entity.description = updated
    await session.flush()
    return True


async def backfill_endings(session: AsyncSession) -> int:
    if not await _lore_is_english(session):
        return 0
    statement = select(EntityRow).where(EntityRow.status.in_(list(ENDED_STATUSES)), EntityRow.end_epoch.is_not(None))
    written = 0
    for entity in await session.scalars(statement):
        epoch = entity.end_epoch
        if epoch is None or mentions_epoch(entity.description, epoch):
            continue
        sentence = fate_note_ending(entity.fate_note, epoch) or default_ending(entity.entity_type, entity.status is EntityStatus.DESTROYED, epoch)
        written += await write_ending(session, entity, sentence)
    return written
