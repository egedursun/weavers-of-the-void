from collections.abc import Mapping
from typing import Any

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.base import Base
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.ecology import BeastProfileRow, HerdRow, SpeciesHostRow, SpeciesProfileRow, SpeciesRangeRow, SpeciesUseRow, SpeciesYieldRow
from aerona.db.tables.entities import EntityRow, EntityTraitRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.ecology import BeastTemper, DomesticationStage, RangeTrend, SpeciesUse
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityType
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.society import CreatureTrait
from aerona.domain.models.entity_stats import BeastStats
from aerona.engine.context import TickContext
from aerona.engine.ecology.beasts import profile_beast
from aerona.engine.ecology.domestication import offspring
from aerona.engine.ecology.profiles import profile_of
from aerona.engine.lore.control import bounds, coerce
from aerona.engine.polity.control import lock
from aerona.engine.primitives.queries import connect, living_entity
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.stats import stat

Values = Mapping[str, Any]


def patch(row: Base, values: Values, release: list[str]) -> Base:
    limits = bounds(row)
    for key, value in values.items():
        setattr(row, key, coerce(row, key, value, limits))
        if hasattr(row, "locked"):
            row.locked = lock(row.locked, key)
    if hasattr(row, "locked"):
        row.locked = [item for item in row.locked if item not in release]
    return row


async def species_of(ctx: TickContext, species_id: int) -> EntityRow:
    species = await living_entity(ctx.session, species_id)
    if species is None or species.entity_type is not EntityType.SPECIES:
        raise NotFoundError("No such living species.")
    return species


async def region_of(ctx: TickContext, region_id: int) -> EntityRow:
    region = await living_entity(ctx.session, region_id)
    if region is None or region.entity_type is not EntityType.REGION:
        raise NotFoundError("No such region.")
    return region


async def edit_species(ctx: TickContext, species_id: int, values: Values, *, release: list[str]) -> SpeciesProfileRow:
    row = await profile_of(ctx, await species_of(ctx, species_id))
    patch(row, values, release)
    await ctx.session.flush()
    return row


async def edit_range(ctx: TickContext, species_id: int, region_id: int, values: Values, *, release: list[str]) -> SpeciesRangeRow:
    await species_of(ctx, species_id)
    await region_of(ctx, region_id)
    row = await ctx.session.get(SpeciesRangeRow, (species_id, region_id))
    if row is None:
        row = SpeciesRangeRow(
            species_entity_id=species_id,
            region_entity_id=region_id,
            abundance=0,
            trend=RangeTrend.RISING,
            fit=PERCENT // 2,
            hunted=0,
            since_epoch=ctx.epoch,
            updated_epoch=ctx.epoch,
            locked=[],
        )
        ctx.session.add(row)
    patch(row, values, release)
    await ctx.session.flush()
    return row


async def move_range(ctx: TickContext, species_id: int, source_id: int, target_id: int) -> SpeciesRangeRow:
    await species_of(ctx, species_id)
    await region_of(ctx, target_id)
    source = await ctx.session.get(SpeciesRangeRow, (species_id, source_id))
    if source is None:
        raise NotFoundError("The species does not range there.")
    target = await edit_range(ctx, species_id, target_id, {}, release=[])
    target.abundance = min(PERCENT, target.abundance + source.abundance)
    await ctx.session.delete(source)
    await ctx.session.flush()
    return target


async def drop_range(ctx: TickContext, species_id: int, region_id: int) -> None:
    row = await ctx.session.get(SpeciesRangeRow, (species_id, region_id))
    if row is None:
        raise NotFoundError("The species does not range there.")
    await ctx.session.delete(row)
    await ctx.session.flush()


async def set_yield(
    ctx: TickContext, species_id: int, product: str, *, commodity: CommodityKind | None, material: MaterialKind | None, rate: int
) -> SpeciesYieldRow | None:
    await species_of(ctx, species_id)
    row = await ctx.session.get(SpeciesYieldRow, (species_id, product))
    if rate == 0:
        if row is not None:
            await ctx.session.delete(row)
            await ctx.session.flush()
        return None
    if rate < 0:
        raise ValidationFailedError("A yield cannot be negative.")
    if row is None:
        row = SpeciesYieldRow(species_entity_id=species_id, product=product, commodity=commodity, material=material, rate=rate)
        ctx.session.add(row)
    row.commodity, row.material, row.rate = commodity, material, rate
    await ctx.session.flush()
    return row


async def set_use(ctx: TickContext, species_id: int, use: SpeciesUse, *, held: bool) -> SpeciesUseRow | None:
    await species_of(ctx, species_id)
    row = await ctx.session.get(SpeciesUseRow, (species_id, use))
    if not held:
        if row is not None:
            await ctx.session.delete(row)
            await ctx.session.flush()
        return None
    if row is None:
        row = SpeciesUseRow(species_entity_id=species_id, use=use)
        ctx.session.add(row)
        await ctx.session.flush()
    return row


async def set_host(ctx: TickContext, species_id: int, disease_id: int, *, carried: bool, immune: bool) -> SpeciesHostRow | None:
    await species_of(ctx, species_id)
    disease = await living_entity(ctx.session, disease_id)
    if disease is None or disease.entity_type is not EntityType.DISEASE:
        raise NotFoundError("No such sickness.")
    row = await ctx.session.get(SpeciesHostRow, (species_id, disease_id))
    if not carried:
        if row is not None:
            await ctx.session.delete(row)
            await ctx.session.flush()
        return None
    if row is None:
        row = SpeciesHostRow(species_entity_id=species_id, disease_entity_id=disease_id, immune=immune)
        ctx.session.add(row)
    row.immune = immune
    await ctx.session.flush()
    return row


async def make_sacred(ctx: TickContext, species_id: int, son_id: int | None) -> SpeciesProfileRow:
    species = await species_of(ctx, species_id)
    row = await profile_of(ctx, species)
    repository = EntityRepository(ctx.session)
    if son_id is None:
        row.sacred_to_node_id = None
        held = await ctx.session.get(EntityTraitRow, (species.id, CreatureTrait.SACRED_ANIMAL))
        if held is not None:
            await ctx.session.delete(held)
    else:
        if await ctx.session.get(SonRow, son_id) is None:
            raise NotFoundError("No such son.")
        row.sacred_to_node_id = son_id
        await repository.add_trait(species.id, CreatureTrait.SACRED_ANIMAL)
    row.locked = lock(row.locked, "sacred_to_node_id")
    await ctx.session.flush()
    return row


async def domesticate_now(ctx: TickContext, species_id: int, community_id: int) -> EntityRow:
    species = await species_of(ctx, species_id)
    keeper = await living_entity(ctx.session, community_id)
    if keeper is None or keeper.entity_type not in COMMUNITY_TYPES:
        raise NotFoundError("No such community.")
    child = await offspring(ctx, species, keeper, stage=DomesticationStage.DOMESTICATED)
    ctx.session.add(
        HerdRow(
            community_entity_id=keeper.id,
            species_entity_id=child.id,
            head=ctx.rules.domestication.starting_head,
            stage=DomesticationStage.DOMESTICATED,
            since_epoch=ctx.epoch,
            fed_epochs=0,
            locked=[],
        )
    )
    await ctx.session.flush()
    return child


async def edit_herd(ctx: TickContext, community_id: int, species_id: int, values: Values, *, release: list[str]) -> HerdRow:
    row = await ctx.session.get(HerdRow, (community_id, species_id))
    if row is None:
        keeper = await living_entity(ctx.session, community_id)
        if keeper is None or keeper.entity_type not in COMMUNITY_TYPES:
            raise NotFoundError("No such community.")
        await species_of(ctx, species_id)
        row = HerdRow(
            community_entity_id=community_id,
            species_entity_id=species_id,
            head=0,
            stage=DomesticationStage.TAMED,
            since_epoch=ctx.epoch,
            fed_epochs=0,
            locked=[],
        )
        ctx.session.add(row)
    patch(row, values, release)
    await ctx.session.flush()
    return row


async def beast_of(ctx: TickContext, beast_id: int) -> tuple[EntityRow, BeastProfileRow]:
    beast = await living_entity(ctx.session, beast_id)
    if beast is None or beast.entity_type is not EntityType.BEAST:
        raise NotFoundError("No such living beast.")
    row = await ctx.session.get(BeastProfileRow, beast.id) or await profile_beast(ctx, beast, None)
    return beast, row


async def edit_beast(ctx: TickContext, beast_id: int, values: Values, *, release: list[str]) -> BeastProfileRow:
    _, row = await beast_of(ctx, beast_id)
    patch(row, values, release)
    await ctx.session.flush()
    return row


async def rouse(ctx: TickContext, beast_id: int, *, awake: bool) -> BeastProfileRow:
    _, row = await beast_of(ctx, beast_id)
    row.temper = BeastTemper.HUNGRY if awake else BeastTemper.SLEEPING
    row.woke_epoch = ctx.epoch if awake else row.woke_epoch
    row.locked = lock(row.locked, "temper")
    await ctx.session.flush()
    return row


async def bind_beast(ctx: TickContext, beast_id: int, node_id: int | None, *, tamed: bool) -> BeastProfileRow:
    _, row = await beast_of(ctx, beast_id)
    if node_id is None:
        row.bound_to_node_id, row.temper = None, BeastTemper.HUNGRY
    else:
        holder = await living_entity(ctx.session, node_id)
        if holder is None and await ctx.session.get(SonRow, node_id) is None:
            raise NotFoundError("No one by that name to bind it to.")
        row.bound_to_node_id, row.temper = node_id, BeastTemper.TAMED if tamed else BeastTemper.BOUND
    row.locked = lock(row.locked, "temper")
    await ctx.session.flush()
    return row


async def shift_lair(ctx: TickContext, beast_id: int, place_id: int) -> BeastProfileRow:
    beast, row = await beast_of(ctx, beast_id)
    place = await living_entity(ctx.session, place_id)
    if place is None or place.entity_type not in {EntityType.PLACE, EntityType.REGION}:
        raise NotFoundError("A lair is a place or a region.")
    row.lair_place_id = place.id
    beast.location_id = place.id
    row.locked = lock(row.locked, "lair_place_id")
    await ctx.session.flush()
    return row


async def spawn_beast(ctx: TickContext, species_id: int) -> EntityRow:
    species = await species_of(ctx, species_id)
    region = await ctx.session.scalar(
        select(SpeciesRangeRow.region_entity_id).where(SpeciesRangeRow.species_entity_id == species.id).order_by(SpeciesRangeRow.abundance.desc()).limit(1)
    )
    beast = await create_record(
        ctx,
        RecordSpec(
            name=f"The Great {species.name}",
            entity_type=EntityType.BEAST,
            stats=BeastStats(
                hp=(stat(species, "hp") or PERCENT) * 2,
                danger=stat(species, "danger"),
                strength=stat(species, "strength"),
                agility=stat(species, "agility"),
                cunning=stat(species, "intelligence"),
                renown=PERCENT // 5,
                terror=PERCENT // 10,
            ),
            body=f"Called forth as the greatest of the {species.name}.",
            power=max(species.power_level, 3),
            world_id=species.world_id,
            location_id=region or species.location_id,
        ),
    )
    await profile_beast(ctx, beast, species)
    await connect(ctx.session, beast.id, species.id, BondKind.DESCENDS_FROM, ctx.epoch, description="the greatest of its kind")
    return beast
