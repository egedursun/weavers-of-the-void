import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.names import NameRepository, clean_display, normalize_name
from aerona.db.repositories.nodes import NodeRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.epochs import EpochRow, EpochWorldNarrativeRow
from aerona.db.tables.lore import CanonFactRow, ChronicleRow, FolkBeliefRow, HistorianViewRow, LexemeRow, ThreadRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.polity import TreatyPartyRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityStatus
from aerona.engine.collective.embodied import follow_name

ROMAN_SUFFIX = r"\s+(?:I{1,3}|IV|VI{0,3}|IX|X{1,3}|\d+)(?![^\W_])"
LETTER_OR_DIGIT_BEFORE = r"(?<![^\W_])"
LETTER_OR_DIGIT_AFTER = r"(?![^\W_])"
MASK = "\u0000{index}\u0000"
PLACE_BONDS = (BondKind.INSIDE, BondKind.LIVES_IN, BondKind.PART_OF)
MASK_PATTERN = re.compile("\u0000(\\d+)\u0000")


@dataclass(frozen=True)
class TextField:
    model: type[Any]
    column: str
    epoch_bound: bool = False


TEXT_FIELDS: tuple[TextField, ...] = (
    TextField(ChronicleRow, "text", epoch_bound=True),
    TextField(HistorianViewRow, "text", epoch_bound=True),
    TextField(EpochRow, "narrative", epoch_bound=True),
    TextField(EpochRow, "summary", epoch_bound=True),
    TextField(EpochWorldNarrativeRow, "narrative", epoch_bound=True),
    TextField(EpochWorldNarrativeRow, "summary", epoch_bound=True),
    TextField(EntityRow, "description"),
    TextField(EntityRow, "fate_note"),
    TextField(BondRow, "description"),
    TextField(ThreadRow, "text"),
    TextField(ThreadRow, "closing_text"),
    TextField(FolkBeliefRow, "account"),
    TextField(FolkBeliefRow, "misconception"),
    TextField(LexemeRow, "etymology"),
    TextField(LexemeRow, "example"),
    TextField(CanonFactRow, "object_text"),
    TextField(CanonFactRow, "predicate"),
)
JSON_FIELDS: tuple[TextField, ...] = (TextField(EntityRow, "depth"),)


@dataclass(frozen=True)
class RenameResult:
    old: str
    new: str
    changed: int


def _word(name: str) -> str:
    return LETTER_OR_DIGIT_BEFORE + re.escape(name) + LETTER_OR_DIGIT_AFTER


def name_in_text(text: str, old: str, new: str, protected: Sequence[str] = ()) -> str:
    if not old or old not in text:
        return text
    masked: list[str] = []
    result = text
    for name in sorted((item for item in protected if old in item and item != old), key=len, reverse=True):
        pattern = re.compile(_word(name))
        if pattern.search(result):
            masked.append(name)
            result = pattern.sub(MASK.format(index=len(masked) - 1), result)
    result = re.sub(_word(old) + f"(?!{ROMAN_SUFFIX})", lambda _match: new, result)
    return MASK_PATTERN.sub(lambda match: masked[int(match.group(1))], result)


def replace_in_value(value: Any, old: str, new: str, protected: Sequence[str]) -> Any:
    if isinstance(value, str):
        return name_in_text(value, old, new, protected)
    if isinstance(value, list):
        return [replace_in_value(item, old, new, protected) for item in value]
    if isinstance(value, tuple):
        return tuple(replace_in_value(item, old, new, protected) for item in value)
    if isinstance(value, dict):
        return {key: replace_in_value(item, old, new, protected) for key, item in value.items()}
    return value


async def protected_names(session: AsyncSession, node_id: int, old: str) -> list[str]:
    statement = select(NodeRow.name).where(NodeRow.id != node_id, NodeRow.name.contains(old))
    return [name for name in await session.scalars(statement) if name != old]


async def replace_texts(session: AsyncSession, old: str, new: str, protected: Sequence[str], from_epoch: int | None) -> int:
    changed = 0
    for field in TEXT_FIELDS:
        column = getattr(field.model, field.column)
        statement = select(field.model).where(column.contains(old))
        if from_epoch is not None and field.epoch_bound:
            statement = statement.where(field.model.epoch >= from_epoch)
        for row in await session.scalars(statement):
            current = getattr(row, field.column)
            updated = name_in_text(current, old, new, protected)
            if updated != current:
                setattr(row, field.column, updated)
                changed += 1
    for field in JSON_FIELDS:
        for row in await session.scalars(select(field.model).where(getattr(field.model, field.column).is_not(None))):
            value = getattr(row, field.column)
            if not isinstance(value, BaseModel):
                continue
            dumped = value.model_dump(mode="python")
            updated_dump = replace_in_value(dumped, old, new, protected)
            if updated_dump != dumped:
                setattr(row, field.column, type(value).model_validate(updated_dump))
                changed += 1
    await session.flush()
    return changed


async def derived_names(session: AsyncSession, node_id: int, old: str) -> list[tuple[int, str]]:
    word = re.compile(_word(old) + f"(?!{ROMAN_SUFFIX})")
    sibling = re.compile(re.escape(old) + ROMAN_SUFFIX + "$")
    bonded = (
        select(BondRow.target_node_id)
        .where(BondRow.source_node_id == node_id, BondRow.kind.not_in(PLACE_BONDS))
        .union(select(BondRow.source_node_id).where(BondRow.target_node_id == node_id, BondRow.kind.not_in(PLACE_BONDS)))
    )
    signed = select(TreatyPartyRow.treaty_entity_id).where(TreatyPartyRow.party_node_id == node_id)
    rows = await session.execute(
        select(NodeRow.id, NodeRow.name)
        .where(NodeRow.id != node_id, NodeRow.name.contains(old), or_(NodeRow.id.in_(bonded), NodeRow.id.in_(signed)))
        .order_by(NodeRow.id)
    )
    return [(found, name) for found, name in rows if name != old and word.search(name) and not sibling.fullmatch(name)]


async def follow_derived(session: AsyncSession, node_id: int, old: str, new: str, from_epoch: int | None) -> int:
    changed = 0
    for found, name in await derived_names(session, node_id, old):
        renamed = name_in_text(name, old, new)
        if renamed == name:
            continue
        display = await NameRepository(session).rename(found, renamed)
        changed += 1 + await replace_texts(session, name, display, await protected_names(session, found, name), from_epoch)
    return changed


async def rewrite_name(session: AsyncSession, node_id: int, old: str, new: str, from_epoch: int | None = None) -> int:
    if not old or old == new:
        return 0
    changed = await replace_texts(session, old, new, await protected_names(session, node_id, old), from_epoch)
    return changed + await follow_derived(session, node_id, old, new, from_epoch)


async def rename_everywhere(session: AsyncSession, node_id: int, new_name: str, from_epoch: int | None = None, *, free: bool = False) -> RenameResult:
    node = await NodeRepository(session).load(node_id)
    old = node.name
    display = clean_display(new_name)
    if not normalize_name(display) or display == old:
        return RenameResult(old=old, new=old, changed=0)
    if free:
        display = await NameRepository(session).unique_name(display)
        if display == old:
            return RenameResult(old=old, new=old, changed=0)
    protected = await protected_names(session, node_id, old)
    if isinstance(node, EntityRow) and node.status is EntityStatus.REJECTED:
        node.name = display
    else:
        await NameRepository(session).rename(node_id, display)
    changed = await replace_texts(session, old, display, protected, from_epoch)
    changed += await follow_derived(session, node_id, old, display, from_epoch)
    await follow_name(session, node_id, display)
    return RenameResult(old=old, new=display, changed=changed)


def reclaim_name(node: EntityRow, name: str) -> None:
    node.name = name
