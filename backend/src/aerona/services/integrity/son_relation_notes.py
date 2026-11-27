import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.grudge_fragments import GRUDGE_FRAGMENTS
from aerona.constants.schema import KEY_MAX_LENGTH
from aerona.db.repositories.bonds import BondRepository
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.repositories.sons import ordered_pair
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.changes import StateChangeRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.sons import SonRelationRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.mind import MemoryKind


def told_plainly(note: str | None) -> bool:
    text = (note or "").strip()
    return not text or text[0].isupper()


async def fragment_rows(session: AsyncSession, son_a_id: int | None = None) -> list[SonRelationRow]:
    statement = select(SonRelationRow).order_by(SonRelationRow.son_a_id, SonRelationRow.son_b_id)
    if son_a_id is not None:
        statement = statement.where(SonRelationRow.son_a_id == son_a_id)
    return [row for row in await session.scalars(statement) if not told_plainly(row.note) and not held(row.son_a_id, row.son_b_id)]


async def bonds_described_by_a_fragment(session: AsyncSession) -> list[int]:
    return sorted({row.son_a_id for row in await fragment_rows(session)})


async def last_description(session: AsyncSession, first: int, second: int) -> str:
    key = json.dumps({"son_a_id": first, "son_b_id": second})
    changes = await session.scalars(
        select(StateChangeRow)
        .where(StateChangeRow.table_name == SonRelationRow.__tablename__, StateChangeRow.row_key == key, StateChangeRow.field == "note")
        .order_by(StateChangeRow.id.desc())
    )
    for change in changes:
        for text in (change.after_text, change.before_text):
            if text and told_plainly(text):
                return text
    return ""


async def restore_bond_description(session: AsyncSession, son_a_id: int) -> None:
    for row in await fragment_rows(session, son_a_id):
        row.note = await last_description(session, row.son_a_id, row.son_b_id)


def named_grudge(kind: MemoryKind, note: str, holder: str, subject: str) -> str | None:
    pattern = GRUDGE_FRAGMENTS.get(kind)
    found = pattern.match(note) if pattern is not None else None
    if found is None:
        return None
    place = found.group("place")
    if kind is MemoryKind.HUMILIATED_ME:
        return f"{subject} overcame {holder} in the battle for {place}"[:KEY_MAX_LENGTH]
    if kind is MemoryKind.STOLE_FAITHFUL:
        return f"{subject} took {place} from {holder}"[:KEY_MAX_LENGTH]
    return f"{subject} blessed {place}"[:KEY_MAX_LENGTH]


async def nameless_grudges(session: AsyncSession) -> list[int]:
    rows = await session.scalars(select(MemoryRow).where(MemoryRow.kind.in_(list(GRUDGE_FRAGMENTS))).order_by(MemoryRow.id))
    return sorted(
        {row.holder_node_id for row in rows if row.note and GRUDGE_FRAGMENTS[row.kind].match(row.note) and not held(row.holder_node_id, row.subject_node_id)}
    )


async def name_both_in_grudges(session: AsyncSession, holder_id: int) -> None:
    holder = await session.get(NodeRow, holder_id)
    rows = await session.scalars(
        select(MemoryRow).where(MemoryRow.holder_node_id == holder_id, MemoryRow.kind.in_(list(GRUDGE_FRAGMENTS))).order_by(MemoryRow.id)
    )
    for row in rows:
        subject = await session.get(NodeRow, row.subject_node_id)
        if holder is None or subject is None or not row.note:
            continue
        named = named_grudge(row.kind, row.note, holder.name, subject.name)
        if named is not None:
            row.note = named


async def covenants_between_enemies(session: AsyncSession) -> list[int]:
    floor = -(await CosmosRepository(session).rules()).son_tools.covenant_min_relation
    found: set[int] = set()
    for bond in await session.scalars(select(BondRow).where(BondRow.kind == BondKind.ALLY, BondRow.state == BondState.ACTIVE).order_by(BondRow.id)):
        relation = await session.get(SonRelationRow, ordered_pair(bond.source_node_id, bond.target_node_id))
        if relation is not None and relation.value <= floor and not held(bond.source_node_id, bond.target_node_id):
            found.add(bond.id)
    return sorted(found)


async def end_covenant_of_enemies(session: AsyncSession, bond_id: int) -> None:
    bond = await session.get(BondRow, bond_id)
    cosmos = await CosmosRepository(session).get()
    if bond is not None and bond.state is BondState.ACTIVE:
        await BondRepository(session).deactivate(bond, cosmos.epoch if cosmos is not None else bond.epoch, "enmity")
