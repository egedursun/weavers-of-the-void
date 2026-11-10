from sqlalchemy import select

from aerona.core.errors import ValidationFailedError
from aerona.db.tables.dominion import (
    CREATURE_FIELDS,
    DESIGN_FIELDS,
    IMAGE_FIELDS,
    MAGIC_SITE_FIELDS,
    MIRACLE_FIELDS,
    SCALE_MAX,
    SCALE_MIN,
    THRONE_FIELDS,
    CreatureLessonRow,
    DivineCreatureRow,
    DominionRow,
    GodDesignRow,
    GodImageRow,
    GodScaleRow,
    MagicSiteRow,
    MiracleRecordRow,
    ThroneRow,
)
from aerona.domain.enums.culture import MagicSchool
from aerona.domain.enums.dominion import CreatureDeed, CreatureLesson, DivineScale, MagicSiteKind
from aerona.domain.enums.entity import EntityType
from aerona.engine.context import TickContext
from aerona.engine.divine.control import apply
from aerona.engine.dominion.creatures import raise_creature, teach
from aerona.engine.dominion.sites import SiteTally, reveal
from aerona.engine.gatherings.control import Values, allowed, entity, found, node
from aerona.engine.primitives.numbers import clamp_int

PLACE_TYPES = frozenset({EntityType.PLACE, EntityType.REGION, EntityType.SETTLEMENT, EntityType.STRUCTURE})


async def set_dominion(ctx: TickContext, god_id: int, region_id: int, strength: int, *, hold: bool) -> DominionRow:
    await node(ctx, god_id, "god")
    region = await entity(ctx, region_id, "region")
    if region.entity_type is not EntityType.REGION:
        raise ValidationFailedError("Dominion lies over regions.")
    row = await ctx.session.get(DominionRow, (god_id, region_id))
    if row is None:
        row = DominionRow(god_node_id=god_id, region_entity_id=region_id, epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    apply(row, {"strength": clamp_int(strength, 0, 100)}, [] if hold else ["strength"])
    await ctx.session.flush()
    return row


async def delete_dominion(ctx: TickContext, god_id: int, region_id: int) -> None:
    await ctx.session.delete(await found(ctx, DominionRow, (god_id, region_id), "dominion"))
    await ctx.session.flush()


async def set_scale(ctx: TickContext, god_id: int, scale: DivineScale, value: int, *, hold: bool) -> GodScaleRow:
    await node(ctx, god_id, "god")
    row = await ctx.session.get(GodScaleRow, (god_id, scale))
    if row is None:
        row = GodScaleRow(god_node_id=god_id, scale=scale, value=0, locked=[])
        ctx.session.add(row)
    apply(row, {"value": clamp_int(value, SCALE_MIN, SCALE_MAX)}, [] if hold else ["value"])
    await ctx.session.flush()
    return row


async def delete_scale(ctx: TickContext, god_id: int, scale: DivineScale) -> None:
    await ctx.session.delete(await found(ctx, GodScaleRow, (god_id, scale), "scale"))
    await ctx.session.flush()


async def edit_design(ctx: TickContext, god_id: int, values: Values, release: list[str]) -> GodDesignRow:
    await node(ctx, god_id, "god")
    row = await ctx.session.get(GodDesignRow, god_id)
    if row is None:
        row = GodDesignRow(god_node_id=god_id, locked=[])
        ctx.session.add(row)
    apply(row, allowed(values, DESIGN_FIELDS, "design"), release)
    await ctx.session.flush()
    return row


async def delete_design(ctx: TickContext, god_id: int) -> None:
    await ctx.session.delete(await found(ctx, GodDesignRow, god_id, "design"))
    await ctx.session.flush()


async def edit_image(ctx: TickContext, god_id: int, values: Values, release: list[str]) -> GodImageRow:
    await node(ctx, god_id, "god")
    row = await ctx.session.get(GodImageRow, god_id)
    if row is None:
        row = GodImageRow(god_node_id=god_id, locked=[])
        ctx.session.add(row)
    apply(row, allowed(values, IMAGE_FIELDS, "image"), release)
    await ctx.session.flush()
    return row


async def delete_image(ctx: TickContext, god_id: int) -> None:
    await ctx.session.delete(await found(ctx, GodImageRow, god_id, "image"))
    await ctx.session.flush()


async def edit_miracle(ctx: TickContext, miracle_id: int, values: Values, release: list[str]) -> MiracleRecordRow:
    row = apply(await found(ctx, MiracleRecordRow, miracle_id, "miracle"), allowed(values, MIRACLE_FIELDS, "miracle"), release)
    await ctx.session.flush()
    return row


async def delete_miracle(ctx: TickContext, miracle_id: int) -> None:
    await ctx.session.delete(await found(ctx, MiracleRecordRow, miracle_id, "miracle"))
    await ctx.session.flush()


async def create_site(ctx: TickContext, place_id: int, kind: MagicSiteKind, school: MagicSchool, strength: int, *, found_now: bool) -> MagicSiteRow:
    place = await entity(ctx, place_id, "place")
    if place.entity_type not in PLACE_TYPES:
        raise ValidationFailedError("A magic site lies at a place, region, settlement or structure.")
    row = MagicSiteRow(place_entity_id=place.id, kind=kind, school=school, strength=clamp_int(strength, 0, 100), locked=[])
    ctx.session.add(row)
    await ctx.session.flush()
    if found_now:
        await reveal(ctx, row, None, SiteTally())
    await ctx.session.flush()
    return row


async def edit_site(ctx: TickContext, site_id: int, values: Values, release: list[str]) -> MagicSiteRow:
    row = apply(await found(ctx, MagicSiteRow, site_id, "magic site"), allowed(values, MAGIC_SITE_FIELDS, "magic site"), release)
    await ctx.session.flush()
    return row


async def reveal_site(ctx: TickContext, site_id: int, finder_id: int | None) -> MagicSiteRow:
    row = await found(ctx, MagicSiteRow, site_id, "magic site")
    if row.found_epoch is not None:
        raise ValidationFailedError("This magic site is already found.")
    finder = await entity(ctx, finder_id, "finder") if finder_id is not None else None
    await reveal(ctx, row, finder, SiteTally())
    await ctx.session.flush()
    return row


async def delete_site(ctx: TickContext, site_id: int) -> None:
    await ctx.session.delete(await found(ctx, MagicSiteRow, site_id, "magic site"))
    await ctx.session.flush()


async def create_throne(ctx: TickContext, place_id: int, power: int, holder_id: int | None) -> ThroneRow:
    place = await entity(ctx, place_id, "place")
    if place.world_id is None:
        raise ValidationFailedError("A throne of power stands on a world.")
    if await ctx.session.scalar(select(ThroneRow.id).where(ThroneRow.place_entity_id == place.id)) is not None:
        raise ValidationFailedError(f"A throne of power already stands at {place.name}.")
    if holder_id is not None:
        await node(ctx, holder_id, "holder")
    row = ThroneRow(world_id=place.world_id, place_entity_id=place.id, power=clamp_int(power, 0, 100), holder_node_id=holder_id, locked=[])
    if holder_id is not None:
        row.since_epoch = ctx.epoch
        row.locked = ["holder_node_id"]
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def edit_throne(ctx: TickContext, throne_id: int, values: Values, release: list[str]) -> ThroneRow:
    row = apply(await found(ctx, ThroneRow, throne_id, "throne"), allowed(values, THRONE_FIELDS, "throne"), release)
    await ctx.session.flush()
    return row


async def delete_throne(ctx: TickContext, throne_id: int) -> None:
    await ctx.session.delete(await found(ctx, ThroneRow, throne_id, "throne"))
    await ctx.session.flush()


async def raise_divine_creature(ctx: TickContext, god_id: int, *, name: str, description: str, home_id: int) -> DivineCreatureRow:
    await node(ctx, god_id, "god")
    home = await entity(ctx, home_id, "home")
    if home.entity_type not in {EntityType.PLACE, EntityType.REGION}:
        raise ValidationFailedError("A divine creature makes its home in a place or a region.")
    return await raise_creature(ctx, god_id, name=name, description=description, home_id=home.id)


async def edit_creature(ctx: TickContext, creature_id: int, values: Values, release: list[str]) -> DivineCreatureRow:
    row = apply(await found(ctx, DivineCreatureRow, creature_id, "divine creature"), allowed(values, CREATURE_FIELDS, "divine creature"), release)
    await ctx.session.flush()
    return row


async def teach_creature(ctx: TickContext, creature_id: int, deed: CreatureDeed, lesson: CreatureLesson) -> CreatureLessonRow:
    return await teach(ctx, await found(ctx, DivineCreatureRow, creature_id, "divine creature"), deed, lesson)


async def set_creature_weight(ctx: TickContext, creature_id: int, deed: CreatureDeed, weight: int, *, hold: bool) -> DivineCreatureRow:
    row = await found(ctx, DivineCreatureRow, creature_id, "divine creature")
    table = ctx.rules.divine_creatures
    row.weights = {**(row.weights or {}), deed.value: clamp_int(weight, table.weight_min, table.weight_max)}
    row.locked = sorted({*row.locked, "weights"}) if hold else [key for key in row.locked if key != "weights"]
    await ctx.session.flush()
    return row


async def release_creature(ctx: TickContext, creature_id: int) -> None:
    await ctx.session.delete(await found(ctx, DivineCreatureRow, creature_id, "divine creature"))
    await ctx.session.flush()
