from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

from sqlalchemy import delete, select

from aerona.catalog.entity_types import can_contain, engine_kind_owner
from aerona.core.errors import ConflictError, NotFoundError, ValidationFailedError
from aerona.core.grammar import an, spoken
from aerona.db.repositories.base import Repository
from aerona.db.repositories.bonds import BondRepository
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.repositories.names import NameRepository, clean_display, normalize_name
from aerona.db.tables.entities import CreationVerdictRow, EntityFlagRow, EntityRow, EntityTagRow, EntityTraitRow
from aerona.db.tables.sons import SonRow
from aerona.db.write_guard import held
from aerona.domain.enums.agent import Verdict
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EngineKind, EntityFlag, EntityOrigin, EntityStatus, EntityType, LegendCategory, MortalRole
from aerona.domain.enums.society import CreatureTrait, KnowledgeBranch, NaturalLaw, ResourceMechanic, SocialClass
from aerona.domain.models.entity_stats import EntityStats

JUDGED_ORIGINS = frozenset({EntityOrigin.SON, EntityOrigin.MORTAL})
TITLE_SEPARATOR = ","
MINIMUM_EPITHET_LENGTH = 3


@dataclass(frozen=True)
class EntityDraft:
    name: str
    entity_type: EntityType
    description: str
    stats: EntityStats
    power_level: int
    origin: EntityOrigin
    birth_epoch: int
    world_id: int | None = None
    location_id: int | None = None
    creator_son_id: int | None = None
    maker_entity_id: int | None = None
    title: str | None = None
    subtype: str | None = None
    engine_kind: EngineKind | None = None
    mortal_role: MortalRole | None = None
    domain: Domain | None = None
    pending_name: bool = False
    knowledge_branch: KnowledgeBranch | None = None
    natural_law: NaturalLaw | None = None
    resource_mechanic: ResourceMechanic | None = None
    sacred_to_son_id: int | None = None
    legend_category: LegendCategory | None = None
    social_class: SocialClass | None = None
    affiliated_entity_id: int | None = None
    is_underworld: bool = False
    is_water: bool = False
    sanity: int | None = None
    image_prompt: str | None = None
    flags: Sequence[EntityFlag] = ()
    tags: Sequence[str] = ()
    traits: Sequence[CreatureTrait] = ()
    split_title: bool = field(default=True)


def split_epithet(name: str) -> tuple[str, str | None]:
    display = clean_display(name)
    head, separator, tail = display.partition(TITLE_SEPARATOR)
    head, tail = head.strip(), tail.strip()
    if not separator or " " in head or not head or len(tail) < MINIMUM_EPITHET_LENGTH:
        return display, None
    return head, tail


class EntityRepository(Repository):
    async def create(self, draft: EntityDraft) -> EntityRow:
        self._validate_shape(draft)
        names = NameRepository(self.session)
        name, title = await self._resolve_name(names, draft)
        location = await self._validated_location(draft.entity_type, draft.location_id)
        world_id = await self._resolve_world(draft, location)
        entity = EntityRow(
            name=name,
            title=title,
            entity_type=draft.entity_type,
            subtype=draft.subtype,
            engine_kind=draft.engine_kind,
            mortal_role=draft.mortal_role,
            description=draft.description,
            stats=draft.stats,
            power_level=draft.power_level,
            domain=draft.domain,
            origin=draft.origin,
            creator_son_id=draft.creator_son_id,
            maker_entity_id=draft.maker_entity_id,
            world_id=world_id,
            location_id=draft.location_id,
            status=EntityStatus.CANON,
            pending_name=draft.pending_name,
            birth_epoch=draft.birth_epoch,
            knowledge_branch=draft.knowledge_branch,
            natural_law=draft.natural_law,
            resource_mechanic=draft.resource_mechanic,
            sacred_to_son_id=draft.sacred_to_son_id,
            legend_category=draft.legend_category,
            social_class=draft.social_class,
            affiliated_entity_id=draft.affiliated_entity_id,
            is_underworld=draft.is_underworld,
            is_water=draft.is_water,
            sanity=draft.sanity,
            image_prompt=draft.image_prompt,
        )
        await self.insert(entity)
        entity.name = await names.claim(entity.id, name)
        if draft.origin in JUDGED_ORIGINS:
            self.session.add(CreationVerdictRow(entity_id=entity.id, epoch=draft.birth_epoch, verdict=Verdict.UNJUDGED))
        self.session.add_all(EntityFlagRow(entity_id=entity.id, flag=flag, epoch=draft.birth_epoch) for flag in dict.fromkeys(draft.flags))
        self.session.add_all(EntityTagRow(entity_id=entity.id, tag=tag) for tag in dict.fromkeys(self._clean_tags(draft.tags)))
        self.session.add_all(EntityTraitRow(entity_id=entity.id, trait=trait) for trait in dict.fromkeys(draft.traits))
        await self.flush()
        if location is not None:
            await BondRepository(self.session).refresh_location(entity.id, location.id, draft.birth_epoch)
        return entity

    async def get(self, entity_id: int) -> EntityRow | None:
        return await self.session.get(EntityRow, entity_id)

    async def require_entity(self, entity_id: int) -> EntityRow:
        return await self.require(EntityRow, entity_id, "record")

    async def by_name(self, name: str) -> EntityRow | None:
        owner = await NameRepository(self.session).owner(name)
        return await self.session.get(EntityRow, owner) if owner is not None else None

    async def canon(self, entity_type: EntityType | None = None, world_id: int | None = None) -> list[EntityRow]:
        statement = select(EntityRow).where(EntityRow.status == EntityStatus.CANON)
        if entity_type is not None:
            statement = statement.where(EntityRow.entity_type == entity_type)
        if world_id is not None:
            statement = statement.where(EntityRow.world_id == world_id)
        return list(await self.session.scalars(statement.order_by(EntityRow.id)))

    async def contents(self, location_id: int, statuses: Iterable[EntityStatus] = (EntityStatus.CANON,)) -> list[EntityRow]:
        statement = select(EntityRow).where(EntityRow.location_id == location_id, EntityRow.status.in_(list(statuses)))
        return list(await self.session.scalars(statement.order_by(EntityRow.id)))

    async def move(self, entity: EntityRow, location_id: int | None, epoch: int) -> EntityRow:
        location = await self._validated_location(entity.entity_type, location_id)
        if location is not None:
            await self._ensure_no_cycle(entity.id, location)
            entity.world_id = location.world_id
        entity.location_id = location_id
        await self.flush()
        await BondRepository(self.session).refresh_location(entity.id, location_id, epoch)
        return entity

    async def transfer_contents(self, old_location: EntityRow, epoch: int) -> int:
        moved = 0
        for item in await self.contents(old_location.id, (EntityStatus.CANON, EntityStatus.FULFILLED)):
            if old_location.location_id is not None and not can_contain(await self._type_of(old_location.location_id), item.entity_type):
                item.location_id = None
                await BondRepository(self.session).refresh_location(item.id, None, epoch)
            else:
                await self.move(item, old_location.location_id, epoch)
            moved += 1
        return moved

    async def set_status(self, entity: EntityRow, status: EntityStatus, epoch: int, fate_note: str | None = None) -> EntityRow:
        previous = entity.status
        if previous is status:
            return entity
        if status in (EntityStatus.DEAD, EntityStatus.DESTROYED) and entity.end_epoch is None:
            entity.end_epoch = epoch
        names = NameRepository(self.session)
        bonds = BondRepository(self.session)
        if status is EntityStatus.REJECTED:
            await names.release(entity.id)
            await self.transfer_contents(entity, epoch)
            await bonds.hide_for_rejection(entity.id, epoch)
            entity.status = status
        elif previous is EntityStatus.REJECTED:
            if await names.is_taken(entity.name, entity.id):
                raise ConflictError(f"The name {entity.name} was taken while the record was out of canon.")
            await names.claim(entity.id, entity.name)
            entity.status = status
            await bonds.reopen_after_restore(entity.id)
        else:
            entity.status = status
        if fate_note is not None:
            entity.fate_note = fate_note
        await self.flush()
        return entity

    async def rename(self, entity: EntityRow, new_name: str) -> str:
        if entity.status is EntityStatus.REJECTED:
            entity.name = clean_display(new_name)
            await self.flush()
            return entity.name
        return await NameRepository(self.session).rename(entity.id, new_name)

    async def flags(self, entity_id: int) -> set[EntityFlag]:
        rows = await self.session.scalars(select(EntityFlagRow.flag).where(EntityFlagRow.entity_id == entity_id))
        return set(rows)

    async def has_flag(self, entity_id: int, flag: EntityFlag) -> bool:
        return await self.session.get(EntityFlagRow, (entity_id, flag)) is not None

    async def add_flag(self, entity_id: int, flag: EntityFlag, epoch: int | None = None) -> bool:
        if held(entity_id) or await self.has_flag(entity_id, flag):
            return False
        self.session.add(EntityFlagRow(entity_id=entity_id, flag=flag, epoch=epoch))
        await self.flush()
        return True

    async def remove_flag(self, entity_id: int, flag: EntityFlag) -> bool:
        if held(entity_id):
            return False
        result = await self.session.execute(delete(EntityFlagRow).where(EntityFlagRow.entity_id == entity_id, EntityFlagRow.flag == flag))
        return bool(getattr(result, "rowcount", 0))

    async def with_flag(self, flag: EntityFlag, status: EntityStatus | None = EntityStatus.CANON) -> list[EntityRow]:
        statement = select(EntityRow).join(EntityFlagRow, EntityFlagRow.entity_id == EntityRow.id).where(EntityFlagRow.flag == flag)
        if status is not None:
            statement = statement.where(EntityRow.status == status)
        return list(await self.session.scalars(statement.order_by(EntityRow.id)))

    async def tags(self, entity_id: int) -> list[str]:
        rows = await self.session.scalars(select(EntityTagRow.tag).where(EntityTagRow.entity_id == entity_id).order_by(EntityTagRow.tag))
        return list(rows)

    async def add_tags(self, entity_id: int, tags: Iterable[str]) -> list[str]:
        existing = set(await self.tags(entity_id))
        added = [tag for tag in dict.fromkeys(self._clean_tags(tags)) if tag not in existing]
        self.session.add_all(EntityTagRow(entity_id=entity_id, tag=tag) for tag in added)
        await self.flush()
        return added

    async def traits(self, entity_id: int) -> set[CreatureTrait]:
        rows = await self.session.scalars(select(EntityTraitRow.trait).where(EntityTraitRow.entity_id == entity_id))
        return set(rows)

    async def add_trait(self, entity_id: int, trait: CreatureTrait) -> bool:
        if await self.session.get(EntityTraitRow, (entity_id, trait)) is not None:
            return False
        self.session.add(EntityTraitRow(entity_id=entity_id, trait=trait))
        await self.flush()
        return True

    async def verdict(self, entity_id: int) -> CreationVerdictRow | None:
        return await self.session.get(CreationVerdictRow, entity_id)

    @staticmethod
    def _clean_tags(tags: Iterable[str]) -> list[str]:
        return [cleaned for cleaned in (normalize_name(tag) for tag in tags) if cleaned]

    @staticmethod
    def _validate_shape(draft: EntityDraft) -> None:
        if draft.stats.kind != draft.entity_type.value:
            raise ValidationFailedError(f"Stats of {an(spoken(draft.stats.kind))} cannot describe {an(spoken(draft.entity_type))}.")
        if draft.engine_kind is not None and engine_kind_owner(draft.engine_kind) is not draft.entity_type:
            raise ValidationFailedError(f"{spoken(draft.engine_kind).capitalize()} does not belong to {an(spoken(draft.entity_type))}.")
        if not draft.description.strip():
            raise ValidationFailedError("A record needs a description.")

    async def _resolve_name(self, names: NameRepository, draft: EntityDraft) -> tuple[str, str | None]:
        display = clean_display(draft.name)
        if not normalize_name(display):
            raise ValidationFailedError("A name cannot be empty.")
        title = draft.title
        if draft.split_title and title is None:
            short, epithet = split_epithet(display)
            if epithet is not None and not await names.is_taken(short):
                return short, epithet
        if await names.is_taken(display):
            raise ConflictError(f"The name {display} is already taken.")
        return display, title

    async def _validated_location(self, entity_type: EntityType, location_id: int | None) -> EntityRow | None:
        if location_id is None:
            return None
        location = await self.session.get(EntityRow, location_id)
        if location is None:
            raise NotFoundError("No such location.")
        if not can_contain(location.entity_type, entity_type):
            raise ValidationFailedError(f"{an(spoken(entity_type), capital=True)} cannot be placed inside {an(spoken(location.entity_type))}.")
        return location

    async def _resolve_world(self, draft: EntityDraft, location: EntityRow | None) -> int:
        if draft.world_id is not None:
            return draft.world_id
        if location is not None:
            return location.world_id
        if draft.creator_son_id is not None:
            son_world: int | None = await self.session.scalar(select(SonRow.current_world_id).where(SonRow.id == draft.creator_son_id))
            if son_world is not None:
                return son_world
        if draft.maker_entity_id is not None:
            maker_world: int | None = await self.session.scalar(select(EntityRow.world_id).where(EntityRow.id == draft.maker_entity_id))
            if maker_world is not None:
                return maker_world
        first = await CosmosRepository(self.session).first_world_id()
        if first is None:
            raise ValidationFailedError("A record needs a world, and no world exists yet.")
        return first

    async def _ensure_no_cycle(self, entity_id: int, location: EntityRow) -> None:
        seen: set[int] = set()
        current: EntityRow | None = location
        while current is not None and current.id not in seen:
            if current.id == entity_id:
                raise ValidationFailedError("A record cannot be placed inside itself.")
            seen.add(current.id)
            current = await self.session.get(EntityRow, current.location_id) if current.location_id is not None else None

    async def _type_of(self, entity_id: int) -> EntityType:
        entity_type: EntityType | None = await self.session.scalar(select(EntityRow.entity_type).where(EntityRow.id == entity_id))
        if entity_type is None:
            raise NotFoundError("No such record.")
        return entity_type
