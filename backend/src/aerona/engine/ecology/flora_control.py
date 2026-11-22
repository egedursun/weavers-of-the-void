from sqlalchemy import select

from aerona.catalog.life.domain import GROWN
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.flora import CropPestRow, PlantProfileRow, RegionCropRow, WorldBiochemistryRow
from aerona.domain.enums.ecology import Biochemistry
from aerona.engine.context import TickContext
from aerona.engine.ecology.biochemistry import LIFE_FIXUP, tolerated
from aerona.engine.ecology.control import Values, patch, region_of, species_of
from aerona.engine.ecology.profiles import Nature, SpeciesSpec, add_plant_profile, cycle_of, profile_of
from aerona.engine.polity.control import lock


async def plant_of(ctx: TickContext, species_id: int) -> PlantProfileRow:
    species = await species_of(ctx, species_id)
    profile = await profile_of(ctx, species)
    if profile.species_class not in GROWN:
        raise ValidationFailedError(f"{species.name} is not a plant or a fungus; set its class first.")
    row = await ctx.session.get(PlantProfileRow, species_id)
    if row is None:
        nature = Nature(profile.body_plan, profile.size_class, profile.diet, profile.sociality, profile.nocturnal, profile.migratory, profile.species_class)
        row = add_plant_profile(ctx, species_id, cycle_of(SpeciesSpec(), nature, profile.lifespan_years))
        await ctx.session.flush()
    return row


async def edit_plant(ctx: TickContext, species_id: int, values: Values, *, release: list[str]) -> PlantProfileRow:
    row = await plant_of(ctx, species_id)
    if values.get("cultivar_of_id") is not None:
        if int(values["cultivar_of_id"]) == species_id:
            raise ValidationFailedError("A plant cannot be bred from itself.")
        await plant_of(ctx, int(values["cultivar_of_id"]))
    patch(row, values, release)
    await ctx.session.flush()
    return row


async def set_crop(ctx: TickContext, region_id: int, plant_id: int, share: int | None, *, hold: bool, release: list[str]) -> RegionCropRow:
    await region_of(ctx, region_id)
    await plant_of(ctx, plant_id)
    row = await ctx.session.get(RegionCropRow, (region_id, plant_id))
    if row is None:
        row = RegionCropRow(region_entity_id=region_id, plant_entity_id=plant_id, share=ctx.rules.flora.new_crop_share, since_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    if share is not None:
        row.share = max(0, min(PERCENT, share))
        if hold:
            row.locked = lock(row.locked, "share")
    row.locked = [item for item in row.locked if item not in release]
    await ctx.session.flush()
    return row


async def drop_crop(ctx: TickContext, region_id: int, plant_id: int) -> None:
    row = await ctx.session.get(RegionCropRow, (region_id, plant_id))
    if row is None:
        raise NotFoundError("That crop is not sown there.")
    await ctx.session.delete(row)
    await ctx.session.flush()


async def set_crop_pest(ctx: TickContext, plant_id: int, pest_id: int, *, present: bool) -> CropPestRow | None:
    await plant_of(ctx, plant_id)
    await species_of(ctx, pest_id)
    if plant_id == pest_id:
        raise ValidationFailedError("A plant cannot be its own pest.")
    row = await ctx.session.get(CropPestRow, (plant_id, pest_id))
    if not present:
        if row is None:
            raise NotFoundError("That pest does not feed on that crop.")
        await ctx.session.delete(row)
        await ctx.session.flush()
        return None
    if row is None:
        row = CropPestRow(plant_entity_id=plant_id, pest_entity_id=pest_id, since_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    await ctx.session.flush()
    return row


async def set_world_life(ctx: TickContext, world_id: int, biochemistry: Biochemistry, *, present: bool) -> tuple[Biochemistry, ...]:
    world = await ctx.session.get(WorldRow, world_id)
    if world is None:
        raise NotFoundError("No such world.")
    key = f"{LIFE_FIXUP}.{world_id}"
    if await ctx.session.get(AppliedFixupRow, key) is None:
        for kind in await tolerated(ctx.session, world_id):
            ctx.session.add(WorldBiochemistryRow(world_id=world_id, biochemistry=kind))
        ctx.session.add(AppliedFixupRow(key=key, result={"by_hand": True}))
        await ctx.session.flush()
    row = await ctx.session.get(WorldBiochemistryRow, (world_id, biochemistry))
    if present and row is None:
        ctx.session.add(WorldBiochemistryRow(world_id=world_id, biochemistry=biochemistry))
    if not present and row is not None:
        await ctx.session.delete(row)
    await ctx.session.flush()
    return tuple(await ctx.session.scalars(select(WorldBiochemistryRow.biochemistry).where(WorldBiochemistryRow.world_id == world_id)))
