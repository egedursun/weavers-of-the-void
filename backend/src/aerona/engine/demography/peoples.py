from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.demography import PeopleBiologyRow, PeopleCultureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.demography import Aesthetic, InheritanceCustom, MarriageCustom, MartialStyle
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.environment import CoastKind, TemperatureBand, TerrainKind
from aerona.domain.enums.mind import SkillKind, ValueAxis
from aerona.domain.enums.society import KnowledgeBranch
from aerona.engine.body.customs import culture_of
from aerona.engine.lore.language import script_factor
from aerona.engine.lore.research import has_technique
from aerona.engine.primitives.knowledge import known_levels
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import active_bonds
from aerona.rules.registry import Rules

HUMAN_LIFESPAN = 70
FERTILITY_FLOOR, FERTILITY_CEILING = 10, 300
LEAN = 25
STEPPE = frozenset({TerrainKind.STEPPE, TerrainKind.DESERT})
HIGHLAND = frozenset({TerrainKind.MOUNTAINS, TerrainKind.HILLS})


async def member_lifespan(session: AsyncSession, people: EntityRow) -> int:
    homes = [bond.target_node_id for bond in await active_bonds(session, [BondKind.LIVES_IN], sources=[people.id])]
    members = select(BondRow.source_node_id).where(
        BondRow.kind == BondKind.MEMBER_OF, BondRow.state == BondState.ACTIVE, BondRow.target_node_id.in_([people.id, *homes])
    )
    statement = select(func.avg(func.json_extract(EntityRow.stats, "$.lifespan"))).where(
        EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, EntityRow.id.in_(members)
    )
    found = await session.scalar(statement)
    return round_half_up(float(found)) if found else HUMAN_LIFESPAN


def staple_of(region: RegionEnvironmentRow | None) -> CommodityKind:
    if region is None:
        return CommodityKind.GRAIN
    if region.coast_kind is not CoastKind.NONE and region.farmed + region.grazed < LEAN:
        return CommodityKind.FISH
    return CommodityKind.LIVESTOCK if region.grazed > region.farmed else CommodityKind.GRAIN


def biology_for(rules: Rules, people: EntityRow, lifespan: int, region: RegionEnvironmentRow | None) -> PeopleBiologyRow:
    table = rules.peoples
    scale = max(0.2, lifespan / HUMAN_LIFESPAN)
    return PeopleBiologyRow(
        people_entity_id=people.id,
        maturity_years=max(1, round_half_up(table.maturity_years * scale)),
        adult_years=max(1, round_half_up(table.adult_years * scale)),
        elder_years=max(1, round_half_up(table.elder_years * scale)),
        fertility_pct=clamp_int(PERCENT / scale, FERTILITY_FLOOR, FERTILITY_CEILING),
        acclimatised=region.temperature_band if region is not None else TemperatureBand.TEMPERATE,
        traits=[],
        staple=staple_of(region),
        immunities=[],
        locked=[],
    )


def aesthetic_of(values: dict[ValueAxis, int]) -> Aesthetic:
    ranked = {
        Aesthetic.CELESTIAL: values.get(ValueAxis.PIETY, 0),
        Aesthetic.AUSTERE: values.get(ValueAxis.MARTIAL, 0) - values.get(ValueAxis.WEALTH, 0),
        Aesthetic.ORNATE: values.get(ValueAxis.WEALTH, 0),
        Aesthetic.NATURAL: values.get(ValueAxis.NATURE, 0),
        Aesthetic.MACABRE: values.get(ValueAxis.DEATH, 0),
        Aesthetic.GEOMETRIC: values.get(ValueAxis.KNOWLEDGE, 0),
    }
    return max(ranked, key=lambda kind: (ranked[kind], kind.value))


def martial_of(region: RegionEnvironmentRow | None, levels: dict[KnowledgeBranch, int], values: dict[ValueAxis, int]) -> MartialStyle:
    coastal = region is not None and region.coast_kind is not CoastKind.NONE
    terrain = region.dominant_terrain if region is not None else None
    ladder = (
        (levels.get(KnowledgeBranch.MAGIC, 0) >= 3, MartialStyle.WAR_MAGIC),
        (coastal and levels.get(KnowledgeBranch.SEAFARING, 0) >= 1, MartialStyle.NAVAL_RAIDER),
        (terrain in STEPPE, MartialStyle.HORSE_ARCHER),
        (levels.get(KnowledgeBranch.WARFARE, 0) >= 3 and levels.get(KnowledgeBranch.ARCHITECTURE, 0) >= 3, MartialStyle.SIEGE_ENGINEER),
        (levels.get(KnowledgeBranch.WARFARE, 0) >= 3, MartialStyle.PHALANX),
        (terrain in HIGHLAND, MartialStyle.SKIRMISHER),
        (values.get(ValueAxis.MARTIAL, 0) >= LEAN * 2 and values.get(ValueAxis.HONOUR, 0) < 0, MartialStyle.BERSERKER),
        (values.get(ValueAxis.NATURE, 0) >= LEAN * 2, MartialStyle.BEAST_WAR),
        (levels.get(KnowledgeBranch.METALLURGY, 0) >= 2 and terrain not in HIGHLAND and values.get(ValueAxis.HIERARCHY, 0) >= LEAN, MartialStyle.CHARIOT),
    )
    return next((style for matched, style in ladder if matched), MartialStyle.SHIELDWALL)


def customs_of(values: dict[ValueAxis, int]) -> tuple[MarriageCustom, bool, InheritanceCustom, bool]:
    hierarchy = values.get(ValueAxis.HIERARCHY, 0)
    tradition = values.get(ValueAxis.TRADITION, 0)
    kinship = values.get(ValueAxis.KINSHIP, 0)
    marriage = MarriageCustom.POLYGYNY if hierarchy >= LEAN * 2 and tradition >= LEAN else MarriageCustom.MONOGAMY
    if kinship <= -LEAN * 2:
        marriage = MarriageCustom.GROUP
    inheritance = (
        InheritanceCustom.PRIMOGENITURE
        if hierarchy >= LEAN
        else InheritanceCustom.BY_MERIT
        if values.get(ValueAxis.KNOWLEDGE, 0) >= LEAN
        else InheritanceCustom.ELECTIVE
        if hierarchy <= -LEAN
        else InheritanceCustom.GAVELKIND
    )
    slavery = hierarchy >= LEAN and values.get(ValueAxis.MERCY, 0) <= -LEAN
    return marriage, kinship >= LEAN, inheritance, slavery


async def culture_for(session: AsyncSession, rules: Rules, people: EntityRow, region: RegionEnvironmentRow | None) -> PeopleCultureRow:
    table = rules.peoples
    values = await culture_of(session, people.id)
    tongues = len(await active_bonds(session, [BondKind.SPEAKS], sources=[people.id]))
    levels = (await known_levels(session, [people.id])).get(people.id, {})
    homes = len(await active_bonds(session, [BondKind.LIVES_IN], sources=[people.id]))
    marriage, endogamous, inheritance, slavery = customs_of(values)
    script = await script_factor(session, rules, people.id)
    if await has_technique(session, people.id, Technique.ALPHABET):
        script = max(script, rules.script.alphabet_pct / PERCENT)
    return PeopleCultureRow(
        people_entity_id=people.id,
        cohesion=clamp_int(table.cohesion_base - max(0, tongues - 1) * table.cohesion_per_tongue + values.get(ValueAxis.KINSHIP, 0) // 4, 0, PERCENT),
        literacy=clamp_int(round_half_up(levels.get(KnowledgeBranch.WRITING, 0) * table.literacy_per_writing_level * script), 0, PERCENT),
        urbanisation=clamp_int(homes * table.urban_per_settlement, 0, PERCENT),
        staples=[staple_of(region).value],
        aesthetic=aesthetic_of(values),
        martial_style=martial_of(region, levels, values),
        marriage=marriage,
        endogamous=endogamous,
        inheritance=inheritance,
        slavery_lawful=slavery,
        locked=[],
    )


async def ensure_profiles(
    session: AsyncSession, rules: Rules, people: EntityRow, region: RegionEnvironmentRow | None
) -> tuple[PeopleBiologyRow, PeopleCultureRow]:
    biology = await session.get(PeopleBiologyRow, people.id)
    if biology is None:
        biology = biology_for(rules, people, await member_lifespan(session, people), region)
        session.add(biology)
    culture = await session.get(PeopleCultureRow, people.id)
    if culture is None:
        culture = await culture_for(session, rules, people, region)
        session.add(culture)
    await session.flush()
    return biology, culture


def refresh_culture(row: PeopleCultureRow, fresh: PeopleCultureRow) -> None:
    if "cohesion" not in row.locked:
        row.cohesion = clamp_int(row.cohesion + (fresh.cohesion - row.cohesion) / 4, 0, PERCENT)
    for key in ("literacy", "urbanisation", "staples", "aesthetic", "martial_style", "marriage", "endogamous", "inheritance", "slavery_lawful"):
        if key not in row.locked:
            setattr(row, key, getattr(fresh, key))


SKILL_FOR_STYLE: dict[MartialStyle, SkillKind] = {
    MartialStyle.SHIELDWALL: SkillKind.SHIELD,
    MartialStyle.HORSE_ARCHER: SkillKind.RIDING,
    MartialStyle.SKIRMISHER: SkillKind.THROWING,
    MartialStyle.CHARIOT: SkillKind.RIDING,
    MartialStyle.PHALANX: SkillKind.SPEAR,
    MartialStyle.BERSERKER: SkillKind.AXE,
    MartialStyle.NAVAL_RAIDER: SkillKind.NAVAL_COMBAT,
    MartialStyle.SIEGE_ENGINEER: SkillKind.SIEGECRAFT,
    MartialStyle.WAR_MAGIC: SkillKind.SPELLCRAFT,
    MartialStyle.BEAST_WAR: SkillKind.BEAST_HANDLING,
}
