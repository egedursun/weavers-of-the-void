import json
from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.incident_kinds.registry import INCIDENT_KINDS
from aerona.catalog.incident_kinds.spec import IncidentKindSpec
from aerona.constants.engine import FOLDED_TEMPLATE_SUFFIX
from aerona.db.fixups import fixup_due
from aerona.db.tables.changes import StateChangeRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.records import IncidentFactRow
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.records import FactValue, IncidentTier

LEGACY_FIXUP = "records_legacy_w49"
UNPLACED_ROLES = frozenset({IncidentRole.PLACE, IncidentRole.WITNESS, IncidentRole.TELLER})
PLACE_FACT = "place"


@dataclass
class LegacyTally:
    roles: int = 0
    facts: int = 0
    moments: int = 0
    restored: int = 0
    views: int = 0
    retired: int = 0

    @property
    def total(self) -> int:
        return self.roles + self.facts + self.moments + self.restored + self.views + self.retired


def role_order(spec: IncidentKindSpec) -> list[tuple[IncidentRole, bool]]:
    return [(item.role, item.many) for item in spec.roles if item.role not in UNPLACED_ROLES]


def given_roles(spec: IncidentKindSpec, subjects: list[IncidentParticipantRow]) -> list[IncidentRole | None]:
    order = role_order(spec)
    found: list[IncidentRole | None] = []
    for index in range(len(subjects)):
        if index < len(order):
            found.append(order[index][0])
        elif order and order[-1][1]:
            found.append(order[-1][0])
        else:
            found.append(None)
    return found


async def give_roles(session: AsyncSession, incident: IncidentRow, spec: IncidentKindSpec, rows: list[IncidentParticipantRow]) -> int:
    if any(row.role not in {IncidentRole.SUBJECT, *UNPLACED_ROLES} for row in rows):
        return 0
    subjects = sorted((row for row in rows if row.role is IncidentRole.SUBJECT), key=lambda row: (row.position, row.node_id))
    taken = {(row.node_id, row.role) for row in rows}
    changed = 0
    for row, role in zip(subjects, given_roles(spec, subjects), strict=True):
        if role is None or role is IncidentRole.SUBJECT or (row.node_id, role) in taken:
            continue
        taken.discard((row.node_id, row.role))
        row.role = role
        taken.add((row.node_id, role))
        changed += 1
    return changed


def linked_facts(incident: IncidentRow, spec: IncidentKindSpec, rows: list[IncidentParticipantRow], known: set[str]) -> list[IncidentFactRow]:
    by_role: dict[str, list[int]] = defaultdict(list)
    for row in rows:
        by_role[row.role.value].append(row.node_id)
    found: list[IncidentFactRow] = []
    for fact in spec.facts:
        if fact.value is not FactValue.NODE or fact.key in known:
            continue
        if fact.key == PLACE_FACT and incident.place_entity_id is not None:
            found.append(IncidentFactRow(incident_id=incident.id, key=fact.key, position=0, node_id=incident.place_entity_id))
            continue
        nodes = sorted(set(by_role.get(fact.key, [])))
        if len(nodes) == 1 or (fact.many and nodes):
            found.extend(IncidentFactRow(incident_id=incident.id, key=fact.key, position=position, node_id=node) for position, node in enumerate(nodes))
    return found


LEGACY_LINE = "legacy.line"
LEGACY_FOLD = "legacy.fold"
SECOND_LINE = "_note"


def successor_of(kind: str) -> str:
    if kind in INCIDENT_KINDS:
        return kind
    if kind.endswith(FOLDED_TEMPLATE_SUFFIX):
        return LEGACY_FOLD
    if kind.endswith(SECOND_LINE) and kind.removesuffix(SECOND_LINE) in INCIDENT_KINDS:
        return kind.removesuffix(SECOND_LINE)
    return LEGACY_LINE


async def retire_one(session: AsyncSession, incident: IncidentRow) -> None:
    old = incident.kind
    incident.kind = successor_of(old)
    if INCIDENT_KINDS[incident.kind].legacy:
        line = await session.get(ChronicleRow, incident.chronicle_id) if incident.chronicle_id is not None else None
        session.add(IncidentFactRow(incident_id=incident.id, key="legacy_key", position=0, name=old))
        session.add(IncidentFactRow(incident_id=incident.id, key="account", position=0, name=line.text if line is not None else old))


async def retire_kinds(session: AsyncSession, tally: LegacyTally) -> None:
    for incident in await session.scalars(select(IncidentRow).where(IncidentRow.kind.not_in(list(INCIDENT_KINDS))).order_by(IncidentRow.id)):
        await retire_one(session, incident)
        tally.retired += 1
    await session.flush()


async def upgrade_incidents(session: AsyncSession, tally: LegacyTally) -> None:
    participants: dict[int, list[IncidentParticipantRow]] = defaultdict(list)
    for row in await session.scalars(select(IncidentParticipantRow).order_by(IncidentParticipantRow.incident_id, IncidentParticipantRow.position)):
        participants[row.incident_id].append(row)
    facts: dict[int, set[str]] = defaultdict(set)
    for incident_id, key in await session.execute(select(IncidentFactRow.incident_id, IncidentFactRow.key)):
        facts[incident_id].add(key)
    years = {row.id: row.year for row in await session.execute(select(ChronicleRow.id, ChronicleRow.year).where(ChronicleRow.year.is_not(None)))}
    for incident in await session.scalars(select(IncidentRow).where(IncidentRow.tier == IncidentTier.LINE).order_by(IncidentRow.id)):
        if incident.year is None and incident.chronicle_id is not None and years.get(incident.chronicle_id) is not None:
            incident.year = years[incident.chronicle_id]
            tally.moments += 1
        spec = INCIDENT_KINDS.get(incident.kind)
        if spec is None:
            continue
        rows = participants.get(incident.id, [])
        tally.roles += await give_roles(session, incident, spec, rows)
        added = linked_facts(incident, spec, rows, facts.get(incident.id, set()))
        session.add_all(added)
        tally.facts += len(added)
    await session.flush()


def told_kind(row: ChronicleRow) -> ChronicleKind:
    spec = INCIDENT_KINDS.get(row.template_key) if row.template_key else None
    kind = spec.chronicle_kind if spec is not None else ChronicleKind.WORLD
    return ChronicleKind.WORLD if kind is ChronicleKind.ENGINE_RAW else kind


async def hidden_by_hand(session: AsyncSession) -> set[int]:
    keys = await session.scalars(
        select(StateChangeRow.row_key).where(
            StateChangeRow.table_name == ChronicleRow.__tablename__,
            StateChangeRow.field == "visible",
            StateChangeRow.actor_kind.not_in([ActorKind.ENGINE, ActorKind.SYSTEM]),
        )
    )
    return {int(found["id"]) for key in keys if isinstance(found := json.loads(key), dict) and isinstance(found.get("id"), int)}


async def restore_folded(session: AsyncSession, tally: LegacyTally) -> None:
    summaries = select(ChronicleRow).where(ChronicleRow.template_key.like(f"%{FOLDED_TEMPLATE_SUFFIX}"), ChronicleRow.visible.is_(True))
    for row in await session.scalars(summaries.order_by(ChronicleRow.id)):
        row.visible = False
        tally.views += 1
    folded = select(ChronicleRow).where(
        ChronicleRow.kind == ChronicleKind.ENGINE_RAW,
        ChronicleRow.hidden_as_duplicate.is_(False),
        ChronicleRow.template_key.is_not(None),
        ChronicleRow.template_key.not_like(f"%{FOLDED_TEMPLATE_SUFFIX}"),
    )
    chosen = await hidden_by_hand(session)
    for row in await session.scalars(folded.order_by(ChronicleRow.id)):
        row.kind = told_kind(row)
        if row.id not in chosen:
            row.visible = True
            tally.restored += 1
    await session.flush()


async def upgrade_records(session: AsyncSession) -> int:
    if not await fixup_due(session, LEGACY_FIXUP):
        return 0
    tally = LegacyTally()
    await retire_kinds(session, tally)
    await upgrade_incidents(session, tally)
    await restore_folded(session, tally)
    session.add(
        AppliedFixupRow(
            key=LEGACY_FIXUP,
            result={
                "roles": tally.roles,
                "facts": tally.facts,
                "moments": tally.moments,
                "restored": tally.restored,
                "views": tally.views,
                "retired": tally.retired,
            },
        )
    )
    await session.flush()
    return tally.total
