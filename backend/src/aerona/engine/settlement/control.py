from collections.abc import Mapping
from dataclasses import dataclass

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.settlement import ADMIN_MAX, DESIGN_PARAMETERS, DistrictDesignRow, DistrictRow
from aerona.db.tables.warfare import ArmyRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.settlement import BuildMaterial, DistrictKind, SizeTier, TreasuryEntry, WaterSupply
from aerona.domain.models.entity_stats import LawStats
from aerona.engine.context import TickContext
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.queries import connect
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.settlement.book import Town, ledger, town_of
from aerona.engine.settlement.districts import CONDITION_KEY, DISTRICT_LOCKS, LEVEL_KEY, MATERIAL_KEY, close_market, unify_market
from aerona.engine.settlement.life import add_district

PROFILE_NUMBERS = ("public_order", "crime", "unrest", "sanitation", "fire_risk", "prestige", "tax_rate")
CHOICES: dict[str, tuple[str, type[SizeTier] | type[WaterSupply] | type[BuildMaterial]]] = {
    "size_tier": ("profile", SizeTier),
    "water": ("infrastructure", WaterSupply),
    "walls_material": ("infrastructure", BuildMaterial),
}
FLAGS = ("sewers", "free_city", "rationing")
WALL_STUFF_KEY = "walls_world_material_id"
DESIGN_SCALES = ("housing", "food_store", "goods_store", "harbour")
POSITIVE_NUMBERS = ("militia", "investment_pool", "siege_supplies", "siege_water", "siege_disease", "construction_capacity", "hauling_capacity")
GARRISON_KEY = "garrison_entity_id"
FOREIGNERS_KEY = "foreigners"
INFRA_NUMBERS = {
    "walls_level": (0, 5),
    "walls_condition": (0, PERCENT),
    "gates": (0, 100000000),
    "roads": (0, 5),
    "towers": (0, 100000000),
    "granary_capacity": (0, 100000000),
    "warehouse_capacity": (0, 100000000),
    "harbour_capacity": (0, 100000000),
    "bridges": (0, 100000000),
    "irrigation": (0, 5),
}
PROFILE_KEYS = (*PROFILE_NUMBERS, *POSITIVE_NUMBERS, "admin_capacity", "size_tier", "free_city", "rationing", GARRISON_KEY, FOREIGNERS_KEY)
INFRA_KEYS = (*INFRA_NUMBERS, "water", "walls_material", "sewers", WALL_STUFF_KEY)


async def town(ctx: TickContext, settlement_id: int) -> Town:
    entity = await ctx.session.get(EntityRow, settlement_id)
    if entity is None or entity.entity_type is not EntityType.SETTLEMENT or entity.status is not EntityStatus.CANON:
        raise NotFoundError("No such settlement.")
    return await town_of(ctx, entity, await KnowledgeMap.load(ctx.session))


def lock(locked: list[str], key: str) -> list[str]:
    return locked if key in locked else [*locked, key]


def bounded(key: str, value: int | str | bool, low: int, high: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not low <= value <= high:
        raise ValidationFailedError(f"{key.replace('_', ' ').capitalize()} runs from {low} to {high}.")
    return value


def set_field(ctx: TickContext, found: Town, key: str, value: int | str | bool) -> None:
    profile, infrastructure = found.profile, found.infrastructure
    if key in PROFILE_NUMBERS:
        setattr(profile, key, bounded(key, value, 0, PERCENT))
        profile.locked = lock(profile.locked, key)
    elif key == "treasury":
        ledger(ctx, found, TreasuryEntry.GRANT, bounded(key, value, 0, 10**12) - profile.treasury, "set by the Creator")
    elif key in POSITIVE_NUMBERS:
        setattr(profile, key, bounded(key, value, 0, 10**12))
        profile.locked = lock(profile.locked, key)
    elif key == "admin_capacity":
        profile.admin_capacity = bounded(key, value, 0, ADMIN_MAX)
        profile.locked = lock(profile.locked, key)
    elif key in INFRA_NUMBERS:
        setattr(infrastructure, key, bounded(key, value, *INFRA_NUMBERS[key]))
        infrastructure.locked = lock(infrastructure.locked, key)
    elif key in CHOICES:
        holder, kind = CHOICES[key]
        try:
            setattr(infrastructure if holder == "infrastructure" else profile, key, kind(str(value)))
        except ValueError as error:
            raise ValidationFailedError(f"{value} is not a known {key.replace('_', ' ')}.") from error
        target = infrastructure if holder == "infrastructure" else profile
        target.locked = lock(target.locked, key)
    elif key == WALL_STUFF_KEY:
        infrastructure.walls_world_material_id = None if value in (0, False) else bounded(key, value, 1, 10**12)
        infrastructure.locked = lock(infrastructure.locked, key)
    elif key in FLAGS:
        target = infrastructure if key == "sewers" else profile
        setattr(target, key, bool(value))
        target.locked = lock(target.locked, key)
    else:
        raise ValidationFailedError(f"Unknown settlement field: {key}.")


async def set_garrison(ctx: TickContext, found: Town, army_id: int) -> None:
    if army_id == 0:
        found.profile.garrison_entity_id = None
    else:
        army = await ctx.session.get(ArmyRow, army_id)
        if army is None or army.owner_entity_id != found.entity.id or army.disbanded_epoch is not None:
            raise ValidationFailedError("Only a standing army of the settlement can garrison it.")
        found.profile.garrison_entity_id = army_id
    found.profile.locked = lock(found.profile.locked, GARRISON_KEY)


async def set_foreigners(ctx: TickContext, settlement_id: int, shares: Mapping[int, int]) -> Town:
    found = await town(ctx, settlement_id)
    for people_id, share in shares.items():
        people = await ctx.session.get(EntityRow, people_id)
        if people is None or people.entity_type is not EntityType.PEOPLE:
            raise ValidationFailedError("Foreigners must belong to a people.")
        bounded("foreign share", share, 0, PERCENT)
    if sum(shares.values()) > PERCENT:
        raise ValidationFailedError("Foreign shares cannot add up to more than the whole settlement.")
    found.profile.foreigners = {str(people_id): share for people_id, share in sorted(shares.items()) if share > 0}
    found.profile.locked = lock(found.profile.locked, FOREIGNERS_KEY)
    await ctx.session.flush()
    return found


async def edit_settlement(ctx: TickContext, settlement_id: int, values: Mapping[str, int | str | bool], *, release: list[str]) -> Town:
    found = await town(ctx, settlement_id)
    for key, value in values.items():
        if key == GARRISON_KEY:
            await set_garrison(ctx, found, bounded(key, value, 0, 10**12))
            continue
        set_field(ctx, found, key, value)
    unknown = [key for key in release if key not in PROFILE_KEYS and key not in INFRA_KEYS]
    if unknown:
        raise ValidationFailedError(f"Unknown settlement field: {unknown[0]}.")
    for key in release:
        found.profile.locked = [item for item in found.profile.locked if item != key]
        found.infrastructure.locked = [item for item in found.infrastructure.locked if item != key]
    await ctx.session.flush()
    return found


async def design_in(ctx: TickContext, design_id: int, world_id: int | None) -> DistrictDesignRow:
    design = await ctx.session.get(DistrictDesignRow, design_id)
    if design is None or design.world_id != world_id:
        raise NotFoundError("No such district design in this world.")
    return design


async def build_district(
    ctx: TickContext, settlement_id: int, kind: DistrictKind | None, *, material: BuildMaterial, son_id: int | None, design_id: int | None = None
) -> DistrictRow:
    found = await town(ctx, settlement_id)
    design = await design_in(ctx, design_id, found.entity.world_id) if design_id is not None else None
    chosen = design.base_kind if design is not None else kind
    if chosen is None:
        raise ValidationFailedError("Choose a district kind or a design.")
    district = await add_district(ctx, found, chosen, material=material, son_id=son_id, design_id=design.id if design is not None else None)
    await unify_market(ctx, found.entity, found.districts, material)
    await ctx.session.flush()
    return district


@dataclass(frozen=True)
class DistrictChange:
    level: int | None = None
    condition: int | None = None
    material: BuildMaterial | None = None
    kind: DistrictKind | None = None
    design_id: int | None = None
    clear_design: bool = False
    release: tuple[str, ...] = ()
    world_material_id: int | None = None
    clear_world_material: bool = False


def set_district_values(district: DistrictRow, change: DistrictChange) -> list[str]:
    locked = list(district.locked or [])
    if change.level is not None:
        if not 1 <= change.level <= 5:
            raise ValidationFailedError("A district's level runs from 1 to 5.")
        district.level = change.level
        locked = lock(locked, LEVEL_KEY)
    if change.condition is not None:
        if not 0 <= change.condition <= PERCENT:
            raise ValidationFailedError(f"A district's condition runs from 0 to {PERCENT}.")
        district.condition = change.condition
        locked = lock(locked, CONDITION_KEY)
    if change.material is not None:
        district.material = change.material
        locked = lock(locked, MATERIAL_KEY)
    if change.world_material_id is not None:
        district.world_material_id = change.world_material_id
        locked = lock(locked, MATERIAL_KEY)
    elif change.clear_world_material:
        district.world_material_id = None
    return locked


async def edit_district(ctx: TickContext, district_id: int, change: DistrictChange) -> DistrictRow:
    district = await ctx.session.get(DistrictRow, district_id)
    if district is None:
        raise NotFoundError("No such district.")
    locked = set_district_values(district, change)
    previous = district.kind
    if change.design_id is not None:
        settlement = await ctx.session.get(EntityRow, district.settlement_entity_id)
        design = await design_in(ctx, change.design_id, settlement.world_id if settlement is not None else None)
        district.design_id = design.id
        district.kind = design.base_kind
    elif change.clear_design:
        district.design_id = None
    if change.kind is not None:
        district.kind = change.kind
        if change.design_id is None:
            district.design_id = None
    unknown = [key for key in change.release if key not in DISTRICT_LOCKS]
    if unknown:
        raise ValidationFailedError(f"Unknown district field: {unknown[0]}.")
    district.locked = [key for key in locked if key not in change.release]
    await ctx.session.flush()
    if previous is DistrictKind.MARKET and district.kind is not DistrictKind.MARKET:
        await close_market(ctx.session, district.settlement_entity_id)
    if district.kind is DistrictKind.MARKET:
        found = await town(ctx, district.settlement_entity_id)
        await unify_market(ctx, found.entity, found.districts, district.material)
    await ctx.session.flush()
    return district


async def raze_district(ctx: TickContext, district_id: int) -> int:
    district = await ctx.session.get(DistrictRow, district_id)
    if district is None:
        raise NotFoundError("No such district.")
    settlement_id = district.settlement_entity_id
    market = district.kind is DistrictKind.MARKET
    await ctx.session.delete(district)
    await ctx.session.flush()
    if market:
        await close_market(ctx.session, settlement_id)
        await ctx.session.flush()
    return settlement_id


def design_value(key: str, value: int) -> int:
    low = -PERCENT if key == "sanitation" else 0
    high = 10**9 if key in DESIGN_SCALES else PERCENT * 3
    return bounded(key, value, low, high)


async def create_design(
    ctx: TickContext, world_id: int, name: str, base_kind: DistrictKind, values: Mapping[str, int], *, description: str | None, son_id: int | None
) -> DistrictDesignRow:
    unknown = [key for key in values if key not in DESIGN_PARAMETERS]
    if unknown:
        raise ValidationFailedError(f"Unknown district parameter: {unknown[0]}.")
    design = DistrictDesignRow(
        world_id=world_id,
        name=name,
        description=description,
        base_kind=base_kind,
        created_epoch=ctx.epoch,
        created_by_son_id=son_id,
        **{key: design_value(key, value) for key, value in values.items()},
    )
    ctx.session.add(design)
    await ctx.session.flush()
    return design


@dataclass(frozen=True)
class DesignChange:
    values: Mapping[str, int | None]
    name: str | None = None
    description: str | None = None
    base_kind: DistrictKind | None = None


async def edit_design(ctx: TickContext, design_id: int, change: DesignChange) -> DistrictDesignRow:
    design = await ctx.session.get(DistrictDesignRow, design_id)
    if design is None:
        raise NotFoundError("No such district design.")
    for key, value in change.values.items():
        if key not in DESIGN_PARAMETERS:
            raise ValidationFailedError(f"Unknown district parameter: {key}.")
        setattr(design, key, design_value(key, value) if value is not None else None)
    if change.name is not None:
        design.name = change.name
    if change.description is not None:
        design.description = change.description
    if change.base_kind is not None and change.base_kind is not design.base_kind:
        design.base_kind = change.base_kind
        for district in await ctx.session.scalars(select(DistrictRow).where(DistrictRow.design_id == design.id)):
            district.kind = change.base_kind
    await ctx.session.flush()
    return design


async def delete_design(ctx: TickContext, design_id: int) -> int:
    design = await ctx.session.get(DistrictDesignRow, design_id)
    if design is None:
        raise NotFoundError("No such district design.")
    world_id = design.world_id
    for district in await ctx.session.scalars(select(DistrictRow).where(DistrictRow.design_id == design.id)):
        district.design_id = None
    await ctx.session.delete(design)
    await ctx.session.flush()
    return world_id


async def set_tax(ctx: TickContext, settlement_id: int, rate: int) -> Town:
    if not 0 <= rate <= PERCENT:
        raise ValidationFailedError(f"Tax runs from 0 to {PERCENT}%.")
    found = await town(ctx, settlement_id)
    found.profile.tax_rate = rate
    found.profile.locked = lock(found.profile.locked, "tax_rate")
    await ctx.session.flush()
    return found


async def free_city(ctx: TickContext, settlement_id: int, free: bool) -> Town:
    found = await town(ctx, settlement_id)
    found.profile.free_city = free
    await ctx.session.flush()
    return found


async def grant_charter(ctx: TickContext, settlement_id: int, *, name: str | None, son_id: int | None) -> EntityRow:
    found = await town(ctx, settlement_id)
    if found.profile.charter_entity_id is not None:
        existing = await ctx.session.get(EntityRow, found.profile.charter_entity_id)
        if existing is not None and existing.status is EntityStatus.CANON:
            return existing
    charter = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.LAW,
            name=name or f"the Charter of {found.entity.name}",
            body=f"A charter granting {found.entity.name} its own courts, markets and walls.",
            stats=LawStats(justice=70, rigidity=40),
            power=3,
            location_id=found.entity.id,
            world_id=found.entity.world_id,
            subtype="charter",
            creator_son_id=son_id,
            pending=False,
        ),
    )
    await connect(ctx.session, charter.id, found.entity.id, BondKind.PART_OF, ctx.epoch, description="granted to")
    found.profile.charter_entity_id = charter.id
    found.profile.free_city = True
    await ctx.session.flush()
    return charter
