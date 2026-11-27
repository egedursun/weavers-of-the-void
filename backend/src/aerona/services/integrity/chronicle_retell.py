import hashlib
from bisect import bisect_right
from collections import defaultdict
from dataclasses import dataclass, field
from itertools import batched

from sqlalchemy import ColumnElement, Select, and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.text import replace_name
from aerona.catalog.incident_kinds.registry import INCIDENT_KINDS
from aerona.db.fixups import marked, marker_key, settle, unmark
from aerona.db.tables.changes import StateChangeRow
from aerona.db.tables.gatherings import CollectionRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.records import IncidentFactRow
from aerona.domain.enums.node import ActorKind
from aerona.engine.recording.accounts import AccountFact, AccountParticipant, Names, retold

TOLD_PREFIX = "chronicle.told."
NAMES_PREFIX = "chronicle.renamed."
WORDED_SCAN_MOST = 40
CHUNK = 500
Moment = tuple[int, int]


@dataclass(frozen=True)
class Retelling:
    kinds: int
    lines: int
    changed: int


@dataclass
class NamesThen:
    now: Names
    changes: dict[int, list[tuple[Moment, str]]] = field(default_factory=dict)
    renamed: dict[str, str] = field(default_factory=dict)

    @classmethod
    async def load(cls, session: AsyncSession) -> "NamesThen":
        found: dict[int, list[tuple[Moment, str]]] = defaultdict(list)
        rows = await session.execute(
            select(StateChangeRow.node_id, StateChangeRow.epoch, StateChangeRow.year, StateChangeRow.before_text)
            .where(StateChangeRow.table_name == NodeRow.__tablename__, StateChangeRow.field == "name", StateChangeRow.actor_kind == ActorKind.ENGINE)
            .order_by(StateChangeRow.id)
        )
        for node, epoch, year, before in rows:
            if node is not None and before:
                found[node].append(((epoch, year or 0), before))
        return cls(Names(session), {node: sorted(items) for node, items in found.items()}, await renamed_texts(session))

    def retold_text(self, text: str | None) -> str | None:
        if not text:
            return text
        for old in sorted(self.renamed, key=len, reverse=True):
            if old in text:
                text = replace_name(text, old, self.renamed[old])
        return text

    def of(self, node_id: int | None, moment: Moment) -> str | None:
        if node_id is None:
            return None
        later = self.changes.get(node_id, [])
        index = bisect_right([when for when, _ in later], moment)
        return later[index][1] if index < len(later) else self.now.of(node_id)


async def renamed_texts(session: AsyncSession) -> dict[str, str]:
    rows = await session.execute(
        select(StateChangeRow.before_text, StateChangeRow.after_text)
        .where(
            StateChangeRow.field == "name",
            or_(
                and_(StateChangeRow.table_name == NodeRow.__tablename__, StateChangeRow.actor_kind != ActorKind.ENGINE),
                StateChangeRow.table_name == CollectionRow.__tablename__,
            ),
        )
        .order_by(StateChangeRow.id)
    )
    found: dict[str, str] = {}
    for before, after in rows:
        if before and after and before != after:
            found = {old: (after if new == before else new) for old, new in found.items()}
            found[before] = after
    return {old: new for old, new in found.items() if old != new}


async def participants_of(session: AsyncSession, names: NamesThen, moments: dict[int, Moment]) -> dict[int, list[AccountParticipant]]:
    found: dict[int, list[AccountParticipant]] = defaultdict(list)
    rows = list(
        await session.scalars(
            select(IncidentParticipantRow)
            .where(IncidentParticipantRow.incident_id.in_(sorted(moments)))
            .order_by(IncidentParticipantRow.incident_id, IncidentParticipantRow.position, IncidentParticipantRow.role, IncidentParticipantRow.node_id)
        )
    )
    await names.now.load(row.node_id for row in rows)
    for row in rows:
        found[row.incident_id].append(
            AccountParticipant(row.node_id, names.of(row.node_id, moments[row.incident_id]), row.role, row.position, row.witness_mode, row.fidelity)
        )
    return found


async def facts_of(session: AsyncSession, names: NamesThen, moments: dict[int, Moment]) -> dict[int, list[AccountFact]]:
    found: dict[int, list[AccountFact]] = defaultdict(list)
    rows = list(
        await session.scalars(
            select(IncidentFactRow)
            .where(IncidentFactRow.incident_id.in_(sorted(moments)))
            .order_by(IncidentFactRow.incident_id, IncidentFactRow.key, IncidentFactRow.position)
        )
    )
    await names.now.load(row.node_id for row in rows)
    for row in rows:
        named = names.of(row.node_id, moments[row.incident_id])
        found[row.incident_id].append(
            AccountFact(row.id, row.key, row.position, row.node_id, named, row.number, row.unit, row.enum_name, row.enum_value, names.retold_text(row.name))
        )
    return found


def told_key(kind: str) -> str:
    template = INCIDENT_KINDS[kind].template or ""
    return marker_key(f"{TOLD_PREFIX}{kind}.{hashlib.blake2s(template.encode(), digest_size=6).hexdigest()}")


async def kinds_told_by_old_templates(session: AsyncSession) -> list[str]:
    settled = await marked(session, TOLD_PREFIX)
    kinds = await session.scalars(select(IncidentRow.kind).where(IncidentRow.chronicle_id.is_not(None)).distinct().order_by(IncidentRow.kind))
    return [kind for kind in kinds if kind in INCIDENT_KINDS and told_key(kind) not in settled]


async def retell_incidents(session: AsyncSession, incidents: list[tuple[int, str, int | None, int, int | None]], names: NamesThen) -> int:
    changed = 0
    for part in batched(incidents, CHUNK, strict=False):
        moments = {incident: (epoch, year or 0) for incident, _, _, epoch, year in part}
        people, facts = await participants_of(session, names, moments), await facts_of(session, names, moments)
        lines = {line.id: line for line in await session.scalars(select(ChronicleRow).where(ChronicleRow.id.in_([line for _, _, line, _, _ in part])))}
        for incident, kind, line_id, _, _ in part:
            line = lines.get(line_id) if line_id is not None else None
            if line is None or line.author_account_id is not None or kind not in INCIDENT_KINDS:
                continue
            told = retold(INCIDENT_KINDS[kind], people.get(incident, []), facts.get(incident, []))
            if told and told != line.text:
                line.text = told
                changed += 1
    return changed


def told_rows(where: ColumnElement[bool]) -> Select[int, str, int | None, int, int | None]:
    return (
        select(IncidentRow.id, IncidentRow.kind, IncidentRow.chronicle_id, IncidentRow.epoch, IncidentRow.year)
        .where(where, IncidentRow.chronicle_id.is_not(None))
        .order_by(IncidentRow.id)
    )


async def renamed_since(session: AsyncSession) -> tuple[list[int], list[str], int]:
    settled = sorted(int(key.rsplit(".", 1)[1]) for key in await marked(session, NAMES_PREFIX))
    since = settled[-1] if settled else 0
    rows = list(
        await session.execute(
            select(StateChangeRow.id, StateChangeRow.node_id, StateChangeRow.before_text)
            .where(
                StateChangeRow.id > since,
                StateChangeRow.field == "name",
                or_(
                    and_(StateChangeRow.table_name == NodeRow.__tablename__, StateChangeRow.actor_kind != ActorKind.ENGINE),
                    StateChangeRow.table_name == CollectionRow.__tablename__,
                ),
            )
            .order_by(StateChangeRow.id)
        )
    )
    nodes = sorted({node for _, node, _ in rows if node is not None})
    old = sorted({before for _, _, before in rows if before})
    return nodes, old, (rows[-1][0] if rows else since)


async def retell_renamed(session: AsyncSession, names: NamesThen) -> tuple[int, int]:
    nodes, old, last = await renamed_since(session)
    if not nodes and not old:
        return 0, 0
    if len(old) > WORDED_SCAN_MOST:
        touched = told_rows(IncidentRow.chronicle_id.is_not(None))
    else:
        named = select(IncidentParticipantRow.incident_id).where(IncidentParticipantRow.node_id.in_(nodes))
        facts = select(IncidentFactRow.incident_id).where(IncidentFactRow.node_id.in_(nodes))
        worded = select(IncidentFactRow.incident_id).where(or_(*(IncidentFactRow.name.contains(name) for name in old))) if old else None
        found = [IncidentRow.id.in_(named), IncidentRow.id.in_(facts), *([IncidentRow.id.in_(worded)] if worded is not None else [])]
        touched = told_rows(or_(*found))
    incidents = [(one, kind, line, epoch, year) for one, kind, line, epoch, year in await session.execute(touched)]
    changed = await retell_incidents(session, incidents, names)
    await unmark(session, NAMES_PREFIX)
    await settle(session, marker_key(f"{NAMES_PREFIX}{last}"), {"lines": len(incidents), "changed": changed})
    return len(incidents), changed


async def retell_old_lines(session: AsyncSession) -> int:
    return (await retelling(session)).changed


async def retelling(session: AsyncSession) -> Retelling:
    kinds = await kinds_told_by_old_templates(session)
    names = await NamesThen.load(session)
    lines = changed = 0
    for kind in kinds:
        incidents = [(one, kind, line, epoch, year) for one, kind, line, epoch, year in await session.execute(told_rows(IncidentRow.kind == kind))]
        moved = await retell_incidents(session, incidents, names)
        lines, changed = lines + len(incidents), changed + moved
        await unmark(session, f"{TOLD_PREFIX}{kind}.")
        await settle(session, told_key(kind), {"lines": len(incidents), "changed": moved})
        await session.flush()
    counted, moved = await retell_renamed(session, names)
    await session.flush()
    return Retelling(len(kinds), lines + counted, changed + moved)
