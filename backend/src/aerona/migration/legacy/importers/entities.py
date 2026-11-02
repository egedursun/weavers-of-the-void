from dataclasses import dataclass

from aerona.catalog.entity_types import can_contain, engine_kind_owner
from aerona.constants.schema import KEY_MAX_LENGTH, PRIVATE_NOTE_MAX_LENGTH, SUBTYPE_MAX_LENGTH, TITLE_MAX_LENGTH
from aerona.db.repositories.names import normalize_name
from aerona.db.tables.cosmic_state import ResourceMechanicRow
from aerona.db.tables.entities import CreationVerdictRow, EntityFlagRow, EntityRow, EntityTagRow, EntityTraitRow
from aerona.domain.enums.agent import Verdict
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import (
    ENDED_STATUSES,
    ArchiveOverride,
    CivilizationTier,
    EngineKind,
    EntityOrigin,
    EntityStatus,
    EntityType,
    MortalRole,
)
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.society import ResourceMechanic
from aerona.migration.legacy import blobs
from aerona.migration.legacy.context import EntityFacts, MigrationContext
from aerona.migration.legacy.idmap import LegacyKind
from aerona.migration.legacy.importers.cosmos import DEFAULTED, UNKNOWN_VALUE
from aerona.migration.legacy.patterns import LegacyPatterns
from aerona.migration.legacy.source import LegacyRow
from aerona.migration.legacy.stats import read_stats
from aerona.migration.legacy.tags import TagReader, TagReading
from aerona.migration.legacy.values import as_float, as_list, bounded, truncated

JUDGED_ORIGINS = frozenset({EntityOrigin.SON, EntityOrigin.MORTAL})
TIER_MAX = max(CivilizationTier)
CLAMPED_STAT = "clamped stat"
LOCATION_DROPPED = "location dropped"
ORIGIN_CHANGED = "origin changed"
DERIVED_FLAG = "derived by legacy pattern"


@dataclass(frozen=True)
class PendingEntity:
    row: LegacyRow
    entity: EntityRow
    reading: TagReading
    origin: EntityOrigin


class EntityImporter:
    def __init__(self, context: MigrationContext) -> None:
        self.context = context
        self.vocabulary = context.vocabulary
        self.report = context.report
        self.tags = TagReader(context.vocabulary)
        self.patterns = LegacyPatterns(context.vocabulary)
        self.types: dict[int, EntityType] = {}

    async def run(self) -> None:
        pending: list[PendingEntity] = []
        for row in self.context.source.iterate("entities", ("id",)):
            item = self._build(row)
            if item is not None:
                pending.append(item)
                self.types[row.integer("id") or 0] = item.entity.entity_type
        self.context.session.add_all([item.entity for item in pending])
        await self.context.session.flush()
        for item in pending:
            legacy_id = item.row.integer("id") or 0
            entity = item.entity
            self.context.ids.put(LegacyKind.ENTITY, legacy_id, entity.id)
            self.context.rows[entity.id] = entity
            self.context.readings[legacy_id] = item.reading
            if entity.status is not EntityStatus.REJECTED:
                self.context.names.bind(entity.id, entity.name)
        self.context.session.add_all(self.context.names.drain())
        await self.context.session.flush()
        for item in pending:
            self._link(item)
        await self.context.session.flush()
        for item in pending:
            self._children(item)
            await self.context.flush_if_full()
        await self.context.flush()
        for item in pending:
            entity = item.entity
            self.context.entities[entity.id] = EntityFacts(entity.entity_type, entity.status, entity.world_id, entity.birth_epoch)

    def _reference(self, row: LegacyRow) -> str:
        return f"entity:{row.integer('id')}"

    def _status(self, row: LegacyRow) -> EntityStatus:
        status = self.vocabulary.decode_as("entity_status", row.text("status"), EntityStatus)
        if status is None:
            self.report.warn(UNKNOWN_VALUE, self._reference(row), f"status {row.text('status')!r} read as canon")
            return EntityStatus.CANON
        return status

    def _origin(self, row: LegacyRow) -> EntityOrigin:
        origin = self.vocabulary.decode_as("entity_origin", row.text("origin"), EntityOrigin) or EntityOrigin.SON
        if origin is EntityOrigin.SON and row.integer("creator_son_id") is None:
            return EntityOrigin.CREATOR
        return origin

    def _name(self, row: LegacyRow, status: EntityStatus) -> str:
        legacy_id = row.integer("id")
        original = (row.text("name") or "").strip()
        if not normalize_name(original):
            original = f"{row.text('entity_type') or 'entity'} {legacy_id}"
            self.report.warn(DEFAULTED, self._reference(row), "empty name replaced")
        if status is EntityStatus.REJECTED:
            return original
        display = self.context.names.reserve(original)
        if display != original:
            self.report.renamed("entity", legacy_id, original, display)
        return display

    def _engine_kind(self, entity_type: EntityType, subtype: str | None, reading: TagReading) -> EngineKind | None:
        table = self.vocabulary.engine_kinds.get(entity_type.value, {})
        folded = (subtype or "").strip().casefold()
        found = next((EngineKind(english) for legacy, english in table.items() if legacy.casefold() == folded), None)
        if found is None and reading.engine_kind is not None:
            found = reading.engine_kind
        if found is not None and engine_kind_owner(found) is not entity_type:
            return None
        return found

    def _mortal_role(self, subtype: str | None, reading: TagReading) -> MortalRole | None:
        if reading.mortal_role is not None:
            return reading.mortal_role
        folded = (subtype or "").strip().casefold()
        found = next((MortalRole(english) for legacy, english in self.vocabulary.mortal_roles.subtypes.items() if legacy.casefold() == folded), None)
        if found is None and subtype is not None:
            self.report.convert("mortals_without_role")
        return found

    def _end_epoch(self, row: LegacyRow, status: EntityStatus, birth: int) -> int | None:
        end = row.integer("end_epoch")
        if status in ENDED_STATUSES and end is None:
            end = max(birth, self.context.epoch - 1)
            self.report.warn(DEFAULTED, self._reference(row), f"end epoch unknown; set to {end}")
        return end

    def _position(self, row: LegacyRow) -> tuple[float | None, float | None]:
        value = as_list(row.json("map_position"))
        if len(value) < 2:
            return None, None
        x, y = as_float(value[0]), as_float(value[1])
        if x is None or y is None:
            return None, None
        self.report.convert("map_position_hints")
        return x, y

    def _build(self, row: LegacyRow) -> PendingEntity | None:
        reference = self._reference(row)
        entity_type = self.vocabulary.decode_as("entity_type", row.text("entity_type"), EntityType)
        if entity_type is None:
            self.report.place_failed("entity", reference, f"unknown type {row.text('entity_type')!r}")
            return None
        status = self._status(row)
        reading = self.tags.read(as_list(row.json("tags")))
        stats = read_stats(self.vocabulary, entity_type, row.json("stats"))
        for key in stats.dropped:
            self.report.stat_dropped(key)
        for detail in stats.clamped:
            self.report.warn(CLAMPED_STAT, reference, detail)
        if stats.extras:
            self.context.war_stats[row.integer("id") or 0] = dict(stats.extras)
        society = row.json("society")
        if isinstance(society, dict) and society:
            self.context.society_payloads[row.integer("id") or 0] = society
        subtype = row.text("subtype")
        birth = max(0, row.integer("birth_epoch") or 0)
        domain = self.vocabulary.decode_as("domain", row.text("domain"), Domain)
        if row.text("domain") is not None and domain is None:
            self.report.warn(UNKNOWN_VALUE, reference, f"domain {row.text('domain')!r} dropped")
        engine_kind = self._engine_kind(entity_type, subtype, reading)
        text = f"{subtype or ''} {row.text('name') or ''}"
        is_water = entity_type is EntityType.REGION and self.patterns.is_water(text)
        is_underworld = entity_type is EntityType.REGION and self.patterns.is_underworld(text)
        if engine_kind is None and entity_type is EntityType.STRUCTURE and self.patterns.is_temple(subtype or ""):
            engine_kind = EngineKind.TEMPLE
            self.report.convert("temples_from_subtype")
        legend_category = None
        if entity_type is EntityType.LEGEND:
            legend_category = self.patterns.legend_category(f"{row.text('name') or ''} {row.text('description') or ''}")
            self.report.convert(f"legend_category_{legend_category.value if legend_category else 'none'}")
        for flag, active in (("water_regions", is_water), ("underworld_regions", is_underworld)):
            if active:
                self.report.convert(flag)
        archive_raw = row.integer("archive_override")
        archive = self.vocabulary.decode_as("archive_override", archive_raw, ArchiveOverride) if archive_raw is not None else None
        sanity = bounded(self.report, reference, "sanity", stats.extras.get("sanity"), (PERCENT_MIN, PERCENT_MAX))
        tier = bounded(self.report, reference, "civilization tier", reading.tier, (CivilizationTier.TRIBE, TIER_MAX))
        previous_tier = bounded(self.report, reference, "previous tier", stats.extras.get("tier_previous"), (CivilizationTier.TRIBE, TIER_MAX))
        if tier is not None:
            self.report.convert("civilization_tiers")
        mechanic = self._resource_mechanic(entity_type, reading)
        title = row.text("title") or reading.title
        if row.text("title") is not None and reading.title is not None and reading.title != row.text("title"):
            reading.kept.append(f"{self.vocabulary.prefix('title')}:{reading.title}")
        map_x, map_y = self._position(row)
        origin = self._origin(row)
        entity = EntityRow(
            name=self._name(row, status),
            title=truncated(self.report, reference, "title", title, TITLE_MAX_LENGTH),
            entity_type=entity_type,
            subtype=truncated(self.report, reference, "subtype", subtype, SUBTYPE_MAX_LENGTH),
            engine_kind=engine_kind,
            mortal_role=self._mortal_role(subtype, reading) if entity_type is EntityType.MORTAL else None,
            description=row.text("description") or row.required_text("name", reference),
            stats=stats.stats,
            power_level=max(1, row.integer("power_level") or 1),
            domain=domain,
            origin=EntityOrigin.ENGINE if origin is EntityOrigin.MORTAL else origin,
            world_id=self.context.world_or_primary(row.integer("world_id")),
            status=status,
            pending_name=row.flag("pending") or (row.text("description") or "").startswith(self.vocabulary.texts.engine_prefix.strip()),
            fate_note=row.text("fate_note"),
            depth=blobs.entity_depth(self.vocabulary, row.json("depth"), birth),
            birth_epoch=birth,
            end_epoch=self._end_epoch(row, status, birth),
            last_acted_epoch=max(0, row.integer("last_acted_epoch") or 0),
            importance=row.integer("importance"),
            archive_override=archive,
            favorite=row.flag("favorite"),
            private_note=truncated(self.report, reference, "private note", row.text("private_note"), PRIVATE_NOTE_MAX_LENGTH),
            map_x=map_x,
            map_y=map_y,
            image_prompt=row.text("image_prompt"),
            civ_tier=tier,
            civ_tier_epoch=stats.extras.get("tier_epoch") if tier is not None else None,
            civ_tier_previous=previous_tier if tier is not None else None,
            sanity=sanity,
            knowledge_branch=reading.branch if entity_type is EntityType.KNOWLEDGE else None,
            natural_law=reading.natural_law if entity_type is EntityType.NATURAL_LAW else None,
            resource_mechanic=mechanic,
            prophecy_reading=reading.reading if entity_type is EntityType.PROPHECY else None,
            legend_category=legend_category,
            social_class=reading.social_class,
            is_underworld=is_underworld,
            is_water=is_water,
            fold_count=max(0, reading.fold_count or 0),
        )
        return PendingEntity(row=row, entity=entity, reading=reading, origin=origin)

    def _resource_mechanic(self, entity_type: EntityType, reading: TagReading) -> ResourceMechanic | None:
        if entity_type is not EntityType.RESOURCE or not reading.mechanics:
            return None
        if ResourceMechanic.SACRED in reading.mechanics and reading.sacred_son is not None:
            return ResourceMechanic.SACRED
        return reading.mechanics[0]

    def _link(self, item: PendingEntity) -> None:
        row, entity, reading = item.row, item.entity, item.reading
        reference = self._reference(row)
        context = self.context
        creator = row.integer("creator_son_id")
        entity.creator_son_id = context.son(creator)
        if creator is not None and entity.creator_son_id is None:
            context.report.place_failed("entity creator", reference, f"son {creator} is missing")
        maker = context.entity(row.integer("maker_id"))
        entity.maker_entity_id = maker if maker != entity.id else None
        if item.origin is EntityOrigin.MORTAL:
            if entity.maker_entity_id is None:
                context.report.warn(ORIGIN_CHANGED, reference, "a mortal-made record without a maker became an engine record")
            else:
                entity.origin = EntityOrigin.MORTAL
        if entity.resource_mechanic is ResourceMechanic.SACRED:
            entity.sacred_to_son_id = context.son(reading.sacred_son)
            if entity.sacred_to_son_id is None:
                entity.resource_mechanic = next((mechanic for mechanic in reading.mechanics if mechanic is not ResourceMechanic.SACRED), None)
                context.report.warn(UNKNOWN_VALUE, reference, "sacred resource without a known son")
        if reading.affiliation is not None:
            entity.affiliated_entity_id = context.entity(reading.affiliation[1])
            if entity.affiliated_entity_id is None:
                context.report.place_failed("faction link", reference, f"community {reading.affiliation[1]} is missing")
            else:
                context.report.convert(f"faction_links_{reading.affiliation[0]}")
        self._locate(row, entity)

    def _locate(self, row: LegacyRow, entity: EntityRow) -> None:
        legacy_location = row.integer("location_id")
        if legacy_location is None:
            return
        reference = self._reference(row)
        location_id = self.context.entity(legacy_location)
        location = self.context.rows.get(location_id) if location_id is not None else None
        if location is None or location.id == entity.id:
            self.report.place_failed(LOCATION_DROPPED, reference, f"location {legacy_location} is missing")
            return
        if not can_contain(location.entity_type, entity.entity_type):
            self.report.place_failed(LOCATION_DROPPED, reference, f"a {entity.entity_type.value} cannot be inside a {location.entity_type.value}")
            return
        if self._cycles(entity.id, location):
            self.report.place_failed(LOCATION_DROPPED, reference, "the location chain loops")
            return
        entity.location_id = location.id
        if location.world_id != entity.world_id:
            self.report.warn("world aligned", reference, "world taken from the location")
            entity.world_id = location.world_id

    def _cycles(self, entity_id: int, location: EntityRow) -> bool:
        seen: set[int] = set()
        current: EntityRow | None = location
        while current is not None and current.id not in seen:
            if current.id == entity_id:
                return True
            seen.add(current.id)
            current = self.context.rows.get(current.location_id) if current.location_id is not None else None
        return False

    def _children(self, item: PendingEntity) -> None:
        entity, reading = item.entity, item.reading
        context = self.context
        for flag in reading.flags:
            context.add(EntityFlagRow(entity_id=entity.id, flag=flag, epoch=None))
            context.report.convert(f"flag_{flag.value}")
        tags = dict.fromkeys(cleaned[:KEY_MAX_LENGTH] for tag in [*reading.free, *reading.kept] if (cleaned := normalize_name(tag)))
        for tag in tags:
            context.add(EntityTagRow(entity_id=entity.id, tag=tag))
        for tag in reading.free:
            context.report.tag_free(tag)
        for tag in reading.kept:
            context.report.tag_kept(tag)
        for tag in reading.unknown:
            context.report.tag_unknown(tag)
        for trait in reading.traits:
            context.add(EntityTraitRow(entity_id=entity.id, trait=trait))
            context.report.convert("creature_traits")
        if entity.entity_type is EntityType.RESOURCE:
            for mechanic in reading.mechanics:
                context.add(ResourceMechanicRow(entity_id=entity.id, mechanic=mechanic))
                context.report.convert("resource_mechanics")
        if entity.origin in JUDGED_ORIGINS:
            verdict = Verdict.REJECTED if entity.status is EntityStatus.REJECTED else Verdict.ACCEPTED
            context.add(CreationVerdictRow(entity_id=entity.id, epoch=entity.birth_epoch, verdict=verdict, judged_epoch=entity.birth_epoch))


async def import_entities(context: MigrationContext) -> dict[int, EntityType]:
    importer = EntityImporter(context)
    await importer.run()
    return importer.types
