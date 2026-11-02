import re
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.engine import ENGINE_SEED_SEPARATOR
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.engine.primitives.naming import Namer
from aerona.engine.primitives.queries import spoken_language
from aerona.language.generator import NameKind
from aerona.rules.registry import Rules

TITLE_PARTS = re.compile(r"[,;]")
FOLK_GOD_SEED = "god"


def guarded_names(name: str | None, title: str | None) -> list[str]:
    parts = [part.strip() for part in TITLE_PARTS.split(title or "")]
    return [item for item in (name or "", (title or "").strip(), *parts) if item]


def clashes(candidate: str, guarded: Sequence[str]) -> bool:
    folded = candidate.strip().casefold()
    if not folded:
        return True
    return any(item.casefold() in folded or folded in item.casefold() for item in guarded if item.strip())


async def people_language(session: AsyncSession, people: EntityRow) -> EntityRow | None:
    spoken = await spoken_language(session, people.id)
    if spoken is not None:
        return spoken
    statement = (
        select(EntityRow)
        .where(EntityRow.world_id == people.world_id, EntityRow.entity_type == EntityType.LANGUAGE, EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
        .limit(1)
    )
    language: EntityRow | None = await session.scalar(statement)
    return language


def folk_seed(god_id: int, people_id: int, attempt: int, salt: str = "") -> str:
    parts = [FOLK_GOD_SEED, str(god_id), str(people_id)] + ([str(attempt)] if attempt else []) + ([salt] if salt else [])
    return ENGINE_SEED_SEPARATOR.join(parts)


async def folk_god_name(namer: Namer, rules: Rules, people: EntityRow, god_id: int, guarded: Sequence[str], *, salt: str = "") -> str | None:
    language = await people_language(namer.session, people)
    if language is None:
        return None
    for attempt in range(rules.folk_belief.name_attempts):
        name = await namer.from_language(language, folk_seed(god_id, people.id, attempt, salt), NameKind.PERSON)
        if name is not None and not clashes(name, guarded):
            return name
    return None
