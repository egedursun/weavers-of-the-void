import re
from collections import Counter
from collections.abc import Iterable

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.entity_types import ENTITY_TYPES
from aerona.constants.tool_inputs import SUBTYPE_MAX
from aerona.core.grammar import spoken
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EngineKind, EntityStatus, EntityType

TRUNCATION_SLACK = 2
MINIMUM_LAST_WORD = 2
KEY_SEPARATOR = ":"
ENGINE_KIND_KEYS = frozenset(kind.value for kind in EngineKind)


STATUS_WORDS = frozenset(
    {
        "dispersed",
        "disbanded",
        "dead",
        "died",
        "alive",
        "living",
        "destroyed",
        "cursed",
        "ruined",
        "ruin",
        "abandoned",
        "lost",
        "forgotten",
        "exiled",
        "mutated",
        "ruler",
    }
)
LEAK = re.compile(r"^(?:g\d+|p\d+|power \d+|\d[\d.,]*\s*(?:soldiers|warriors|men)|epoch \d+|led by .+|second|third)$")
TYPE_PREFIX = re.compile(r"^([^\W\d_][\w ]*?)\s*[·/]\s*(.+)$")
PARENTHESES = re.compile(r"^(.*?)\s*\(([^()]*)\)\s*$")
TYPE_WORDS = frozenset({spoken(entity_type) for entity_type in EntityType} | {spec.label.casefold() for spec in ENTITY_TYPES.values()})


def without_status(text: str) -> str:
    cleaned = " ".join(text.split())
    prefix = TYPE_PREFIX.match(cleaned)
    if prefix is not None and prefix.group(1).strip().casefold() in TYPE_WORDS:
        cleaned = prefix.group(2).strip()
    found = PARENTHESES.match(cleaned)
    if found is None:
        return cleaned
    outside = found.group(1).strip()
    kept = [part.strip() for part in found.group(2).split(",") if part.strip()]
    kept = [part for part in kept if part.casefold() not in STATUS_WORDS and not LEAK.match(part.casefold()) and part.casefold() not in TYPE_WORDS]
    if not outside or outside.casefold() in TYPE_WORDS:
        return ", ".join(kept) if kept else outside or cleaned
    return f"{outside} ({', '.join(kept)})" if kept else outside


def tidy(text: str) -> str:
    return without_status(" ".join(text.replace("_", " ").split()))[:SUBTYPE_MAX]


def _labelled(text: str) -> str:
    head, separator, rest = " ".join(text.split()).partition(KEY_SEPARATOR)
    key = head.strip().casefold()
    if key not in ENGINE_KIND_KEYS and "_" not in key:
        return text
    label = key.replace("_", " ")
    return f"{label}{KEY_SEPARATOR} {rest.strip()}" if separator and rest.strip() else label


def normalize_subtype(subtype: str | None, existing: Iterable[str] | Counter[str] = ()) -> str | None:
    if subtype is None:
        return None
    cleaned = tidy(_labelled(subtype))
    if not cleaned:
        return None
    spellings = existing if isinstance(existing, Counter) else Counter(spelling for spelling in existing if spelling)
    folded = cleaned.casefold()
    same = [(count, spelling) for spelling, count in spellings.items() if spelling.casefold() == folded]
    if same:
        cleaned = max(same)[1]
    words = cleaned.split(" ")
    if len(words) > 1 and len(words[-1]) >= MINIMUM_LAST_WORD:
        longer = [
            (count, spelling)
            for spelling, count in spellings.items()
            if spelling.casefold().startswith(folded) and 0 < len(spelling) - len(cleaned) <= TRUNCATION_SLACK and " " not in spelling[len(cleaned) :]
        ]
        if longer and max(longer)[0] > spellings.get(cleaned, 0):
            cleaned = max(longer)[1]
    return cleaned


async def subtype_spellings(session: AsyncSession, entity_type: EntityType) -> Counter[str]:
    statement = (
        select(EntityRow.subtype, func.count())
        .where(EntityRow.entity_type == entity_type, EntityRow.subtype.is_not(None), EntityRow.status != EntityStatus.REJECTED)
        .group_by(EntityRow.subtype)
    )
    return Counter({str(value): int(count) for value, count in await session.execute(statement) if value})


async def normalized_subtype(session: AsyncSession, entity_type: EntityType, subtype: str | None) -> str | None:
    if subtype is None or not subtype.strip():
        return None
    return normalize_subtype(subtype, await subtype_spellings(session, entity_type))
