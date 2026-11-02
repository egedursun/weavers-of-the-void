import re
from collections.abc import Iterable

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.rarities import name_similarity_policy
from aerona.core.errors import ConflictError, ValidationFailedError
from aerona.db.repositories.entities import split_epithet
from aerona.db.repositories.names import NameRepository, clean_display, normalize_name, roman
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import LIVING_STATUSES
from aerona.engine.primitives.renames import rename_everywhere
from aerona.rules.registry import Rules

LETTER_OR_DIGIT_BEFORE = r"(?<![^\W_])"


def normalize(name: str) -> str:
    return normalize_name(name)


def roman_numeral(number: int) -> str:
    return roman(number)


async def is_taken(session: AsyncSession, name: str, ignore_node_id: int | None = None) -> bool:
    return await NameRepository(session).is_taken(name, ignore_node_id)


async def unique_name(session: AsyncSession, base: str) -> str:
    return await NameRepository(session).unique_name(base)


async def similar_name(session: AsyncSession, rules: Rules, name: str, family: bool = False, ignore_node_id: int | None = None) -> str | None:
    return await NameRepository(session).similar_name(name, name_similarity_policy(rules), family=family, ignore_node_id=ignore_node_id)


async def validate_new_name(session: AsyncSession, rules: Rules, name: str, ignore_node_id: int | None = None, family: bool = False) -> str:
    display = clean_display(name)
    if not normalize(display):
        raise ValidationFailedError("A name cannot be empty.")
    if await is_taken(session, display, ignore_node_id):
        raise ConflictError(f"The name {display} is already taken.")
    similar = await similar_name(session, rules, display, family=family, ignore_node_id=ignore_node_id)
    if similar is not None:
        raise ConflictError(f"The name {display} is too close to {similar}.")
    return display


async def apply_epithet(session: AsyncSession, entity: EntityRow) -> bool:
    short, epithet = split_epithet(entity.name)
    if epithet is None or await is_taken(session, short, entity.id):
        return False
    if not entity.title:
        entity.title = epithet
    await rename_everywhere(session, entity.id, short)
    return True


async def find_named_records(
    session: AsyncSession,
    rules: Rules,
    text: str,
    *,
    world_id: int | None = None,
    exclude: Iterable[int] = (),
    limit: int | None = None,
) -> list[EntityRow]:
    minimum = rules.link_graph.name_min_chars
    cap = limit if limit is not None else rules.link_graph.proposal_cap
    excluded = set(exclude)
    statement = select(EntityRow).where(
        EntityRow.status.in_(list(LIVING_STATUSES)),
        EntityRow.pending_name.is_(False),
        func.length(EntityRow.name) >= minimum,
        func.instr(text, EntityRow.name) > 0,
    )
    if world_id is not None:
        statement = statement.where(EntityRow.world_id == world_id)
    candidates = sorted(await session.scalars(statement), key=lambda row: (-len(row.name), -(row.importance or 0), row.id))
    found: list[EntityRow] = []
    for candidate in candidates:
        if candidate.id in excluded:
            continue
        if not _bounded(text, candidate.name):
            continue
        found.append(candidate)
        if len(found) >= cap:
            break
    return found


def mentions_name(text: str, name: str) -> bool:
    return name in text and _bounded(text, name)


def _bounded(text: str, name: str) -> bool:
    for match in re.finditer(LETTER_OR_DIGIT_BEFORE + re.escape(name), text):
        following = text[match.end() : match.end() + 1]
        if not following or not following.isalpha() or not following.islower():
            return True
    return False
