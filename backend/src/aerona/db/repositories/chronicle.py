from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field

from sqlalchemy import ColumnElement, and_, case, event, exists, false, func, or_, select, true
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from aerona.catalog.chronicle import chronicle_notification, is_visible
from aerona.catalog.incident_roles import positional_role
from aerona.constants.engine import FOLDED_TEMPLATE_SUFFIX
from aerona.constants.units import PERCENT
from aerona.core.errors import ValidationFailedError
from aerona.db.fast_session import rows_by_id
from aerona.db.repositories.base import Repository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.lore import ChronicleEntityRow, ChronicleRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.chronicle import ChronicleKind, FeedCategory, NotificationCategory
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import IncidentTier


@dataclass(frozen=True)
class ChronicleDraft:
    epoch: int
    kind: ChronicleKind
    text: str
    entity_ids: Sequence[int] = ()
    son_id: int | None = None
    world_id: int | None = None
    feed_category: FeedCategory | None = None
    template_key: str | None = None
    cause_incident_id: int | None = None
    place_entity_id: int | None = None
    magnitude: int = 0
    year: int | None = None
    roles: Mapping[int, IncidentRole] = field(default_factory=dict)
    participants: Sequence[tuple[int, IncidentRole]] = ()
    incident_id: int | None = None
    season: int | None = None
    day: int | None = None
    hour: int | None = None
    origin_entity_id: int | None = None
    destination_entity_id: int | None = None
    tier: IncidentTier = IncidentTier.LINE


@dataclass(frozen=True)
class LastIncident:
    incident_id: int
    epoch: int
    participants: frozenset[int]


LAST_INCIDENT = "last_incident"


def folded_away() -> ColumnElement[bool]:
    return and_(ChronicleRow.kind == ChronicleKind.ENGINE_RAW, ChronicleRow.hidden_as_duplicate.is_(False))


def not_a_fold() -> ColumnElement[bool]:
    return func.coalesce(ChronicleRow.template_key, "").not_like(f"%{FOLDED_TEMPLATE_SUFFIX}")


def shown_lines() -> ColumnElement[bool]:
    return and_(or_(ChronicleRow.visible.is_(True), folded_away()), not_a_fold())


def kept_lines() -> ColumnElement[bool]:
    return and_(or_(ChronicleRow.kind != ChronicleKind.ENGINE_RAW, folded_away()), not_a_fold())


def feed_lines() -> ColumnElement[bool]:
    return ChronicleRow.visible.is_(True)


def told_kind(row: ChronicleRow) -> ChronicleKind:
    return ChronicleKind.WORLD if row.kind is ChronicleKind.ENGINE_RAW else row.kind


CAUSE_SCOPE: ContextVar[int | None] = ContextVar("cause_scope", default=None)


def scoped_cause() -> int | None:
    return CAUSE_SCOPE.get()


@contextmanager
def caused_by(incident_id: int | None) -> Iterator[None]:
    token = CAUSE_SCOPE.set(incident_id if incident_id is not None else CAUSE_SCOPE.get())
    try:
        yield
    finally:
        CAUSE_SCOPE.reset(token)


KIND_WEIGHTS: dict[ChronicleKind, int] = {
    ChronicleKind.WAR: 50,
    ChronicleKind.DEATH: 40,
    ChronicleKind.DISASTER: 45,
    ChronicleKind.COSMIC: 50,
    ChronicleKind.FOREIGN_GOD: 40,
    ChronicleKind.LINEAGE: 20,
    ChronicleKind.CLIMATE: 25,
}
DEFAULT_WEIGHT = 15
PARTICIPANT_WEIGHT = 5
QUIET_ROLES = (IncidentRole.WITNESS, IncidentRole.PLACE)


def incident_for(session: AsyncSession | Session, node_id: int, epoch: int) -> int | None:
    last = session.info.get(LAST_INCIDENT)
    return last.incident_id if last is not None and last.epoch == epoch and node_id in last.participants else None


def typed_participants(incident_id: int, given: Sequence[tuple[int, IncidentRole]]) -> list[IncidentParticipantRow]:
    rows: list[IncidentParticipantRow] = []
    seen: set[tuple[int, IncidentRole]] = set()
    places: dict[IncidentRole, int] = {}
    for node_id, role in given:
        if (node_id, role) in seen:
            continue
        seen.add((node_id, role))
        rows.append(IncidentParticipantRow(incident_id=incident_id, node_id=node_id, role=role, position=places.get(role, 0)))
        places[role] = places.get(role, 0) + 1
    return rows


@dataclass(frozen=True)
class ChronicleWrite:
    row: ChronicleRow
    notification: NotificationCategory | None
    incident_id: int | None = None


def in_world(world_id: int, primary_world_id: int) -> ColumnElement[bool]:
    linked = select(ChronicleEntityRow.entity_id).where(ChronicleEntityRow.chronicle_id == ChronicleRow.id)
    outside = (
        select(ChronicleEntityRow.entity_id)
        .join(EntityRow, EntityRow.id == ChronicleEntityRow.entity_id)
        .where(ChronicleEntityRow.chronicle_id == ChronicleRow.id, EntityRow.world_id != world_id)
    )
    son_world = select(func.coalesce(SonRow.current_world_id, primary_world_id)).where(SonRow.id == ChronicleRow.son_id).scalar_subquery()
    return case(
        (exists(linked), ~exists(outside)),
        (ChronicleRow.world_id.is_not(None), ChronicleRow.world_id == world_id),
        (ChronicleRow.son_id.is_not(None), func.coalesce(son_world, primary_world_id) == world_id),
        else_=true() if world_id == primary_world_id else false(),
    )


class ChronicleRepository(Repository):
    async def append(self, draft: ChronicleDraft) -> ChronicleWrite:
        text = " ".join(draft.text.split())
        if not text:
            raise ValidationFailedError("A chronicle line cannot be empty.")
        entity_ids = list(dict.fromkeys(entity_id for entity_id in draft.entity_ids if entity_id > 0))
        await self.flush()
        entities = await rows_by_id(self.session, EntityRow, entity_ids)
        world_id = draft.world_id if draft.world_id is not None else await self._derive_world(list(entities.values()), draft.son_id)
        involved = [*entity_ids, *([draft.son_id] if draft.son_id is not None else [])]
        scoped = CAUSE_SCOPE.get()
        cause = draft.cause_incident_id if draft.cause_incident_id is not None else scoped
        year = draft.year
        row = ChronicleRow(
            epoch=draft.epoch,
            year=year,
            kind=draft.kind,
            visible=is_visible(draft.kind),
            feed_category=draft.feed_category,
            template_key=draft.template_key,
            son_id=draft.son_id,
            world_id=world_id,
            text=text,
        )
        await self.insert(row)
        existing = set(entities)
        linked = [entity_id for entity_id in entity_ids if entity_id in existing]
        self.session.add_all(ChronicleEntityRow(chronicle_id=row.id, entity_id=entity_id, position=position) for position, entity_id in enumerate(linked))
        involved = [*linked, *([draft.son_id] if draft.son_id is not None else [])]
        magnitude = draft.magnitude or min(PERCENT, KIND_WEIGHTS.get(draft.kind, DEFAULT_WEIGHT) + PARTICIPANT_WEIGHT * len(involved))
        incident = await self.incident_for(draft, year=year, world_id=world_id, cause=cause, chronicle_id=row.id, magnitude=magnitude)
        participants = (
            typed_participants(incident.id, draft.participants)
            if draft.participants
            else [
                IncidentParticipantRow(
                    incident_id=incident.id,
                    node_id=entity_id,
                    role=draft.roles.get(entity_id) or positional_role(draft.template_key, entity_ids.index(entity_id)) or IncidentRole.SUBJECT,
                    position=position,
                )
                for position, entity_id in enumerate(linked)
            ]
        )
        if draft.participants:
            linked = [node for node, _ in draft.participants]
        if draft.son_id is not None and draft.son_id not in linked:
            acted = any(row.role is IncidentRole.ACTOR for row in participants)
            role = IncidentRole.ALLY if acted else IncidentRole.ACTOR
            participants.append(IncidentParticipantRow(incident_id=incident.id, node_id=draft.son_id, role=role, position=0))
        if draft.place_entity_id is not None and draft.place_entity_id not in linked and draft.place_entity_id in existing:
            participants.append(IncidentParticipantRow(incident_id=incident.id, node_id=draft.place_entity_id, role=IncidentRole.PLACE, position=len(linked)))
        self.session.add_all(participants)
        await self.flush()
        self.session.info[LAST_INCIDENT] = LastIncident(incident.id, draft.epoch, frozenset(involved))
        return ChronicleWrite(row, chronicle_notification(draft.kind, draft.feed_category), incident.id)

    async def incident_for(
        self, draft: ChronicleDraft, *, year: int | None, world_id: int | None, cause: int | None, chronicle_id: int, magnitude: int
    ) -> IncidentRow:
        found = await self.session.get(IncidentRow, draft.incident_id) if draft.incident_id is not None else None
        incident = found or IncidentRow(epoch=draft.epoch)
        incident.kind = draft.template_key or draft.kind.value
        incident.year = year if year is not None else incident.year
        incident.season = draft.season if draft.season is not None else incident.season
        incident.day = draft.day if draft.day is not None else incident.day
        incident.hour = draft.hour if draft.hour is not None else incident.hour
        incident.world_id = world_id if world_id is not None else incident.world_id
        incident.place_entity_id = draft.place_entity_id if draft.place_entity_id is not None else incident.place_entity_id
        incident.origin_entity_id = draft.origin_entity_id
        incident.destination_entity_id = draft.destination_entity_id
        incident.cause_incident_id = cause if cause is not None and cause != incident.id else incident.cause_incident_id
        incident.chronicle_id = chronicle_id
        incident.magnitude = magnitude
        incident.tier = draft.tier
        if found is None:
            await self.insert(incident)
        return incident

    async def prior_incident(self, node_ids: Sequence[int], kinds: Sequence[str] = (), *, before_epoch: int | None = None, shared: bool = False) -> int | None:
        wanted = list(dict.fromkeys(node_ids))
        if not wanted:
            return None
        statement = (
            select(IncidentRow.id)
            .join(IncidentParticipantRow, IncidentParticipantRow.incident_id == IncidentRow.id)
            .where(IncidentParticipantRow.node_id.in_(wanted), IncidentParticipantRow.role.not_in(QUIET_ROLES))
        )
        if kinds:
            statement = statement.where(or_(*(IncidentRow.kind.startswith(kind) for kind in kinds)))
        if before_epoch is not None:
            statement = statement.where(IncidentRow.epoch <= before_epoch)
        statement = statement.group_by(IncidentRow.id)
        if shared and len(wanted) > 1:
            statement = statement.having(func.count(func.distinct(IncidentParticipantRow.node_id)) >= len(wanted))
        found: int | None = await self.session.scalar(statement.order_by(IncidentRow.id.desc()).limit(1))
        return found

    async def witness(self, incident_id: int, node_ids: Sequence[int]) -> None:
        present = set(await self.session.scalars(select(IncidentParticipantRow.node_id).where(IncidentParticipantRow.incident_id == incident_id)))
        self.session.add_all(
            IncidentParticipantRow(incident_id=incident_id, node_id=node_id, role=IncidentRole.WITNESS, position=index)
            for index, node_id in enumerate(node_ids)
            if node_id not in present
        )

    async def entity_ids(self, chronicle_id: int) -> list[int]:
        statement = select(ChronicleEntityRow.entity_id).where(ChronicleEntityRow.chronicle_id == chronicle_id).order_by(ChronicleEntityRow.position)
        return list(await self.session.scalars(statement))

    async def recent(self, limit: int, world_id: int | None = None, visible_only: bool = True, primary_world_id: int | None = None) -> list[ChronicleRow]:
        statement = select(ChronicleRow)
        if visible_only:
            statement = statement.where(ChronicleRow.visible.is_(True), ChronicleRow.hidden_as_duplicate.is_(False))
        if world_id is not None:
            statement = statement.where(in_world(world_id, primary_world_id if primary_world_id is not None else world_id))
        rows = list(await self.session.scalars(statement.order_by(ChronicleRow.id.desc()).limit(limit)))
        return list(reversed(rows))

    async def for_epoch(self, epoch: int, visible_only: bool = True) -> list[ChronicleRow]:
        statement = select(ChronicleRow).where(ChronicleRow.epoch == epoch)
        if visible_only:
            statement = statement.where(ChronicleRow.visible.is_(True))
        return list(await self.session.scalars(statement.order_by(ChronicleRow.id)))

    async def mentioning(self, entity_id: int, limit: int) -> list[ChronicleRow]:
        statement = (
            select(ChronicleRow)
            .join(ChronicleEntityRow, ChronicleEntityRow.chronicle_id == ChronicleRow.id)
            .where(ChronicleEntityRow.entity_id == entity_id, ChronicleRow.kind != ChronicleKind.SPEECH)
            .order_by(ChronicleRow.id.desc())
            .limit(limit)
        )
        return list(await self.session.scalars(statement))

    async def _derive_world(self, entities: list[EntityRow], son_id: int | None) -> int | None:
        if entities:
            worlds = {entity.world_id for entity in entities}
            if len(worlds) == 1:
                return worlds.pop()
            if worlds:
                return None
        if son_id is not None:
            son_world: int | None = await self.session.scalar(select(SonRow.current_world_id).where(SonRow.id == son_id))
            return son_world
        return None


def forget_incident(session: Session, *_: object) -> None:
    session.info.pop(LAST_INCIDENT, None)


event.listen(Session, "after_soft_rollback", forget_incident)
