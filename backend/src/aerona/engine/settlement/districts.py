from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.urban import DENSITY_RULE, HOUSING_RULE
from aerona.constants.units import PERCENT
from aerona.db.tables.economy import WorkshopRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.settlement import DESIGN_PARAMETERS, DistrictDesignRow, DistrictRow
from aerona.domain.enums.chronicle import ChronicleKind, FeedCategory
from aerona.domain.enums.economy import WorkshopKind
from aerona.domain.enums.polity import OfficeKind
from aerona.domain.enums.settlement import BuildMaterial, DistrictHarm, DistrictKind
from aerona.engine.context import TickContext
from aerona.engine.notes import note
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.rules.registry import Rules

HALF = 2
MAX_LEVEL = 5
CONDITION_KEY = "condition"
LEVEL_KEY = "level"
MATERIAL_KEY = "material"
DISTRICT_LOCKS = (LEVEL_KEY, CONDITION_KEY, MATERIAL_KEY)
DISASTER_TARGETS: Mapping[DistrictHarm, frozenset[DistrictKind]] = MappingProxyType(
    {
        DistrictHarm.FLOOD: frozenset({DistrictKind.FARMLAND, DistrictKind.HARBOUR, DistrictKind.SLUMS, DistrictKind.MARKET, DistrictKind.NECROPOLIS}),
        DistrictHarm.EARTHQUAKE: frozenset(DistrictKind),
        DistrictHarm.STORM: frozenset({DistrictKind.HARBOUR, DistrictKind.SLUMS, DistrictKind.FARMLAND, DistrictKind.FOREIGN_QUARTER}),
        DistrictHarm.DROUGHT: frozenset({DistrictKind.FARMLAND}),
        DistrictHarm.SACK: frozenset(
            {
                DistrictKind.MARKET,
                DistrictKind.PALACE,
                DistrictKind.TEMPLE_QUARTER,
                DistrictKind.CRAFT_QUARTER,
                DistrictKind.FOREIGN_QUARTER,
                DistrictKind.HARBOUR,
                DistrictKind.SLUMS,
            }
        ),
    }
)
HARM_WORDS: Mapping[DistrictHarm, str] = MappingProxyType(
    {
        DistrictHarm.FLOOD: "The flood waters broke into",
        DistrictHarm.EARTHQUAKE: "The earthquake shook down",
        DistrictHarm.STORM: "The storm tore through",
        DistrictHarm.DROUGHT: "The drought withered",
        DistrictHarm.SACK: "The looters stripped",
    }
)
OFFICE_TIER_RULES: Mapping[OfficeKind, str] = MappingProxyType(
    {
        OfficeKind.CHANCELLOR: "chancellor_tier",
        OfficeKind.MARSHAL: "marshal_tier",
        OfficeKind.TREASURER: "treasurer_tier",
        OfficeKind.HIGH_JUDGE: "high_judge_tier",
        OfficeKind.SPYMASTER: "spymaster_tier",
        OfficeKind.HERALD: "herald_tier",
        OfficeKind.CHAPLAIN: "chaplain_tier",
        OfficeKind.GOVERNOR: "governor_tier",
        OfficeKind.COURT_SCHOLAR: "court_scholar_tier",
    }
)


@dataclass(frozen=True)
class AdminParts:
    base: int
    literacy: int
    scribes: int
    writing: int
    palace: int

    @property
    def total(self) -> int:
        return self.base + self.literacy + self.scribes + self.writing + self.palace


@dataclass
class DistrictEffects:
    housing: int = 0
    food_store: int = 0
    goods_store: int = 0
    harbour: int = 0
    order: int = 0
    sanitation: int = 0
    piety_floor: int = 0
    admin_pct: int = 0
    policing: int = 0
    investment_pct: int = 0
    tension_relief_pct: int = 0


def density_pct(rules: Rules, kind: DistrictKind) -> int:
    return int(getattr(rules.city_plan, DENSITY_RULE[kind]))


def base_parameters(rules: Rules, kind: DistrictKind) -> dict[str, int]:
    urban = rules.urban
    table = rules.districts
    found = dict.fromkeys(DESIGN_PARAMETERS, 0)
    found["housing"] = urban.housing_per_level * density_pct(rules, kind) // PERCENT
    if kind in (DistrictKind.FARMLAND, DistrictKind.MARKET):
        found["food_store"] = urban.granary_per_level
    if kind in (DistrictKind.MARKET, DistrictKind.CRAFT_QUARTER):
        found["goods_store"] = table.warehouse_per_level
    if kind is DistrictKind.HARBOUR:
        found["harbour"] = urban.harbour_per_level
    if kind is DistrictKind.PALACE:
        found["order"] = table.palace_order
        found["admin_pct"] = table.admin_palace_pct
    if kind is DistrictKind.NECROPOLIS:
        found["sanitation"] = table.necropolis_sanitation
        found["piety_floor"] = table.necropolis_piety_floor
    if kind is DistrictKind.SLUMS:
        found["sanitation"] = -rules.sanitation.slum_loss
    if kind is DistrictKind.TEMPLE_QUARTER:
        found["piety_floor"] = table.temple_quarter_piety_floor
    if kind is DistrictKind.CITADEL:
        found["policing"] = rules.crime.citadel_policing
    if kind is DistrictKind.FOREIGN_QUARTER:
        found["investment_pct"] = table.foreign_quarter_investment_pct
        found["tension_relief_pct"] = table.foreign_quarter_tension_pct
    return found


def parameters_of(rules: Rules, kind: DistrictKind, design: DistrictDesignRow | None) -> dict[str, int]:
    found = base_parameters(rules, kind)
    if design is None:
        return found
    for key in DESIGN_PARAMETERS:
        value = getattr(design, key)
        if value is not None:
            found[key] = value
    return found


def home_factor(rules: Rules, district: DistrictRow) -> float:
    key = HOUSING_RULE.get(district.housing)
    return 1.0 if key is None else int(getattr(rules.housing_evolution, key)) / PERCENT


def effects_of(rules: Rules, districts: Sequence[DistrictRow], designs: Mapping[int, DistrictDesignRow]) -> DistrictEffects:
    effects = DistrictEffects()
    for district in districts:
        design = designs.get(district.design_id) if district.design_id is not None else None
        for key, value in parameters_of(rules, district.kind, design).items():
            factor = home_factor(rules, district) if key == "housing" else 1.0
            setattr(effects, key, getattr(effects, key) + round(value * district.level * factor))
    return effects


async def designs_for(session: AsyncSession, districts: Sequence[DistrictRow]) -> dict[int, DistrictDesignRow]:
    ids = {district.design_id for district in districts if district.design_id is not None}
    if not ids:
        return {}
    return {row.id: row for row in await session.scalars(select(DistrictDesignRow).where(DistrictDesignRow.id.in_(ids)))}


def admin_parts(rules: Rules, *, literacy: int, scribe_share: float, writing: int, palace_pct: int) -> AdminParts:
    table = rules.taxation
    extra = rules.districts
    return AdminParts(
        base=table.admin_base_pct,
        literacy=round_half_up(literacy * table.admin_per_literacy_pct / PERCENT),
        scribes=round_half_up(scribe_share * extra.admin_per_scribe_pct / PERCENT),
        writing=writing * extra.admin_per_writing_pct,
        palace=palace_pct,
    )


def material_factor(rules: Rules, harm: DistrictHarm, material: BuildMaterial) -> float:
    table = rules.districts
    stone = material is BuildMaterial.STONE
    factors = {
        DistrictHarm.FLOOD: table.stone_flood_pct if stone else table.timber_flood_pct,
        DistrictHarm.EARTHQUAKE: table.stone_quake_pct if stone else table.timber_quake_pct,
        DistrictHarm.STORM: table.stone_storm_pct if stone else table.timber_storm_pct,
        DistrictHarm.DROUGHT: PERCENT,
        DistrictHarm.SACK: table.stone_sack_pct if stone else table.timber_sack_pct,
    }
    return factors[harm] / PERCENT


def harm_loss(rules: Rules, harm: DistrictHarm) -> int:
    table = rules.districts
    return {
        DistrictHarm.FLOOD: table.flood_loss,
        DistrictHarm.EARTHQUAKE: table.quake_loss,
        DistrictHarm.STORM: table.storm_loss,
        DistrictHarm.DROUGHT: table.drought_loss,
        DistrictHarm.SACK: table.sack_loss,
    }[harm]


def wound_district(district: DistrictRow, loss: int) -> bool:
    if CONDITION_KEY in (district.locked or []) or loss <= 0:
        return False
    district.condition = max(0, district.condition - loss)
    if district.condition > 0:
        return False
    if LEVEL_KEY in (district.locked or []):
        district.condition = PERCENT // HALF
        return False
    district.level -= 1
    district.condition = PERCENT // HALF
    return district.level <= 0


async def damage_districts(ctx: TickContext, settlement: EntityRow, harm: DistrictHarm, scale: float) -> int:
    rows = list(
        await ctx.session.scalars(
            select(DistrictRow)
            .where(DistrictRow.settlement_entity_id == settlement.id, DistrictRow.kind.in_(list(DISASTER_TARGETS[harm])))
            .order_by(DistrictRow.id)
        )
    )
    struck: list[str] = []
    base = harm_loss(ctx.rules, harm) * max(0.0, scale)
    for district in rows:
        loss = round_half_up(base * material_factor(ctx.rules, harm, district.material))
        if loss <= 0:
            continue
        struck.append(district.kind.value.replace("_", " "))
        if wound_district(district, loss):
            await ctx.session.delete(district)
    if not struck:
        return 0
    await ctx.session.flush()
    await note(
        ctx,
        f"{HARM_WORDS[harm]} the {', '.join(sorted(set(struck)))} of {settlement.name}.",
        key=f"settlement.district_{harm.value}",
        ids=[settlement.id],
        feed=FeedCategory.DISASTER,
        kind=ChronicleKind.WORLD,
    )
    ctx.count(f"districts_{harm.value}", len(struck))
    return len(struck)


def office_tier(rules: Rules, kind: OfficeKind) -> int:
    key = OFFICE_TIER_RULES.get(kind)
    return int(getattr(rules.districts, key)) if key is not None else 0


async def market_workshop(session: AsyncSession, community_id: int) -> WorkshopRow | None:
    return await session.scalar(select(WorkshopRow).where(WorkshopRow.community_entity_id == community_id, WorkshopRow.kind == WorkshopKind.MARKET))


async def unify_market(ctx: TickContext, settlement: EntityRow, districts: list[DistrictRow], material: BuildMaterial) -> DistrictRow | None:
    levels = sum(district.level for district in districts if district.kind is DistrictKind.MARKET)
    workshop = await market_workshop(ctx.session, settlement.id)
    added: DistrictRow | None = None
    if workshop is not None and levels <= 0:
        added = DistrictRow(
            settlement_entity_id=settlement.id,
            kind=DistrictKind.MARKET,
            level=clamp_int(workshop.level, 1, MAX_LEVEL),
            condition=PERCENT,
            material=material,
            built_epoch=workshop.built_epoch,
            built_by_entity_id=settlement.id,
            locked=[],
        )
        ctx.session.add(added)
        districts.append(added)
        levels = added.level
    if levels <= 0:
        return None
    if workshop is None:
        ctx.session.add(WorkshopRow(community_entity_id=settlement.id, kind=WorkshopKind.MARKET, level=levels, built_epoch=ctx.epoch))
    elif workshop.level < levels:
        workshop.level = levels
    return added


async def close_market(session: AsyncSession, settlement_id: int) -> None:
    remaining = await session.scalar(
        select(DistrictRow.id).where(DistrictRow.settlement_entity_id == settlement_id, DistrictRow.kind == DistrictKind.MARKET).limit(1)
    )
    if remaining is not None:
        return
    workshop = await market_workshop(session, settlement_id)
    if workshop is not None:
        await session.delete(workshop)
