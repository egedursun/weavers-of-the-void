from dataclasses import dataclass, replace

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.materials import BUILD_MATERIALS, MATERIALS
from aerona.catalog.methods import METHODS, MethodSpec
from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.kind_concepts.nature import FUNCTION_DANGER, FUNCTION_STEPS, LEGACY_TRAITS, OFFICE_DUTY, REALM_FUNCTION, TRAIT_STATS
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.demography import PeopleBiologyRow
from aerona.db.tables.economy import WorldMaterialRow
from aerona.db.tables.entities import EntityRow, EntityTraitRow
from aerona.db.tables.kinds import KindHoldingRow
from aerona.db.tables.mythic import CosmicOfficeRow
from aerona.db.tables.nature_kinds import DivineOfficeKindRow, ProductionMethodKindRow, RealmKindRow, TraitKindRow
from aerona.db.tables.polity import HouseProfileRow
from aerona.db.tables.settlement import DistrictRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.kinds import KindConcept, KindStance
from aerona.domain.enums.mythic import MythicRealm
from aerona.domain.enums.nature_kinds import OfficeDuty, RealmFunction
from aerona.domain.enums.settlement import BuildMaterial
from aerona.engine.context import TickContext
from aerona.engine.kinds.legacy import give
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import shift_stat, stat
from aerona.rules.registry import Rules

STAT_COLUMN = {EntityType.SPECIES: 0, EntityType.PEOPLE: 1, EntityType.HOUSE: 2}


@dataclass
class TraitTally:
    shifted: int = 0


async def ensure_built_ins(session: AsyncSession) -> int:
    added = 0
    if not await session.scalar(select(func.count()).select_from(ProductionMethodKindRow).where(ProductionMethodKindRow.built_in.is_(True))):
        for kind, spec in METHODS.items():
            session.add(
                ProductionMethodKindRow(
                    name=spec.label,
                    description=spec.summary,
                    built_in=True,
                    built_in_key=kind.value,
                    category=spec.process,
                    base=kind,
                    output_pct=spec.output_pct,
                    quality_bonus=spec.quality_bonus,
                    labour_pct=spec.labour_pct,
                    energy_need=spec.energy_need,
                    tool_wear=spec.tool_wear,
                    locked=[],
                )
            )
            added += 1
    if not await session.scalar(select(func.count()).select_from(DivineOfficeKindRow).where(DivineOfficeKindRow.built_in.is_(True))):
        for office, duty in OFFICE_DUTY.items():
            session.add(DivineOfficeKindRow(name=spoken(duty).capitalize(), built_in=True, built_in_key=office.value, category=duty, locked=[]))
            added += 1
    if not await session.scalar(select(func.count()).select_from(RealmKindRow).where(RealmKindRow.built_in.is_(True))):
        for realm, function in REALM_FUNCTION.items():
            session.add(
                RealmKindRow(
                    name=spoken(function).capitalize(),
                    built_in=True,
                    built_in_key=realm.value,
                    category=function,
                    steps=FUNCTION_STEPS[function],
                    danger=FUNCTION_DANGER[function],
                    locked=[],
                )
            )
            added += 1
    if not await session.scalar(select(func.count()).select_from(TraitKindRow).where(TraitKindRow.built_in.is_(True))):
        for key, name, capacity, strength in LEGACY_TRAITS:
            session.add(TraitKindRow(name=name, built_in=True, built_in_key=key, category=capacity, strength=strength, locked=[]))
            added += 1
    await session.flush()
    return added


async def chosen_method(session: AsyncSession, kind_id: int | None, spec: MethodSpec) -> MethodSpec:
    kind = await session.get(ProductionMethodKindRow, kind_id) if kind_id is not None else None
    if kind is None or kind.retired:
        return spec
    base = METHODS[kind.base] if kind.base is not None else spec
    return replace(
        base,
        output_pct=kind.output_pct,
        quality_bonus=kind.quality_bonus,
        labour_pct=kind.labour_pct,
        energy_need=kind.energy_need,
        tool_wear=kind.tool_wear,
        label=kind.name,
    )


async def office_duty(session: AsyncSession, row: CosmicOfficeRow) -> tuple[OfficeDuty, int]:
    kind = await session.get(DivineOfficeKindRow, row.office_kind_id) if row.office_kind_id is not None else None
    if kind is None or kind.retired:
        return OFFICE_DUTY[row.office], PERCENT
    return kind.category, kind.income_pct


async def realm_kind_for(ctx: TickContext, realm: MythicRealm, world_id: int | None) -> int | None:
    query = (
        select(RealmKindRow.id)
        .where(RealmKindRow.category == REALM_FUNCTION[realm], RealmKindRow.retired.is_(False))
        .where((RealmKindRow.world_id == world_id) | RealmKindRow.world_id.is_(None))
        .order_by(RealmKindRow.built_in, RealmKindRow.id)
        .limit(1)
    )
    return await ctx.session.scalar(query)


async def realm_kind_of(session: AsyncSession, kind_id: int | None, realm: MythicRealm) -> tuple[RealmFunction, int, str | None]:
    kind = await session.get(RealmKindRow, kind_id) if kind_id is not None else None
    if kind is None or kind.retired:
        legacy = REALM_FUNCTION[realm]
        return legacy, FUNCTION_STEPS[legacy], None
    return kind.category, kind.steps, kind.name


def pulled(current: int, strength: int, rules: Rules) -> int:
    target = PERCENT // 2 + strength * rules.typed_traits.pull // PERCENT
    return clamp_int(current + round_half_up((target - current) * rules.typed_traits.drift_pct / PERCENT), 0, PERCENT)


async def keep_traits(ctx: TickContext) -> TraitTally:
    tally = TraitTally()
    holdings = list(
        await ctx.session.scalars(
            select(KindHoldingRow).where(KindHoldingRow.concept == KindConcept.TRAIT, KindHoldingRow.stance != KindStance.FORBIDS).order_by(KindHoldingRow.id)
        )
    )
    for holding in holdings:
        holder = await ctx.session.get(EntityRow, holding.holder_node_id)
        kind = await ctx.session.get(TraitKindRow, holding.kind_id)
        if holder is None or kind is None or kind.retired or holder.status is not EntityStatus.CANON or held(holder.id):
            continue
        column = STAT_COLUMN.get(holder.entity_type)
        key = TRAIT_STATS[kind.category][column] if column is not None else None
        current = stat(holder, key) if key is not None else None
        if key is None or current is None:
            continue
        strength = kind.strength * holding.strength // PERCENT
        shift_stat(holder, key, pulled(current, strength, ctx.rules) - current, high=PERCENT)
        tally.shifted += 1
    await ctx.session.flush()
    return tally


@dataclass(frozen=True)
class Build:
    fireproof: float
    strength: float


def build_of(rules: Rules, material: BuildMaterial, world_material: WorldMaterialRow | None) -> Build:
    if world_material is not None:
        ignition, blows = world_material.ignition_point, (world_material.impact_fracture + world_material.shear_fracture) // 2
    else:
        props = MATERIALS[BUILD_MATERIALS[material]]
        ignition, blows = props.ignition_point, (props.impact_fracture + props.shear_fracture) // 2
    return Build(
        fireproof=min(1.0, ignition / PERCENT * rules.building.fire_pct / PERCENT),
        strength=min(2.0, blows / PERCENT * rules.building.strength_pct / PERCENT),
    )


async def material_of(session: AsyncSession, world_material_id: int | None) -> WorldMaterialRow | None:
    return await session.get(WorldMaterialRow, world_material_id) if world_material_id is not None else None


async def sturdiness(session: AsyncSession, rules: Rules, material: BuildMaterial, world_material_id: int | None) -> float:
    world_material = await material_of(session, world_material_id)
    if world_material is None:
        return 1.0
    plain = build_of(rules, material, None).strength
    return build_of(rules, material, world_material).strength / plain if plain > 0 else 1.0


async def burn_factors(session: AsyncSession, rules: Rules, districts: list[DistrictRow]) -> dict[int, float]:
    found: dict[int, float] = {}
    for district in districts:
        world_material = await material_of(session, district.world_material_id)
        if world_material is not None:
            found[district.id] = max(0.0, 1 - build_of(rules, district.material, world_material).fireproof)
    return found


TRAIT_FIXUP = "kinds.legacy_traits"


async def legacy_traits(ctx: TickContext) -> int:
    if await ctx.session.get(AppliedFixupRow, TRAIT_FIXUP) is not None:
        return 0
    built = {row.built_in_key: row.id for row in await ctx.session.scalars(select(TraitKindRow).where(TraitKindRow.built_in.is_(True)))}
    pairs: list[tuple[int, str]] = []
    for entity_id, trait in await ctx.session.execute(select(EntityTraitRow.entity_id, EntityTraitRow.trait)):
        pairs.append((entity_id, f"creature.{trait.value}"))
    for house in await ctx.session.scalars(select(HouseProfileRow)):
        pairs.extend((house.house_entity_id, f"house.{trait}") for trait in house.traits or [])
    for biology in await ctx.session.scalars(select(PeopleBiologyRow)):
        pairs.extend((biology.people_entity_id, f"natural.{trait}") for trait in biology.traits or [])
    given = 0
    for holder_id, key in pairs:
        kind_id = built.get(key)
        if kind_id is not None and await give(ctx, KindConcept.TRAIT, kind_id, holder_id, PERCENT):
            given += 1
    ctx.session.add(AppliedFixupRow(key=TRAIT_FIXUP, result={"traits": given}))
    await ctx.session.flush()
    return given
