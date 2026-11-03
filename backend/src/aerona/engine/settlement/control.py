from collections.abc import Mapping

from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.settlement import DistrictRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.settlement import BuildMaterial, DistrictKind, SizeTier, TreasuryEntry, WaterSupply
from aerona.domain.models.entity_stats import LawStats
from aerona.engine.context import TickContext
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.queries import connect
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.settlement.book import Town, ledger, town_of
from aerona.engine.settlement.life import add_district

PROFILE_NUMBERS = ("public_order", "crime", "unrest", "sanitation", "fire_risk", "prestige", "tax_rate")
CHOICES: dict[str, tuple[str, type[SizeTier] | type[WaterSupply] | type[BuildMaterial]]] = {
    "size_tier": ("profile", SizeTier),
    "water": ("infrastructure", WaterSupply),
    "walls_material": ("infrastructure", BuildMaterial),
}
FLAGS = ("sewers", "free_city", "rationing")
POSITIVE_NUMBERS = ("militia", "investment_pool", "siege_supplies", "siege_water", "siege_disease")
INFRA_NUMBERS = {
    "walls_level": (0, 5),
    "walls_condition": (0, PERCENT),
    "gates": (0, 20),
    "roads": (0, 5),
    "towers": (0, 20),
    "granary_capacity": (0, 100000000),
    "warehouse_capacity": (0, 100000000),
    "harbour_capacity": (0, 100000000),
}


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
    elif key in FLAGS:
        setattr(infrastructure if key == "sewers" else profile, key, bool(value))
    else:
        raise ValidationFailedError(f"Unknown settlement field: {key}.")


async def edit_settlement(ctx: TickContext, settlement_id: int, values: Mapping[str, int | str | bool], *, release: list[str]) -> Town:
    found = await town(ctx, settlement_id)
    for key, value in values.items():
        set_field(ctx, found, key, value)
    for key in release:
        found.profile.locked = [item for item in found.profile.locked if item != key]
        found.infrastructure.locked = [item for item in found.infrastructure.locked if item != key]
    await ctx.session.flush()
    return found


async def build_district(ctx: TickContext, settlement_id: int, kind: DistrictKind, *, material: BuildMaterial, son_id: int | None) -> DistrictRow:
    found = await town(ctx, settlement_id)
    return await add_district(ctx, found, kind, material=material, son_id=son_id)


async def edit_district(ctx: TickContext, district_id: int, *, level: int | None, condition: int | None, material: BuildMaterial | None) -> DistrictRow:
    district = await ctx.session.get(DistrictRow, district_id)
    if district is None:
        raise NotFoundError("No such district.")
    if level is not None:
        if not 1 <= level <= 5:
            raise ValidationFailedError("A district's level runs from 1 to 5.")
        district.level = level
    if condition is not None:
        if not 0 <= condition <= PERCENT:
            raise ValidationFailedError(f"A district's condition runs from 0 to {PERCENT}.")
        district.condition = condition
    if material is not None:
        district.material = material
    await ctx.session.flush()
    return district


async def raze_district(ctx: TickContext, district_id: int) -> int:
    district = await ctx.session.get(DistrictRow, district_id)
    if district is None:
        raise NotFoundError("No such district.")
    settlement_id = district.settlement_entity_id
    await ctx.session.delete(district)
    await ctx.session.flush()
    return settlement_id


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
