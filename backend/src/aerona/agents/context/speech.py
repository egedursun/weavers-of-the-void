import re
from collections import Counter

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.agents import COMMON_WORDS, TIC_MIN_WORD_LETTERS, TIC_STEM_LETTERS
from aerona.db.tables.lore import ChronicleRow
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.rules.registry import Rules

WORD_SPLIT = re.compile(r"[^\W\d_]+")
SPOKEN = re.compile(r':\s*"(.*)"\s*$', re.DOTALL)
PERCENT = 100


def spoken_text(line: str) -> str:
    match = SPOKEN.search(line)
    return match.group(1) if match else line


def stems(text: str) -> set[str]:
    words = (word.casefold() for word in WORD_SPLIT.findall(text))
    return {word[:TIC_STEM_LETTERS] for word in words if len(word) >= TIC_MIN_WORD_LETTERS and word not in COMMON_WORDS}


async def recent_words(session: AsyncSession, limit: int, son_id: int | None = None) -> list[str]:
    statement = select(ChronicleRow.text).where(ChronicleRow.kind == ChronicleKind.SPEECH).order_by(ChronicleRow.id.desc()).limit(limit)
    if son_id is not None:
        statement = statement.where(ChronicleRow.son_id == son_id)
    return [spoken_text(text) for text in await session.scalars(statement)]


def frequent_stems(texts: list[str], threshold_pct: int, cap: int) -> list[str]:
    if not texts:
        return []
    counts = Counter(stem for text in texts for stem in stems(text))
    floor = max(2, len(texts) * threshold_pct / PERCENT)
    ranked = sorted((stem for stem, count in counts.items() if count >= floor), key=lambda stem: (-counts[stem], stem))
    return ranked[:cap]


async def openings(session: AsyncSession, rules: Rules, son_id: int) -> list[str]:
    fate = rules.fate
    texts = await recent_words(session, fate.banned_son_message_openings, son_id)
    return [" ".join(text.split()[: fate.son_opening_words]) for text in texts if text.strip()]


async def tics(session: AsyncSession, rules: Rules, son_id: int | None) -> list[str]:
    fate = rules.fate
    found: list[str] = []
    if son_id is not None:
        own = await recent_words(session, fate.message_tic_window, son_id)
        if len(own) >= fate.message_tic_min_messages:
            found.extend(frequent_stems(own, fate.message_tic_threshold_pct, fate.message_tic_cap))
    shared = await recent_words(session, fate.shared_tic_window)
    found.extend(stem for stem in frequent_stems(shared, fate.shared_tic_threshold_pct, fate.shared_tic_cap) if stem not in found)
    return found
