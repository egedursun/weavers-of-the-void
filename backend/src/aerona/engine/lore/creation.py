from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from pydantic import TypeAdapter

from aerona.catalog.lore import ART_MESSAGES, IDEOLOGY_APPEAL, IDEOLOGY_VALUES, ITEM_CLASSES, LEGEND_MORALS, RITE_TEMPLATES, TRADITIONS
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.grammar import an
from aerona.db.base import Base
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.culture import (
    ArtworkProfileRow,
    IdeologyProfileRow,
    IdeologyTenetRow,
    ItemProfileRow,
    LegendProfileRow,
    RiteProfileRow,
    TraditionProfileRow,
)
from aerona.db.tables.economy import NodeMaterialRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.culture import (
    PERFORMED_MEDIA,
    ArtMedium,
    BacklashKind,
    CurseKind,
    IdeologyTenet,
    ItemClass,
    LegendArchetype,
    MagicSchool,
    MagicSource,
    ProphecyConsequence,
    ProphecyPredicate,
    TraditionKind,
)
from aerona.domain.enums.economy import MaterialSlot
from aerona.domain.enums.entity import EngineKind, EntityType
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.world import SkyEventKind
from aerona.domain.models.entity_stats import EntityStats
from aerona.engine.context import TickContext
from aerona.engine.economy.materials import slot_key
from aerona.engine.lore.language import standing_of
from aerona.engine.lore.prophecy import Foretelling, typed_condition
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.records import RecordSpec, create_record

STATS: TypeAdapter[EntityStats] = TypeAdapter(EntityStats)
CREATABLE = frozenset(
    {
        EntityType.LANGUAGE,
        EntityType.LEGEND,
        EntityType.TRADITION,
        EntityType.IDEOLOGY,
        EntityType.RITE,
        EntityType.PROPHECY,
        EntityType.ITEM,
        EntityType.ARTWORK,
        EntityType.KNOWLEDGE,
    }
)
Values = dict[str, Any]
Seeder = Callable[[TickContext, EntityRow, Values], Awaitable[Base | None]]


def take[E](values: Values, key: str, kind: Callable[[str], E], default: E | None = None) -> E:
    raw = values.pop(key, None)
    if raw is None:
        if default is None:
            raise ValidationFailedError(f"Choose the {key.replace('_', ' ')} first.")
        return default
    try:
        return kind(str(raw))
    except ValueError as error:
        raise ValidationFailedError(f"{raw} is not a known {key.replace('_', ' ')}.") from error


async def seed_language(ctx: TickContext, entity: EntityRow, values: Values) -> Base:
    return await standing_of(ctx.session, entity, ctx.epoch)


async def seed_legend(ctx: TickContext, entity: EntityRow, values: Values) -> Base:
    archetype = take(values, "archetype", LegendArchetype)
    row = LegendProfileRow(
        legend_entity_id=entity.id,
        archetype=archetype,
        credence=PERCENT * 3 // 10,
        distortion=0,
        moral={axis.value: value for axis, value in LEGEND_MORALS[archetype].items()},
        tellers=[],
        updated_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    return row


async def seed_tradition(ctx: TickContext, entity: EntityRow, values: Values) -> Base:
    kind = take(values, "kind", TraditionKind)
    spec = TRADITIONS[kind]
    row = TraditionProfileRow(tradition_entity_id=entity.id, kind=kind, cost=dict(spec.cost), effects=dict(spec.effects), updated_epoch=ctx.epoch, locked=[])
    ctx.session.add(row)
    return row


async def seed_ideology(ctx: TickContext, entity: EntityRow, values: Values) -> Base:
    raw = values.pop("tenets", None) or []
    if not isinstance(raw, list) or not raw:
        raise ValidationFailedError("A creed needs at least one tenet.")
    tenets = [take({"tenet": item}, "tenet", IdeologyTenet) for item in dict.fromkeys(raw)]
    delta: dict[str, int] = {}
    appeal: dict[str, int] = {}
    for tenet in tenets:
        ctx.session.add(IdeologyTenetRow(ideology_entity_id=entity.id, tenet=tenet))
        for axis, value in IDEOLOGY_VALUES[tenet].items():
            delta[axis.value] = delta.get(axis.value, 0) + value
        for social_class, value in IDEOLOGY_APPEAL[tenet].items():
            appeal[social_class.value] = max(appeal.get(social_class.value, 0), value)
    row = IdeologyProfileRow(
        ideology_entity_id=entity.id,
        value_delta=delta,
        tenets=[tenet.value for tenet in tenets],
        appeal=appeal,
        texts=[],
        updated_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    return row


async def seed_rite(ctx: TickContext, entity: EntityRow, values: Values) -> Base:
    school = take(values, "school", MagicSchool)
    template = RITE_TEMPLATES[school]
    source = take(values, "source", MagicSource, template.source)
    power = clamp_int(int(values.pop("power", template.power)), 1, 10)
    row = RiteProfileRow(
        rite_entity_id=entity.id,
        school=school,
        source=source,
        requirements={},
        cost={},
        power=power,
        backlash_chance=clamp_int(power * ctx.rules.backlash.per_power_pct, 0, PERCENT),
        backlash=BacklashKind.INJURY,
        holy=source is MagicSource.DIVINE,
        heretical=False,
        locked=[],
    )
    ctx.session.add(row)
    return row


def optional_id(values: Values, key: str) -> int | None:
    raw = values.pop(key, None)
    if raw is None or raw == "":
        return None
    if isinstance(raw, bool) or not isinstance(raw, int | str) or not str(raw).isdigit():
        raise ValidationFailedError(f"{key.replace('_', ' ').capitalize()} is an id.")
    return int(raw)


def optional_kind[E](values: Values, key: str, kind: Callable[[str], E]) -> E | None:
    raw = values.pop(key, None)
    if raw is None or raw == "":
        return None
    try:
        return kind(str(raw))
    except ValueError as error:
        raise ValidationFailedError(f"{raw} is not a known {key.replace('_', ' ')}.") from error


async def seed_prophecy(ctx: TickContext, entity: EntityRow, values: Values) -> Base:
    told = Foretelling(
        predicate=take(values, "predicate", ProphecyPredicate),
        subject_id=optional_id(values, "subject_id"),
        second_id=optional_id(values, "second_id"),
        archetype=optional_kind(values, "archetype", LegendArchetype),
        sky_kind=optional_kind(values, "sky_kind", SkyEventKind),
        event_kind=optional_kind(values, "event_kind", EngineKind),
        within_epochs=optional_id(values, "within_epochs"),
        consequence=optional_kind(values, "consequence", ProphecyConsequence),
        consequence_id=optional_id(values, "consequence_id"),
    )
    return await typed_condition(ctx, entity, told)


async def seed_item(ctx: TickContext, entity: EntityRow, values: Values) -> Base:
    item_class = take(values, "item_class", ItemClass)
    spec = ITEM_CLASSES[item_class]
    body = await ctx.session.get(NodeMaterialRow, (entity.id, MaterialSlot.BODY))
    row = ItemProfileRow(
        item_entity_id=entity.id,
        item_class=item_class,
        material=slot_key(body.material, body.world_material_id) if body is not None else None,
        quality=PERCENT // 2,
        condition=PERCENT,
        damage_type=spec.damage_type,
        reach=spec.reach,
        coverage=spec.coverage,
        weight=spec.weight,
        curse=CurseKind.NONE,
        value=PERCENT // 2,
        renown=0,
        symbol=False,
        secondary_materials=[],
        updated_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    return row


async def seed_artwork(ctx: TickContext, entity: EntityRow, values: Values) -> Base:
    medium = take(values, "medium", ArtMedium)
    row = ArtworkProfileRow(
        artwork_entity_id=entity.id,
        medium=medium,
        performed=medium in PERFORMED_MEDIA,
        message={axis.value: value for axis, value in ART_MESSAGES[medium].items()},
        quality=PERCENT // 2,
        copies=1,
        translations=[],
        propaganda=False,
        updated_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    return row


async def seed_knowledge(ctx: TickContext, entity: EntityRow, values: Values) -> None:
    return None


SEEDERS: dict[EntityType, Seeder] = {
    EntityType.LANGUAGE: seed_language,
    EntityType.LEGEND: seed_legend,
    EntityType.TRADITION: seed_tradition,
    EntityType.IDEOLOGY: seed_ideology,
    EntityType.RITE: seed_rite,
    EntityType.PROPHECY: seed_prophecy,
    EntityType.ITEM: seed_item,
    EntityType.ARTWORK: seed_artwork,
    EntityType.KNOWLEDGE: seed_knowledge,
}


async def place_of(ctx: TickContext, location_id: int | None, world_id: int | None) -> tuple[int, int | None]:
    location = await living_entity(ctx.session, location_id) if location_id is not None else None
    if location_id is not None and location is None:
        raise NotFoundError("No such living place to set it in.")
    world = location.world_id if location is not None else world_id
    if world is None or await ctx.session.get(WorldRow, world) is None:
        raise NotFoundError("Choose the world it belongs to.")
    return world, location.id if location is not None else None


async def open_lore(
    ctx: TickContext,
    entity_type: EntityType,
    *,
    name: str,
    description: str,
    world_id: int | None,
    location_id: int | None,
    power: int,
    values: Mapping[str, Any],
) -> tuple[EntityRow, Base | None, Values]:
    if entity_type not in CREATABLE:
        raise ValidationFailedError(f"{an(entity_type.value, capital=True)} cannot be made here.")
    if not name.strip():
        raise ValidationFailedError("Name it first.")
    world, location = await place_of(ctx, location_id, world_id)
    rest: Values = dict(values)
    branch = take(rest, "branch", KnowledgeBranch) if entity_type is EntityType.KNOWLEDGE else None
    stats: dict[str, Any] = {"kind": entity_type.value}
    if entity_type is EntityType.KNOWLEDGE:
        stats["level"] = clamp_int(int(rest.pop("level", 1)), 1, 10)
    for key in ("certainty", "renown", "influence", "spread", "rigidity", "sacredness", "complexity", "damage", "protection", "might", "curse"):
        if key in rest:
            stats[key] = clamp_int(int(rest.pop(key)), 0, PERCENT)
    entity = await create_record(
        ctx,
        RecordSpec(
            name=name.strip(),
            entity_type=entity_type,
            stats=STATS.validate_python(stats),
            body=description.strip() or name.strip(),
            power=clamp_int(power, 1, 10),
            world_id=world,
            location_id=location,
            knowledge_branch=branch,
        ),
    )
    row = await SEEDERS[entity_type](ctx, entity, rest)
    await ctx.session.flush()
    return entity, row, rest
