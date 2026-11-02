from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import ColumnElement, case, exists, false, func, select, true

from aerona.catalog.chronicle import chronicle_notification, is_visible
from aerona.core.errors import ValidationFailedError
from aerona.core.random import SeededRandom
from aerona.db.repositories.base import Repository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.lore import ChronicleEntityRow, ChronicleRow, EpochYearCursorRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.chronicle import ChronicleKind, FeedCategory, NotificationCategory
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.models.calendar import YearWindow, chronicle_year


@dataclass(frozen=True)
class ChronicleClock:
    years_per_epoch: int
    window: YearWindow
    pace_divisor: int
    rng: SeededRandom


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
    async def append(self, draft: ChronicleDraft, clock: ChronicleClock | None = None) -> ChronicleWrite:
        text = " ".join(draft.text.split())
        if not text:
            raise ValidationFailedError("A chronicle line cannot be empty.")
        entity_ids = list(dict.fromkeys(entity_id for entity_id in draft.entity_ids if entity_id > 0))
        world_id = draft.world_id if draft.world_id is not None else await self._derive_world(entity_ids, draft.son_id)
        year = (
            await self._exact_year(draft.epoch, draft.year)
            if draft.year is not None
            else await self._stamp_year(draft.epoch, clock)
            if clock is not None
            else None
        )
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
        existing = set(await self.session.scalars(select(EntityRow.id).where(EntityRow.id.in_(entity_ids)))) if entity_ids else set()
        linked = [entity_id for entity_id in entity_ids if entity_id in existing]
        self.session.add_all(ChronicleEntityRow(chronicle_id=row.id, entity_id=entity_id, position=position) for position, entity_id in enumerate(linked))
        incident = IncidentRow(
            kind=draft.template_key or draft.kind.value,
            epoch=draft.epoch,
            year=year,
            world_id=world_id,
            place_entity_id=draft.place_entity_id,
            cause_incident_id=draft.cause_incident_id,
            chronicle_id=row.id,
            magnitude=draft.magnitude,
        )
        await self.insert(incident)
        participants = [
            IncidentParticipantRow(incident_id=incident.id, node_id=entity_id, role=IncidentRole.SUBJECT, position=position)
            for position, entity_id in enumerate(linked)
        ]
        if draft.son_id is not None:
            participants.append(IncidentParticipantRow(incident_id=incident.id, node_id=draft.son_id, role=IncidentRole.ACTOR, position=0))
        self.session.add_all(participants)
        await self.flush()
        return ChronicleWrite(row, chronicle_notification(draft.kind, draft.feed_category), incident.id)

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
            .where(ChronicleEntityRow.entity_id == entity_id)
            .order_by(ChronicleRow.id.desc())
            .limit(limit)
        )
        return list(await self.session.scalars(statement))

    async def last_year(self, epoch: int) -> int | None:
        cursor = await self.session.get(EpochYearCursorRow, epoch)
        return cursor.last_year if cursor is not None else None

    async def _exact_year(self, epoch: int, year: int) -> int:
        cursor = await self.session.get(EpochYearCursorRow, epoch)
        if cursor is None:
            self.session.add(EpochYearCursorRow(epoch=epoch, last_year=year))
        elif year > cursor.last_year:
            cursor.last_year = year
        return year

    async def _stamp_year(self, epoch: int, clock: ChronicleClock) -> int:
        cursor = await self.session.get(EpochYearCursorRow, epoch)
        year = chronicle_year(
            epoch=epoch,
            years_per_epoch=clock.years_per_epoch,
            window=clock.window,
            last_year=cursor.last_year if cursor else None,
            roll=clock.rng.random(),
            pace_divisor=clock.pace_divisor,
        )
        if cursor is None:
            self.session.add(EpochYearCursorRow(epoch=epoch, last_year=year))
        else:
            cursor.last_year = year
        return year

    async def _derive_world(self, entity_ids: list[int], son_id: int | None) -> int | None:
        if entity_ids:
            worlds = set(await self.session.scalars(select(EntityRow.world_id).where(EntityRow.id.in_(entity_ids))))
            if len(worlds) == 1:
                return worlds.pop()
            if worlds:
                return None
        if son_id is not None:
            son_world: int | None = await self.session.scalar(select(SonRow.current_world_id).where(SonRow.id == son_id))
            return son_world
        return None
