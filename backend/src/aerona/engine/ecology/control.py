from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.base import Base
from aerona.db.kind_concepts.nature import PRODUCT_PARTS
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.ecology import (
    BeastProfileRow,
    HerdRow,
    SpeciesCustomUseRow,
    SpeciesHostRow,
    SpeciesProductRow,
    SpeciesProfileRow,
    SpeciesRangeRow,
    SpeciesUseKindRow,
    SpeciesUseRow,
)
from aerona.db.tables.economy import WorldMaterialRow
from aerona.db.tables.entities import EntityRow, EntityTraitRow
from aerona.db.tables.kinds import GoodKindRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import ItemDeed
from aerona.domain.enums.ecology import AnimalRole, BeastTemper, DomesticationStage, FoodLink, RangeTrend, SizeClass
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus, EntityType
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.nature_kinds import ProductPart
from aerona.domain.enums.society import CreatureTrait
from aerona.domain.models.entity_stats import BeastStats, SpeciesStats, revised
from aerona.engine.body.book import ensure_species_body
from aerona.engine.context import TickContext
from aerona.engine.ecology.beasts import fall, hand_over, owned_items, profile_beast
from aerona.engine.ecology.domestication import offspring
from aerona.engine.ecology.profiles import SpeciesSpec, profile_of
from aerona.engine.ecology.totems import drop_totem, found_totem
from aerona.engine.polity.control import lock
from aerona.engine.primitives.edits import bounds, coerce
from aerona.engine.primitives.queries import close, connect, directed_bond, living_entity
from aerona.engine.primitives.records import RecordSpec, create_record, retire_in
from aerona.engine.primitives.stats import stat, stat_or

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


async def world_material_of(ctx: TickContext, material_id: int | None) -> WorldMaterialRow | None:
    if material_id is None:
        return None
    found = await ctx.session.get(WorldMaterialRow, material_id)
    if found is None:
        raise NotFoundError("No such world material.")
    return found


async def set_yield(
    ctx: TickContext,
    species_id: int,
    product: str,
    *,
    commodity: CommodityKind | None,
    material: MaterialKind | None,
    rate: int,
    world_material_id: int | None = None,
    part: ProductPart | None = None,
    good_kind_id: int | None = None,
) -> SpeciesProductRow | None:
    await species_of(ctx, species_id)
    stuff = await world_material_of(ctx, world_material_id)
    if stuff is not None and material is None:
        material = stuff.base_kind
    row = await ctx.session.get(SpeciesProductRow, (species_id, product))
    if rate == 0:
        if row is not None:
            await ctx.session.delete(row)
            await ctx.session.flush()
        return None
    if rate < 0:
        raise ValidationFailedError("A yield cannot be negative.")
    if row is None:
        row = SpeciesProductRow(
            species_entity_id=species_id, product=product, commodity=commodity, material=material, rate=rate, part=PRODUCT_PARTS.get(product), locked=[]
        )
        ctx.session.add(row)
    row.commodity, row.material, row.rate, row.world_material_id = commodity, material, rate, world_material_id
    if part is not None:
        row.part = part
    if good_kind_id is not None:
        if await ctx.session.get(GoodKindRow, good_kind_id) is None:
            raise ValidationFailedError("No such good.")
        row.good_kind_id = good_kind_id
    await ctx.session.flush()
    return row


async def set_use(ctx: TickContext, species_id: int, use: AnimalRole, *, held: bool) -> SpeciesUseRow | None:
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


async def set_host(ctx: TickContext, species_id: int, disease_id: int, *, carried: bool, immune: bool, release: bool = False) -> SpeciesHostRow | None:
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
        row = SpeciesHostRow(species_entity_id=species_id, disease_entity_id=disease_id, immune=immune, locked=[])
        ctx.session.add(row)
    row.immune = immune
    row.locked = [item for item in row.locked if item != "immune"] if release else lock(row.locked, "immune")
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


async def commonest_species(ctx: TickContext, region_id: int | None) -> int | None:
    if region_id is None:
        return None
    return await ctx.session.scalar(
        select(SpeciesRangeRow.species_entity_id)
        .join(EntityRow, EntityRow.id == SpeciesRangeRow.species_entity_id)
        .where(
            SpeciesRangeRow.region_entity_id == region_id,
            SpeciesRangeRow.abundance > 0,
            EntityRow.entity_type == EntityType.SPECIES,
            EntityRow.status == EntityStatus.CANON,
        )
        .order_by(SpeciesRangeRow.abundance.desc(), SpeciesRangeRow.species_entity_id)
        .limit(1)
    )


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
                hp=(stat_or(species, "hp", PERCENT)) * 2,
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


@dataclass(frozen=True)
class NewSpecies:
    name: str
    description: str
    region_id: int
    spec: SpeciesSpec
    stats: SpeciesStats
    power: int = 2
    traits: tuple[CreatureTrait, ...] = ()
    abundance: int | None = None


async def create_species(ctx: TickContext, draft: NewSpecies) -> EntityRow:
    region = await region_of(ctx, draft.region_id)
    species = await create_record(
        ctx,
        RecordSpec(
            name=draft.name,
            entity_type=EntityType.SPECIES,
            body=draft.description,
            stats=draft.stats,
            power=draft.power,
            world_id=region.world_id,
            location_id=region.id,
            traits=list(dict.fromkeys(draft.traits)),
        ),
    )
    await ensure_species_body(ctx.session, species, draft.spec.body_plan)
    await profile_of(ctx, species, draft.spec)
    ctx.session.add(
        SpeciesRangeRow(
            species_entity_id=species.id,
            region_entity_id=region.id,
            abundance=draft.abundance if draft.abundance is not None else ctx.rules.ecology.initial_base,
            trend=RangeTrend.STEADY,
            fit=PERCENT // 2,
            hunted=0,
            since_epoch=ctx.epoch,
            updated_epoch=ctx.epoch,
            locked=[],
        )
    )
    await connect(ctx.session, species.id, region.id, BondKind.LIVES_IN, ctx.epoch, description="set there by the Creator")
    await ctx.session.flush()
    return species


@dataclass(frozen=True)
class NewBeast:
    name: str
    description: str
    stats: BeastStats
    species_id: int | None = None
    lair_id: int | None = None
    size_class: SizeClass | None = None
    temper: BeastTemper | None = None
    power: int = 3
    abilities: dict[str, int] = field(default_factory=dict)


ABILITIES = frozenset({"endurance", "perception", "willpower", "intelligence", "lifespan", "age"})


async def create_beast(ctx: TickContext, draft: NewBeast, *, world_id: int | None = None) -> EntityRow:
    species = await species_of(ctx, draft.species_id) if draft.species_id is not None else None
    lair = await living_entity(ctx.session, draft.lair_id) if draft.lair_id is not None else None
    if draft.lair_id is not None and (lair is None or lair.entity_type not in {EntityType.PLACE, EntityType.REGION}):
        raise NotFoundError("A lair is a place or a region.")
    home = lair.id if lair is not None else species.location_id if species is not None else None
    world = lair.world_id if lair is not None else species.world_id if species is not None else world_id
    stats = draft.stats
    if stats.hp is None:
        stats = revised(stats, {"hp": (stat_or(species, "hp", PERCENT)) * 2 if species is not None else PERCENT * 2})
    beast = await create_record(
        ctx,
        RecordSpec(
            name=draft.name,
            entity_type=EntityType.BEAST,
            stats=stats,
            body=draft.description,
            power=draft.power,
            world_id=world,
            location_id=home,
        ),
    )
    row = await profile_beast(ctx, beast, species, draft.size_class)
    if lair is not None:
        row.lair_place_id = lair.id
    if draft.temper is not None:
        row.temper = draft.temper
    patch(row, {key: value for key, value in draft.abilities.items() if key in ABILITIES}, [])
    row.locked = []
    if species is not None:
        await connect(ctx.session, beast.id, species.id, BondKind.DESCENDS_FROM, ctx.epoch, description="the greatest of its kind")
    await ctx.session.flush()
    return beast


async def slay_beast(ctx: TickContext, beast_id: int, slayer_id: int | None) -> str:
    beast, row = await beast_of(ctx, beast_id)
    if slayer_id is not None:
        slayer = await living_entity(ctx.session, slayer_id)
        if slayer is None:
            raise NotFoundError("No such slayer.")
        await connect(ctx.session, slayer.id, beast.id, BondKind.KILLED, ctx.epoch, description="slew the beast")
    await retire_in(ctx, beast, "slain by the Creator's will" if slayer_id is None else "slain")
    told = await fall(ctx, beast, row)
    await ctx.session.flush()
    return told


async def drop_herd(ctx: TickContext, community_id: int, species_id: int) -> None:
    row = await ctx.session.get(HerdRow, (community_id, species_id))
    if row is None:
        raise NotFoundError("That community keeps no such herd.")
    await ctx.session.delete(row)
    await ctx.session.flush()


async def set_prey(ctx: TickContext, hunter_id: int, prey_id: int, link: FoodLink) -> SpeciesProfileRow:
    hunter = await species_of(ctx, hunter_id)
    prey = await species_of(ctx, prey_id)
    if hunter.id == prey.id:
        raise ValidationFailedError("A kind does not hunt itself.")
    row = await profile_of(ctx, hunter)
    row.pinned_prey = sorted({*row.pinned_prey, prey.id}) if link is FoodLink.PINNED else [item for item in row.pinned_prey if item != prey.id]
    row.barred_prey = sorted({*row.barred_prey, prey.id}) if link is FoodLink.BARRED else [item for item in row.barred_prey if item != prey.id]
    bond = await directed_bond(ctx.session, hunter.id, prey.id, BondKind.HUNTS)
    if link is FoodLink.PINNED and bond is None:
        await connect(ctx.session, hunter.id, prey.id, BondKind.HUNTS, ctx.epoch, description="set by the Creator")
    if link is FoodLink.BARRED and bond is not None:
        await close(ctx.session, bond, ctx.epoch, "forbidden by the Creator")
    await ctx.session.flush()
    return row


async def set_totem(ctx: TickContext, people_id: int, species_id: int | None) -> EntityRow | None:
    people = await living_entity(ctx.session, people_id)
    if people is None or people.entity_type is not EntityType.PEOPLE:
        raise NotFoundError("Only a living people keeps a totem.")
    await drop_totem(ctx, people.id)
    if species_id is None:
        await ctx.session.flush()
        return None
    tradition = await found_totem(ctx, people, await species_of(ctx, species_id))
    await ctx.session.flush()
    return tradition


async def move_treasure(ctx: TickContext, beast_id: int, item_id: int, *, into_hoard: bool, receiver_id: int | None) -> EntityRow:
    beast, _ = await beast_of(ctx, beast_id)
    item = await living_entity(ctx.session, item_id)
    if item is None or item.entity_type is not EntityType.ITEM:
        raise NotFoundError("No such item.")
    if into_hoard:
        await hand_over(ctx, item.id, beast.id, ItemDeed.OWNED, f"laid in the hoard of {beast.name} by the Creator")
        return item
    if item.id not in await owned_items(ctx, [beast.id]):
        raise ValidationFailedError(f"{item.name} is not in the hoard of {beast.name}.")
    receiver = await living_entity(ctx.session, receiver_id) if receiver_id is not None else None
    if receiver is None:
        raise NotFoundError("Name who takes the item from the hoard.")
    await hand_over(ctx, item.id, receiver.id, ItemDeed.OWNED, f"taken from the hoard of {beast.name} by the Creator")
    return item


async def use_kind_of(ctx: TickContext, kind_id: int) -> SpeciesUseKindRow:
    row = await ctx.session.get(SpeciesUseKindRow, kind_id)
    if row is None:
        raise NotFoundError("No such kind of keeping.")
    return row


async def create_use_kind(ctx: TickContext, name: str, base_use: AnimalRole, output_pct: int, description: str | None) -> SpeciesUseKindRow:
    if not name.strip():
        raise ValidationFailedError("A kind of keeping needs a name.")
    row = SpeciesUseKindRow(name=name.strip(), base_use=base_use, output_pct=output_pct, description=description, locked=[])
    patch(row, {"output_pct": output_pct}, [])
    row.locked = []
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def edit_use_kind(ctx: TickContext, kind_id: int, values: Values, *, release: list[str]) -> SpeciesUseKindRow:
    row = await use_kind_of(ctx, kind_id)
    patch(row, values, release)
    for species_id in list(await ctx.session.scalars(select(SpeciesCustomUseRow.species_entity_id).where(SpeciesCustomUseRow.kind_id == row.id))):
        await set_use(ctx, species_id, row.base_use, held=True)
    await ctx.session.flush()
    return row


async def drop_use_kind(ctx: TickContext, kind_id: int) -> None:
    await ctx.session.delete(await use_kind_of(ctx, kind_id))
    await ctx.session.flush()


async def set_custom_use(ctx: TickContext, species_id: int, kind_id: int, *, held: bool) -> SpeciesCustomUseRow | None:
    await species_of(ctx, species_id)
    kind = await use_kind_of(ctx, kind_id)
    row = await ctx.session.get(SpeciesCustomUseRow, (species_id, kind.id))
    if not held:
        if row is not None:
            await ctx.session.delete(row)
            await ctx.session.flush()
        return None
    if row is None:
        row = SpeciesCustomUseRow(species_entity_id=species_id, kind_id=kind.id)
        ctx.session.add(row)
    await set_use(ctx, species_id, kind.base_use, held=True)
    await ctx.session.flush()
    return row
