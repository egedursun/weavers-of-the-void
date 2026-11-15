from collections import defaultdict
from dataclasses import dataclass, field, replace

from sqlalchemy import event, inspect, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import ORMExecuteState, Session

from aerona.db.read_memo import memo_of, table_names, touched_rows
from aerona.db.tables.celestial import WorldMapRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import OfficeRow, PolityMemberRow, PolityProfileRow, PolityTerritoryRow, VassalageRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.polity import OfficeKind
from aerona.domain.models.entity_stats import MortalStats
from aerona.engine.primitives.distance import RegionAtlas

SEXES = ("female", "male")
BOOK_TABLES = table_names((PolityProfileRow, PolityMemberRow, PolityTerritoryRow, OfficeRow, VassalageRow, WorldMapRow))
REALM_SHAPE = "aerona.realm_book.shape"
REALM_COLUMNS = ("entity_type", "status")


def realm_shape(sync: Session) -> int:
    found: int = sync.info.setdefault(REALM_SHAPE, 0)
    return found


def reshapes_realms(row: EntityRow) -> bool:
    state = inspect(row)
    kinds = {*state.attrs.entity_type.history.added, *state.attrs.entity_type.history.unchanged, *state.attrs.entity_type.history.deleted}
    return EntityType.POLITY in kinds and any(state.attrs[column].history.has_changes() for column in REALM_COLUMNS)


def realms_pending(sync: Session) -> bool:
    new, dirty, deleted = touched_rows(sync, EntityRow)
    return bool(deleted) or any(row.entity_type is EntityType.POLITY for row in new) or any(reshapes_realms(row) for row in dirty)


def follow_realms(sync: Session, *_: object) -> None:
    if realms_pending(sync):
        sync.info[REALM_SHAPE] = realm_shape(sync) + 1


def reshape_on_write(state: ORMExecuteState) -> None:
    if not state.is_select:
        state.session.info[REALM_SHAPE] = realm_shape(state.session) + 1


event.listen(Session, "after_flush", follow_realms)
event.listen(Session, "do_orm_execute", reshape_on_write)


def sex_of(mortal: EntityRow) -> str:
    stats = mortal.stats
    if not isinstance(stats, MortalStats):
        return SEXES[(mortal.id * 2654435761) % 2]
    if stats.sex is None:
        mortal.stats = stats.model_copy(update={"sex": SEXES[(mortal.id * 2654435761) % 2]})
        return str(mortal.stats.sex)
    return stats.sex


@dataclass
class Realm:
    entity: EntityRow
    profile: PolityProfileRow
    members: dict[int, PolityMemberRow] = field(default_factory=dict)
    territory: dict[int, PolityTerritoryRow] = field(default_factory=dict)
    offices: list[OfficeRow] = field(default_factory=list)

    def office(self, kind: OfficeKind) -> OfficeRow | None:
        return next((row for row in self.offices if row.kind is kind), None)

    @property
    def ruler_id(self) -> int | None:
        office = self.office(OfficeKind.RULER)
        return office.holder_entity_id if office is not None else None


@dataclass
class RealmBook:
    atlas: RegionAtlas
    realms: dict[int, Realm]
    member_of: dict[int, int]
    vassals: dict[int, VassalageRow]
    entities: dict[int, EntityRow]

    @classmethod
    async def load(cls, session: AsyncSession) -> "RealmBook":
        atlas = await RegionAtlas.load(session)
        sync = session.sync_session
        memo = memo_of(session, "realm_book", BOOK_TABLES)
        known: tuple[int, RealmBook] | None = memo.get("book") if memo is not None else None
        if known is not None and known[0] == realm_shape(sync) and not realms_pending(sync):
            if known[1].atlas is not atlas and memo is not None:
                memo["book"] = (known[0], replace(known[1], atlas=atlas))
            found: RealmBook = memo["book"][1] if memo is not None else known[1]
            return found
        if realms_pending(sync):
            await session.flush()
        shape = realm_shape(sync)
        book = await cls.read(session)
        after = memo_of(session, "realm_book", BOOK_TABLES)
        if after is not None and shape == realm_shape(sync):
            after["book"] = (shape, book)
        return book

    @classmethod
    async def read(cls, session: AsyncSession) -> "RealmBook":
        atlas = await RegionAtlas.load(session)
        polities = {
            row.id: row
            for row in await session.scalars(select(EntityRow).where(EntityRow.entity_type == EntityType.POLITY, EntityRow.status == EntityStatus.CANON))
        }
        realms: dict[int, Realm] = {}
        for profile in await session.scalars(select(PolityProfileRow)):
            entity = polities.get(profile.polity_entity_id)
            if entity is not None:
                realms[entity.id] = Realm(entity, profile)
        member_of: dict[int, int] = {}
        for member in await session.scalars(select(PolityMemberRow)):
            realm = realms.get(member.polity_entity_id)
            if realm is not None:
                realm.members[member.member_entity_id] = member
                member_of[member.member_entity_id] = realm.entity.id
        for territory in await session.scalars(select(PolityTerritoryRow)):
            realm = realms.get(territory.polity_entity_id)
            if realm is not None:
                realm.territory[territory.region_entity_id] = territory
        offices: dict[int, list[OfficeRow]] = defaultdict(list)
        for office in await session.scalars(select(OfficeRow).order_by(OfficeRow.id)):
            offices[office.polity_entity_id].append(office)
        for realm_id, rows in offices.items():
            if realm_id in realms:
                realms[realm_id].offices = rows
        vassals = {row.vassal_entity_id: row for row in await session.scalars(select(VassalageRow))}
        ids = {member_id for realm in realms.values() for member_id in realm.members}
        entities = {row.id: row for row in await session.scalars(select(EntityRow).where(EntityRow.id.in_(list(ids))))} if ids else {}
        return cls(atlas, realms, member_of, vassals, entities)

    def realm_of(self, entity_id: int | None) -> Realm | None:
        if entity_id is None:
            return None
        polity_id = self.member_of.get(entity_id)
        return self.realms.get(polity_id) if polity_id is not None else None

    def realm_for(self, node_id: int | None) -> Realm | None:
        if node_id is None:
            return None
        return self.realms.get(node_id) or self.realm_of(node_id)

    def members(self, realm: Realm) -> list[EntityRow]:
        return [self.entities[member_id] for member_id in realm.members if member_id in self.entities and self.entities[member_id].status is EntityStatus.CANON]
