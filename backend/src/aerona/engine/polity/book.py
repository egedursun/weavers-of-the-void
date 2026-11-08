from collections import defaultdict
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import OfficeRow, PolityMemberRow, PolityProfileRow, PolityTerritoryRow, VassalageRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.polity import OfficeKind
from aerona.domain.models.entity_stats import MortalStats
from aerona.engine.primitives.distance import RegionAtlas

SEXES = ("female", "male")


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

    def same_realm(self, first: int, second: int) -> bool:
        realm = self.member_of.get(first)
        return realm is not None and realm == self.member_of.get(second)
