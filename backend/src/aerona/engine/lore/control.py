import re
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, cast

from sqlalchemy import JSON, Boolean, CheckConstraint, Integer, Table
from sqlalchemy.sql.sqltypes import Enum as SqlEnum

from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.base import Base
from aerona.db.tables.culture import (
    ArtworkProfileRow,
    CastingRow,
    HolderLevelRow,
    HolderTechniqueRow,
    IdeologyAdherentRow,
    IdeologyProfileRow,
    IdeologyTenetRow,
    ItemEnchantmentRow,
    ItemProfileRow,
    LanguageIntelligibilityRow,
    LanguageStandingRow,
    LegendProfileRow,
    ProphecyConditionRow,
    RiteEffectRow,
    RiteProfileRow,
    SpeakerCohortRow,
    TraditionParticipationRow,
    TraditionProfileRow,
)
from aerona.db.tables.economy import WorldMaterialRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.body import DamageType
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import CustomCatalog, ItemDeed, MagicSchool, ProphecyState, RiteEffectKind, SpeakerKind, SummonForm, Technique
from aerona.domain.enums.economy import MaterialSlot
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus, EntityType
from aerona.domain.enums.society import KnowledgeBranch
from aerona.engine.context import TickContext
from aerona.engine.economy.materials import key_parts, set_node_material
from aerona.engine.lore import art, ideology, items, kinds, legends, prophecy, rites, traditions
from aerona.engine.lore.creation import open_lore
from aerona.engine.lore.history import record
from aerona.engine.lore.language import standing_of
from aerona.engine.polity.book import RealmBook
from aerona.engine.polity.control import lock
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import active_bonds, close, connect, living_entity

Values = Mapping[str, Any]
RANGE = re.compile(r"^(\w+) BETWEEN (-?\d+) AND (-?\d+)$")
FLOOR = re.compile(r"^(\w+) >= (-?\d+)$")
FIXED = frozenset({"updated_epoch", "locked", "resolved_epoch", "since_epoch"})


async def ensure_language(ctx: TickContext, entity: EntityRow) -> Base:
    return await standing_of(ctx.session, entity, ctx.epoch)


async def ensure_prophecy(ctx: TickContext, entity: EntityRow) -> Base:
    return await prophecy.condition_of(ctx, entity)


async def ensure_rite(ctx: TickContext, entity: EntityRow) -> Base:
    row = await ctx.session.get(RiteProfileRow, entity.id)
    if row is None:
        row = rites.profile_for(ctx, entity, await rites.school_of(ctx, entity), entity.maker_entity_id)
        await ctx.session.flush()
    return row


async def ensure_ideology(ctx: TickContext, entity: EntityRow) -> Base:
    row = await ctx.session.get(IdeologyProfileRow, entity.id)
    if row is None:
        raise NotFoundError("That creed has no teachings yet.")
    return row


PROFILES: dict[EntityType, Callable[[TickContext, EntityRow], Awaitable[Base]]] = {
    EntityType.LANGUAGE: ensure_language,
    EntityType.LEGEND: legends.profile_of,
    EntityType.TRADITION: traditions.profile_of,
    EntityType.IDEOLOGY: ensure_ideology,
    EntityType.RITE: ensure_rite,
    EntityType.PROPHECY: ensure_prophecy,
    EntityType.ITEM: items.profile_of,
    EntityType.ARTWORK: art.profile_of,
}


def table_of(row: Base) -> Table:
    return cast(Table, type(row).__table__)


def bounds(row: Base) -> dict[str, tuple[int, int | None]]:
    found: dict[str, tuple[int, int | None]] = {}
    for constraint in table_of(row).constraints:
        if not isinstance(constraint, CheckConstraint):
            continue
        text = str(constraint.sqltext)
        if match := RANGE.match(text):
            found[match.group(1)] = (int(match.group(2)), int(match.group(3)))
        elif match := FLOOR.match(text):
            found[match.group(1)] = (int(match.group(2)), None)
    return found


def whole(key: str, value: object, limits: dict[str, tuple[int, int | None]]) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValidationFailedError(f"{key.replace('_', ' ').capitalize()} is a whole number.")
    low, high = limits.get(key, (None, None))
    if (low is not None and value < low) or (high is not None and value > high):
        raise ValidationFailedError(f"{key.replace('_', ' ').capitalize()} runs from {low} to {high if high is not None else 'any height'}.")
    return value


def coerce(row: Base, key: str, value: object, limits: dict[str, tuple[int, int | None]]) -> object:
    column = table_of(row).columns.get(key)
    if column is None or column.primary_key or key in FIXED:
        raise ValidationFailedError(f"{key.replace('_', ' ').capitalize()} cannot be set here.")
    kind = column.type
    if value is None:
        if not column.nullable:
            raise ValidationFailedError(f"{key.replace('_', ' ').capitalize()} cannot be empty.")
        return None
    if isinstance(kind, SqlEnum) and kind.enum_class is not None:
        try:
            return kind.enum_class(str(value))
        except ValueError as error:
            raise ValidationFailedError(f"{value} is not a known {key.replace('_', ' ')}.") from error
    if isinstance(kind, Boolean):
        if not isinstance(value, bool):
            raise ValidationFailedError(f"{key.replace('_', ' ').capitalize()} is yes or no.")
        return value
    if isinstance(kind, Integer):
        return whole(key, value, limits)
    if isinstance(kind, JSON):
        if not isinstance(value, dict | list):
            raise ValidationFailedError(f"{key.replace('_', ' ').capitalize()} is a list or a table of values.")
        return value
    if not isinstance(value, str):
        raise ValidationFailedError(f"{key.replace('_', ' ').capitalize()} is text.")
    return value


async def record_of(ctx: TickContext, entity_id: int) -> EntityRow:
    entity = await ctx.session.get(EntityRow, entity_id)
    if entity is None or entity.entity_type not in PROFILES:
        raise NotFoundError("No such language, legend, tradition, creed, rite, prophecy, item or artwork.")
    return entity


async def body_material(ctx: TickContext, entity: EntityRow, key: object) -> None:
    material, world_material_id = key_parts(str(key) if key is not None else None)
    if world_material_id is not None:
        found = await ctx.session.get(WorldMaterialRow, world_material_id)
        if found is None or found.world_id != entity.world_id:
            raise ValidationFailedError(f"{key} is not a substance of this world.")
    await set_node_material(ctx.session, entity.id, MaterialSlot.BODY, material, world_material_id, force=True)


async def assign(ctx: TickContext, entity: EntityRow, row: Base, key: str, value: object) -> None:
    if isinstance(row, ItemProfileRow) and key == "material":
        await body_material(ctx, entity, value)
        return
    setattr(row, key, value)


async def edit_profile(ctx: TickContext, entity_id: int, values: Values, *, release: list[str]) -> Base:
    entity = await record_of(ctx, entity_id)
    row = await PROFILES[entity.entity_type](ctx, entity)
    limits = bounds(row)
    for key, value in values.items():
        await assign(ctx, entity, row, key, coerce(row, key, value, limits))
        if hasattr(row, "locked"):
            row.locked = lock(row.locked, key)
    if hasattr(row, "locked"):
        row.locked = [item for item in row.locked if item not in release]
    await ctx.session.flush()
    return row


async def create_lore(
    ctx: TickContext,
    entity_type: EntityType,
    *,
    name: str,
    description: str,
    world_id: int | None,
    location_id: int | None,
    power: int,
    values: Values,
) -> EntityRow:
    entity, row, rest = await open_lore(
        ctx, entity_type, name=name, description=description, world_id=world_id, location_id=location_id, power=power, values=values
    )
    if row is not None:
        limits = bounds(row)
        for key, value in rest.items():
            await assign(ctx, entity, row, key, coerce(row, key, value, limits))
    elif rest:
        raise ValidationFailedError(f"{next(iter(rest)).replace('_', ' ').capitalize()} cannot be set here.")
    await ctx.session.flush()
    return entity


def share(value: int, label: str) -> int:
    if not 0 <= value <= PERCENT:
        raise ValidationFailedError(f"{label} runs from 0 to {PERCENT}.")
    return value


async def languages(ctx: TickContext, *ids: int) -> list[EntityRow]:
    found = []
    for entity_id in ids:
        entity = await living_entity(ctx.session, entity_id)
        if entity is None or entity.entity_type is not EntityType.LANGUAGE:
            raise NotFoundError("No such living language.")
        found.append(entity)
    return found


async def set_intelligibility(ctx: TickContext, first: int, second: int, value: int) -> LanguageIntelligibilityRow:
    if first == second:
        raise ValidationFailedError("A tongue always understands itself.")
    await languages(ctx, first, second)
    low, high = sorted((first, second))
    row = await ctx.session.get(LanguageIntelligibilityRow, (low, high))
    if row is None:
        row = LanguageIntelligibilityRow(first_entity_id=low, second_entity_id=high, value=0, epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    row.value, row.epoch = share(value, "Intelligibility"), ctx.epoch
    row.locked = lock(row.locked, "value")
    await ctx.session.flush()
    return row


async def community(ctx: TickContext, community_id: int) -> EntityRow:
    entity = await living_entity(ctx.session, community_id)
    if entity is None or entity.entity_type not in COMMUNITY_TYPES:
        raise NotFoundError("No such living community.")
    return entity


async def set_speakers(ctx: TickContext, community_id: int, language_id: int, kind: SpeakerKind, value: int) -> SpeakerCohortRow | None:
    await community(ctx, community_id)
    await languages(ctx, language_id)
    row = await ctx.session.get(SpeakerCohortRow, (community_id, language_id, kind))
    if value == 0:
        if row is not None:
            await ctx.session.delete(row)
            await ctx.session.flush()
        return None
    if row is None:
        row = SpeakerCohortRow(community_entity_id=community_id, language_entity_id=language_id, kind=kind, share=0, since_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    row.share = share(value, "Share of speakers")
    row.locked = lock(row.locked, "share")
    await ctx.session.flush()
    return row


async def set_level(ctx: TickContext, holder_id: int, branch: KnowledgeBranch, level: int) -> HolderLevelRow:
    await community(ctx, holder_id)
    if level < 0:
        raise ValidationFailedError("A level cannot be negative.")
    row = await ctx.session.get(HolderLevelRow, (holder_id, branch))
    if row is None:
        row = HolderLevelRow(holder_entity_id=holder_id, branch=branch, level=0, practitioners=0, progress=0, secret=False, updated_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    row.level, row.locked = level, lock(row.locked, "level")
    await ctx.session.flush()
    return row


async def set_technique(ctx: TickContext, holder_id: int, technique: Technique, *, held: bool, secret: bool) -> HolderTechniqueRow | None:
    await community(ctx, holder_id)
    row = await ctx.session.get(HolderTechniqueRow, (holder_id, technique))
    if not held:
        if row is not None:
            await ctx.session.delete(row)
            await ctx.session.flush()
        return None
    if row is None:
        row = HolderTechniqueRow(holder_entity_id=holder_id, technique=technique, since_epoch=ctx.epoch, secret=secret)
        ctx.session.add(row)
    row.secret = secret
    await ctx.session.flush()
    return row


async def creed(ctx: TickContext, ideology_id: int) -> EntityRow:
    entity = await living_entity(ctx.session, ideology_id)
    if entity is None or entity.entity_type is not EntityType.IDEOLOGY:
        raise NotFoundError("No such living creed.")
    return entity


async def set_creed_tenet(ctx: TickContext, ideology_id: int, tenet: StrEnum, *, held: bool) -> IdeologyTenetRow | None:
    await creed(ctx, ideology_id)
    row = await ctx.session.get(IdeologyTenetRow, (ideology_id, tenet))
    if not held:
        if row is not None:
            await ctx.session.delete(row)
            await ctx.session.flush()
        return None
    if row is None:
        row = IdeologyTenetRow(ideology_entity_id=ideology_id, tenet=tenet)
        ctx.session.add(row)
        await ctx.session.flush()
    return row


async def set_adherent(ctx: TickContext, ideology_id: int, community_id: int, strength: int, *, state: bool) -> IdeologyAdherentRow | None:
    await creed(ctx, ideology_id)
    await community(ctx, community_id)
    row = await ctx.session.get(IdeologyAdherentRow, (ideology_id, community_id))
    if strength == 0:
        if row is not None:
            await ctx.session.delete(row)
            await ctx.session.flush()
        return None
    if row is None:
        row = IdeologyAdherentRow(ideology_entity_id=ideology_id, adherent_entity_id=community_id, strength=0, state=False, since_epoch=ctx.epoch)
        ctx.session.add(row)
    row.strength, row.state = share(strength, "Adherence"), state
    if state:
        await ideology.adopt(ctx, await creed(ctx, ideology_id))
    await ctx.session.flush()
    return row


async def found_creed(ctx: TickContext, founder_id: int) -> EntityRow:
    founder = await living_entity(ctx.session, founder_id)
    if founder is None or founder.entity_type is not EntityType.MORTAL:
        raise NotFoundError("No such living mortal.")
    found = await ideology.found(ctx, founder)
    if found is None:
        raise ValidationFailedError(f"{founder.name} holds no conviction strong enough to teach.")
    return found


async def rite(ctx: TickContext, rite_id: int) -> tuple[EntityRow, RiteProfileRow]:
    entity = await living_entity(ctx.session, rite_id)
    row = await ctx.session.get(RiteProfileRow, rite_id) if entity is not None else None
    if entity is None or row is None:
        raise NotFoundError("No such living rite.")
    return entity, row


async def devise_rite(ctx: TickContext, school: MagicSchool, inventor_id: int) -> EntityRow:
    inventor = await living_entity(ctx.session, inventor_id)
    if inventor is None or inventor.entity_type is not EntityType.MORTAL:
        raise NotFoundError("No such living mortal.")
    found, _ = await rites.devise(ctx, school, inventor)
    return found


@dataclass(frozen=True)
class EffectShape:
    detail: str | None = None
    damage_type: DamageType | None = None
    summon_form: SummonForm | None = None
    custom_kind_id: int | None = None


async def set_rite_effect(ctx: TickContext, rite_id: int, effect: RiteEffectKind, magnitude: int, shape: EffectShape) -> RiteEffectRow | None:
    await rite(ctx, rite_id)
    if shape.custom_kind_id is not None and await kinds.kind_of(ctx.session, shape.custom_kind_id, CustomCatalog.RITE_EFFECT) is None:
        raise NotFoundError("No such working of your own making.")
    row = await ctx.session.get(RiteEffectRow, (rite_id, effect))
    if magnitude == 0:
        if row is not None:
            await ctx.session.delete(row)
            await ctx.session.flush()
        return None
    if not 0 < magnitude <= PERCENT:
        raise ValidationFailedError(f"Magnitude runs from 1 to {PERCENT}.")
    if row is None:
        row = RiteEffectRow(rite_entity_id=rite_id, effect=effect, magnitude=magnitude)
        ctx.session.add(row)
    row.magnitude, row.detail = magnitude, shape.detail
    row.damage_type, row.summon_form, row.custom_kind_id = shape.damage_type, shape.summon_form, shape.custom_kind_id
    await ctx.session.flush()
    return row


async def teach_rite(ctx: TickContext, rite_id: int, holder_id: int, *, taught: bool) -> bool:
    entity, _ = await rite(ctx, rite_id)
    holder = await living_entity(ctx.session, holder_id)
    if holder is None:
        raise NotFoundError("No such living pupil.")
    bonds = await active_bonds(ctx.session, [BondKind.OWNS], sources=[holder.id], targets=[entity.id])
    if taught and not bonds:
        await connect(ctx.session, holder.id, entity.id, BondKind.OWNS, ctx.epoch, description="taught the rite")
    if not taught:
        for bond in bonds:
            await close(ctx.session, bond, ctx.epoch, "made to forget the rite")
    await ctx.session.flush()
    return taught


async def forbid_rite(ctx: TickContext, rite_id: int, authority_id: int, *, forbidden: bool) -> list[int]:
    _, row = await rite(ctx, rite_id)
    authority = await living_entity(ctx.session, authority_id) or await ctx.session.get(EntityRow, authority_id)
    if authority is None:
        raise NotFoundError("No such realm, cult or people to forbid it.")
    held = set(row.forbidden_by)
    row.forbidden_by = sorted(held | {authority.id}) if forbidden else sorted(held - {authority.id})
    row.locked = lock(row.locked, "forbidden_by")
    await ctx.session.flush()
    return row.forbidden_by


async def dispel_rite(ctx: TickContext, rite_id: int) -> CastingRow:
    await rite(ctx, rite_id)
    casting = await rites.dispel(ctx, rite_id)
    if casting is None:
        raise ValidationFailedError("Nothing of that rite lingers to be undone.")
    return casting


async def set_requirements(ctx: TickContext, rite_id: int, values: dict[str, int | str | bool]) -> RiteProfileRow:
    _, row = await rite(ctx, rite_id)
    row.requirements = rites.checked_requirements(values)
    row.locked = lock(row.locked, "requirements")
    await ctx.session.flush()
    return row


async def cast_rite(ctx: TickContext, rite_id: int, caster_id: int, target_id: int | None) -> CastingRow:
    entity, row = await rite(ctx, rite_id)
    caster = await living_entity(ctx.session, caster_id)
    if caster is None:
        raise NotFoundError("No such living caster.")
    target = await living_entity(ctx.session, target_id) if target_id is not None else None
    casting = await rites.cast(ctx, caster, entity, row, target=target, realms=await RealmBook.load(ctx.session), forced=True)
    if casting is None:
        raise ValidationFailedError("The rite would not answer.")
    await ctx.session.flush()
    return casting


async def resolve_prophecy(ctx: TickContext, prophecy_id: int, *, fulfilled: bool) -> ProphecyConditionRow:
    entity = await living_entity(ctx.session, prophecy_id)
    if entity is None or entity.entity_type is not EntityType.PROPHECY or entity.status is not EntityStatus.CANON:
        raise NotFoundError("No such open prophecy.")
    row = await prophecy.condition_of(ctx, entity)
    if row.state is not ProphecyState.PENDING:
        raise ValidationFailedError("That prophecy is already settled.")
    if fulfilled:
        await prophecy.fulfil(ctx, entity, row)
    else:
        await prophecy.fail(ctx, row)
    await ctx.session.flush()
    return row


async def set_enchantment(ctx: TickContext, item_id: int, effect: RiteEffectKind, strength: int) -> ItemEnchantmentRow | None:
    item = await living_entity(ctx.session, item_id)
    if item is None or item.entity_type is not EntityType.ITEM:
        raise NotFoundError("No such item.")
    row = await ctx.session.get(ItemEnchantmentRow, (item_id, effect))
    if strength == 0:
        if row is not None:
            await ctx.session.delete(row)
            await ctx.session.flush()
        return None
    if row is None:
        row = ItemEnchantmentRow(item_entity_id=item_id, effect=effect, strength=0, rite_entity_id=None, since_epoch=ctx.epoch)
        ctx.session.add(row)
        record(ctx, item_id, ItemDeed.ENCHANTED, None, f"enchanted with {effect.value.replace('_', ' ')}")
    row.strength = share(strength, "Strength")
    await ctx.session.flush()
    return row


async def set_participation(ctx: TickContext, tradition_id: int, community_id: int, value: int) -> TraditionParticipationRow:
    tradition = await living_entity(ctx.session, tradition_id)
    if tradition is None or tradition.entity_type is not EntityType.TRADITION:
        raise NotFoundError("No such living tradition.")
    row = await traditions.participate(ctx, tradition, await community(ctx, community_id))
    row.participation = clamp_int(share(value, "Participation"), 0, PERCENT)
    row.locked = lock(row.locked, "participation")
    await ctx.session.flush()
    return row


PROFILE_ROWS = (
    LanguageStandingRow,
    LegendProfileRow,
    TraditionProfileRow,
    IdeologyProfileRow,
    RiteProfileRow,
    ProphecyConditionRow,
    ItemProfileRow,
    ArtworkProfileRow,
)
