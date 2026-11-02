import unicodedata

from sqlalchemy import func, select

from aerona.core.errors import ConflictError, ValidationFailedError
from aerona.db.repositories.base import Repository
from aerona.db.tables.node import NameRegistryRow, NodeRow
from aerona.domain.models.names import NameSimilarityPolicy

ROMAN_NUMERALS = (
    (1000, "M"),
    (900, "CM"),
    (500, "D"),
    (400, "CD"),
    (100, "C"),
    (90, "XC"),
    (50, "L"),
    (40, "XL"),
    (10, "X"),
    (9, "IX"),
    (5, "V"),
    (4, "IV"),
    (1, "I"),
)
ROMAN_LIMIT = 4000
FIRST_SUFFIX = 2
RANGE_END = "\U0010ffff"


def normalize_name(name: str) -> str:
    decomposed = unicodedata.normalize("NFKD", name.casefold())
    stripped = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(stripped.split())


def clean_display(name: str) -> str:
    return " ".join(name.split())


def is_single_word(name: str) -> bool:
    return len(clean_display(name).split(" ")) == 1


def roman(number: int) -> str:
    if number <= 0 or number >= ROMAN_LIMIT:
        return str(number)
    parts: list[str] = []
    remaining = number
    for value, symbol in ROMAN_NUMERALS:
        while remaining >= value:
            parts.append(symbol)
            remaining -= value
    return "".join(parts)


def edit_distance_within_one(left: str, right: str) -> bool:
    if left == right:
        return True
    if abs(len(left) - len(right)) > 1:
        return False
    if len(left) == len(right):
        return sum(1 for a, b in zip(left, right, strict=True) if a != b) <= 1
    shorter, longer = (left, right) if len(left) < len(right) else (right, left)
    index = 0
    while index < len(shorter) and shorter[index] == longer[index]:
        index += 1
    return shorter[index:] == longer[index + 1 :]


class NameRepository(Repository):
    async def owner(self, name: str) -> int | None:
        row = await self.session.get(NameRegistryRow, normalize_name(name))
        return row.node_id if row is not None else None

    async def is_taken(self, name: str, ignore_node_id: int | None = None) -> bool:
        owner = await self.owner(name)
        return owner is not None and owner != ignore_node_id

    async def claim(self, node_id: int, name: str) -> str:
        display = clean_display(name)
        normalized = normalize_name(display)
        if not normalized:
            raise ValidationFailedError("A name cannot be empty.")
        existing = await self.session.get(NameRegistryRow, normalized)
        if existing is not None and existing.node_id != node_id:
            raise ConflictError(f"The name {display} is already taken.")
        current = await self._row_for(node_id)
        if current is not None and current.normalized != normalized:
            await self.session.delete(current)
            await self.session.flush()
        if existing is None:
            self.session.add(NameRegistryRow(normalized=normalized, node_id=node_id, display=display, single_word=is_single_word(display)))
        else:
            existing.display = display
        await self.session.flush()
        return display

    async def release(self, node_id: int) -> None:
        current = await self._row_for(node_id)
        if current is not None:
            await self.session.delete(current)
            await self.session.flush()

    async def rename(self, node_id: int, new_name: str) -> str:
        node = await self.require(NodeRow, node_id, "record")
        display = await self.claim(node_id, new_name)
        node.name = display
        await self.session.flush()
        return display

    async def unique_name(self, base: str) -> str:
        root = clean_display(base)
        if not normalize_name(root):
            raise ValidationFailedError("A name cannot be empty.")
        if not await self.is_taken(root):
            return root
        suffix = FIRST_SUFFIX
        while await self.is_taken(f"{root} {roman(suffix)}"):
            suffix += 1
        return f"{root} {roman(suffix)}"

    async def similar_name(self, name: str, policy: NameSimilarityPolicy, family: bool = False, ignore_node_id: int | None = None) -> str | None:
        if not is_single_word(name):
            return None
        normalized = normalize_name(name)
        if len(normalized) <= policy.similar_max_length:
            close = await self._close_name(normalized, policy, ignore_node_id)
            if close is not None:
                return close
        if family and len(normalized) >= policy.root_letters:
            prefix = normalized[: policy.root_letters]
            members = await self._single_word_with_prefix(prefix, ignore_node_id)
            if len(members) >= policy.family_cap:
                return members[0].display
        return None

    async def _close_name(self, normalized: str, policy: NameSimilarityPolicy, ignore_node_id: int | None) -> str | None:
        longest = min(len(normalized) + 1, policy.similar_max_length + 1)
        statement = (
            select(NameRegistryRow)
            .where(
                NameRegistryRow.single_word.is_(True),
                func.length(NameRegistryRow.normalized) >= len(normalized) - 1,
                func.length(NameRegistryRow.normalized) <= longest,
            )
            .order_by(NameRegistryRow.normalized)
        )
        for row in await self.session.scalars(statement):
            if row.node_id == ignore_node_id or row.normalized == normalized:
                continue
            if edit_distance_within_one(row.normalized, normalized):
                return row.display
        return None

    async def _single_word_with_prefix(self, prefix: str, ignore_node_id: int | None) -> list[NameRegistryRow]:
        statement = (
            select(NameRegistryRow)
            .where(NameRegistryRow.normalized >= prefix, NameRegistryRow.normalized < prefix + RANGE_END, NameRegistryRow.single_word.is_(True))
            .order_by(NameRegistryRow.normalized)
        )
        return [row for row in await self.session.scalars(statement) if row.node_id != ignore_node_id]

    async def _row_for(self, node_id: int) -> NameRegistryRow | None:
        row: NameRegistryRow | None = await self.session.scalar(select(NameRegistryRow).where(NameRegistryRow.node_id == node_id))
        return row
