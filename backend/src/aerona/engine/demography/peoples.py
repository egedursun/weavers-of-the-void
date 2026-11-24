from collections import Counter
from dataclasses import dataclass

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.body_plans import BUILD_RANK, HEIGHT_RANK
from aerona.catalog.goods_traits import commodities_with
from aerona.catalog.peoples import CREATURE_DIETS, CREATURE_NATURES, CREATURE_PLANS, PLAN_DIETS, PLAN_NATURES, STYLE_AXES, STYLE_NEUTRAL, VALUE_STYLE
from aerona.catalog.terrain import terrains
from aerona.catalog.units import UNITS
from aerona.constants.units import PERCENT
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.body import BodyRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.culture import LanguageStandingRow
from aerona.db.tables.cycles import KinshipSystemRow
from aerona.db.tables.demography import PeopleBiologyRow, PeopleCultureRow
from aerona.db.tables.disease import EndemicDiseaseRow
from aerona.db.tables.ecology import SpeciesProfileRow
from aerona.db.tables.entities import EntityRow, LanguageProfileRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.faith import CultDoctrineRow
from aerona.db.tables.unions import UnionCustomRow
from aerona.domain.enums.body import BodyPlan
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.demography import FuneralCustom, InheritanceCustom, MartialStyle, NaturalTrait
from aerona.domain.enums.ecology import Diet, SizeClass
from aerona.domain.enums.entity import SOCIETY_TYPES, EntityStatus, EntityType
from aerona.domain.enums.environment import CoastKind, TemperatureBand, TerrainTrait
from aerona.domain.enums.goods_traits import CommodityTrait
from aerona.domain.enums.military import UnitKind
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.society import CreatureTrait, KnowledgeBranch
from aerona.domain.enums.unions import PartnerScope, PluralSide, UnionForm
from aerona.engine.body.customs import culture_of
from aerona.engine.cosmos.lifeforms import HOMELAND_FIXUP, fit_to_homeland
from aerona.engine.demography.biology import edible, record_of, staple_for
from aerona.engine.demography.rites import set_rite
from aerona.engine.faith.book import patron_node
from aerona.engine.lore.language import script_factor, tongues_of
from aerona.engine.lore.motifs import canon_motifs
from aerona.engine.lore.research import has_technique
from aerona.engine.primitives.knowledge import known_levels
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import active_bonds, spoken_language
from aerona.engine.primitives.stats import stat_or
from aerona.engine.unions.axes import Spousing, drift_custom, fresh_custom
from aerona.rules.registry import Rules

HUMAN_LIFESPAN = 70
FERTILITY_FLOOR, FERTILITY_CEILING = 10, 300
LEAN = 25
STEPPE = terrains(TerrainTrait.ARID)
HIGHLAND = terrains(TerrainTrait.HIGH, without=(TerrainTrait.CONFINED,))
COVERED = (
    terrains(TerrainTrait.HIGH, without=(TerrainTrait.CONFINED,))
    | terrains(TerrainTrait.WOODED)
    | terrains(every=(TerrainTrait.AMBUSH_COVER, TerrainTrait.WET))
)
SKY_LANDS = terrains(TerrainTrait.COLD)
STAPLE_FOODS = frozenset(commodities_with(CommodityTrait.STAPLE))
SIZE_STEPS = ((0, SizeClass.SMALL), (2, SizeClass.MEDIUM), (3, SizeClass.LARGE), (5, SizeClass.HUGE), (8, SizeClass.COLOSSAL))


def size_by_rank(rank: int) -> SizeClass:
    return next((size for floor, size in reversed(SIZE_STEPS) if rank >= floor), SizeClass.SMALL)


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


async def species_root(session: AsyncSession, people: EntityRow) -> EntityRow | None:
    seen = {people.id}
    frontier = [people.id]
    while frontier:
        found = await active_bonds(session, [BondKind.DESCENDS_FROM], sources=frontier)
        frontier = []
        for bond in sorted(found, key=lambda item: item.id):
            if bond.target_node_id in seen:
                continue
            seen.add(bond.target_node_id)
            parent = await session.get(EntityRow, bond.target_node_id)
            if parent is None:
                continue
            if parent.entity_type is EntityType.SPECIES:
                return parent
            if parent.entity_type in {EntityType.PEOPLE, EntityType.SETTLEMENT}:
                frontier.append(parent.id)
    return None


@dataclass(frozen=True)
class Kin:
    plan: BodyPlan
    size: SizeClass
    diet: Diet
    traits: tuple[NaturalTrait, ...]


def kin_from(
    plan: BodyPlan | None, size: SizeClass | None, ecology_diet: Diet | None, creature: set[CreatureTrait], *, nocturnal: bool, height_rank: int | None
) -> Kin:
    chosen = plan or next((found for trait, found in CREATURE_PLANS if trait in creature), BodyPlan.HUMANOID)
    if size is None and chosen is BodyPlan.COLOSSAL:
        size = SizeClass.COLOSSAL
    if size is None:
        size = size_by_rank(height_rank) if height_rank is not None else SizeClass.MEDIUM
    diet = next((found for trait, found in CREATURE_DIETS if trait in creature), None) or PLAN_DIETS.get(chosen)
    if diet is None:
        diet = ecology_diet if ecology_diet is not None else Diet.OMNIVORE
    traits = {CREATURE_NATURES[trait] for trait in creature if trait in CREATURE_NATURES} | set(PLAN_NATURES.get(chosen, ()))
    if nocturnal:
        traits.add(NaturalTrait.DARK_SIGHT)
    return Kin(chosen, size, diet, tuple(sorted(traits, key=lambda item: item.value)))


async def kin_of(session: AsyncSession, people: EntityRow) -> Kin:
    repository = EntityRepository(session)
    creature = set(await repository.traits(people.id))
    species = await species_root(session, people)
    if species is None:
        return kin_from(None, None, None, creature, nocturnal=False, height_rank=None)
    creature |= set(await repository.traits(species.id))
    body = await session.get(BodyRow, species.id)
    profile = await session.get(SpeciesProfileRow, species.id)
    return kin_from(
        body.plan if body is not None else None,
        profile.size_class if profile is not None else None,
        profile.diet if profile is not None else None,
        creature,
        nocturnal=profile.nocturnal if profile is not None else False,
        height_rank=HEIGHT_RANK[body.height_class] + BUILD_RANK[body.build] if body is not None else None,
    )


async def homeland_diseases(session: AsyncSession, regions: list[int]) -> list[int]:
    if not regions:
        return []
    rows = await session.scalars(select(EndemicDiseaseRow.disease_entity_id).where(EndemicDiseaseRow.region_entity_id.in_(regions)))
    return sorted(set(rows))


def biology_for(
    rules: Rules, people: EntityRow, lifespan: int, region: RegionEnvironmentRow | None, *, kin: Kin | None = None, immunities: list[int] | None = None
) -> PeopleBiologyRow:
    table = rules.peoples
    scale = max(0.2, lifespan / HUMAN_LIFESPAN)
    found = kin or kin_from(None, None, None, set(), nocturnal=False, height_rank=None)
    return PeopleBiologyRow(
        people_entity_id=people.id,
        maturity_years=max(1, round_half_up(table.maturity_years * scale)),
        adult_years=max(1, round_half_up(table.adult_years * scale)),
        elder_years=max(1, round_half_up(table.elder_years * scale)),
        fertility_pct=clamp_int(PERCENT / scale, FERTILITY_FLOOR, FERTILITY_CEILING),
        acclimatised=region.temperature_band if region is not None else TemperatureBand.TEMPERATE,
        traits=[trait.value for trait in found.traits],
        staple=staple_for(rules, found.diet, region),
        immunities=list(immunities or []),
        body_plan=found.plan,
        size_class=found.size,
        diet=found.diet,
        locked=[],
    )


BIOLOGY_DRIFT = ("acclimatised", "traits", "immunities", "body_plan", "size_class", "diet")


def refresh_biology(rules: Rules, row: PeopleBiologyRow, fresh: PeopleBiologyRow, region: RegionEnvironmentRow | None) -> None:
    for key in BIOLOGY_DRIFT:
        if key not in row.locked:
            setattr(row, key, getattr(fresh, key))
    if "staple" not in row.locked:
        row.staple = staple_for(rules, row.diet, region)


def leading_value(values: dict[ValueAxis, int]) -> ValueAxis:
    ranked = {
        ValueAxis.PIETY: values.get(ValueAxis.PIETY, 0),
        ValueAxis.MARTIAL: values.get(ValueAxis.MARTIAL, 0) - values.get(ValueAxis.WEALTH, 0),
        ValueAxis.WEALTH: values.get(ValueAxis.WEALTH, 0),
        ValueAxis.NATURE: values.get(ValueAxis.NATURE, 0),
        ValueAxis.DEATH: values.get(ValueAxis.DEATH, 0),
        ValueAxis.KNOWLEDGE: values.get(ValueAxis.KNOWLEDGE, 0),
    }
    return max(ranked, key=lambda axis: (ranked[axis], axis.value))


def fields(levels: dict[KnowledgeBranch, int], kind: UnitKind) -> bool:
    spec = UNITS[kind]
    return spec.branch is None or levels.get(spec.branch, 0) >= spec.level


def martial_of(region: RegionEnvironmentRow | None, levels: dict[KnowledgeBranch, int], values: dict[ValueAxis, int]) -> MartialStyle:
    coastal = region is not None and region.coast_kind is not CoastKind.NONE
    terrain = region.dominant_terrain if region is not None else None
    ladder = (
        (fields(levels, UnitKind.DROP_TROOPS), MartialStyle.ORBITAL),
        (fields(levels, UnitKind.DRONE_OPERATORS), MartialStyle.DRONE_WAR),
        (fields(levels, UnitKind.MECHANISED_INFANTRY) and fields(levels, UnitKind.PILOTS), MartialStyle.COMBINED_ARMS),
        (fields(levels, UnitKind.PILOTS), MartialStyle.AIR_MOBILE),
        (fields(levels, UnitKind.MECHANISED_INFANTRY), MartialStyle.MECHANISED),
        (terrain in COVERED and fields(levels, UnitKind.SPECIAL_FORCES) and values.get(ValueAxis.HIERARCHY, 0) < 0, MartialStyle.GUERRILLA),
        (levels.get(KnowledgeBranch.MAGIC, 0) >= 3, MartialStyle.WAR_MAGIC),
        (coastal and levels.get(KnowledgeBranch.SEAFARING, 0) >= 1, MartialStyle.NAVAL_RAIDER),
        (terrain in STEPPE, MartialStyle.HORSE_ARCHER),
        (levels.get(KnowledgeBranch.WARFARE, 0) >= 3 and levels.get(KnowledgeBranch.ARCHITECTURE, 0) >= 3, MartialStyle.SIEGE_ENGINEER),
        (levels.get(KnowledgeBranch.WARFARE, 0) >= 3, MartialStyle.PHALANX),
        (terrain in HIGHLAND, MartialStyle.SKIRMISHER),
        (values.get(ValueAxis.MARTIAL, 0) >= LEAN * 2 and values.get(ValueAxis.HONOUR, 0) < 0, MartialStyle.SHOCK),
        (values.get(ValueAxis.NATURE, 0) >= LEAN * 2, MartialStyle.BEAST_WAR),
        (levels.get(KnowledgeBranch.METALLURGY, 0) >= 2 and terrain not in HIGHLAND and values.get(ValueAxis.HIERARCHY, 0) >= LEAN, MartialStyle.CHARIOT),
    )
    return next((style for matched, style in ladder if matched), MartialStyle.SHIELDWALL)


def spousing_for(values: dict[ValueAxis, int]) -> Spousing:
    hierarchy = values.get(ValueAxis.HIERARCHY, 0)
    tradition = values.get(ValueAxis.TRADITION, 0)
    kinship = values.get(ValueAxis.KINSHIP, 0)
    endogamy = PartnerScope.PEOPLE if kinship >= LEAN else PartnerScope.NONE
    if kinship <= -LEAN * 2:
        return Spousing(UnionForm.GROUP, PluralSide.EITHER, endogamy)
    if hierarchy <= -LEAN and kinship >= LEAN:
        return Spousing(UnionForm.PLURAL, PluralSide.SECOND, endogamy)
    if hierarchy >= LEAN * 2 and tradition >= LEAN:
        return Spousing(UnionForm.PLURAL, PluralSide.FIRST, endogamy)
    return Spousing(UnionForm.PAIR, PluralSide.EITHER, endogamy)


STYLE_LEANS: dict[str, ValueAxis] = {
    "ornament": ValueAxis.WEALTH,
    "geometry": ValueAxis.KNOWLEDGE,
    "scale": ValueAxis.HIERARCHY,
    "symmetry": ValueAxis.TRADITION,
}


def style_columns(values: dict[ValueAxis, int]) -> dict[str, int]:
    base = VALUE_STYLE.get(leading_value(values), STYLE_NEUTRAL)
    found = {axis: getattr(base, axis) for axis in STYLE_AXES}
    for axis, value_axis in STYLE_LEANS.items():
        found[axis] = clamp_int(found[axis] + values.get(value_axis, 0) // 4, 0, PERCENT)
    return found


def customs_of(values: dict[ValueAxis, int]) -> tuple[InheritanceCustom, bool]:
    hierarchy = values.get(ValueAxis.HIERARCHY, 0)
    kinship = values.get(ValueAxis.KINSHIP, 0)
    mercy = values.get(ValueAxis.MERCY, 0)
    second_plural = spousing_for(values).plural_on(PluralSide.SECOND)
    ladder = (
        (hierarchy >= LEAN and kinship >= LEAN and mercy >= LEAN, InheritanceCustom.ULTIMOGENITURE),
        (hierarchy >= LEAN, InheritanceCustom.PRIMOGENITURE),
        (kinship >= LEAN * 2 or second_plural, InheritanceCustom.THROUGH_SECOND_LINE),
        (kinship >= LEAN and values.get(ValueAxis.TRADITION, 0) >= LEAN, InheritanceCustom.SENIORITY),
        (values.get(ValueAxis.KNOWLEDGE, 0) >= LEAN, InheritanceCustom.BY_MERIT),
        (values.get(ValueAxis.LAW, 0) >= LEAN, InheritanceCustom.DESIGNATED),
        (values.get(ValueAxis.EQUALITY, 0) >= LEAN, InheritanceCustom.COMMUNAL),
        (hierarchy <= -LEAN, InheritanceCustom.ELECTIVE),
    )
    inheritance = next((custom for matched, custom in ladder if matched), InheritanceCustom.EQUAL_SHARES)
    slavery = hierarchy >= LEAN and mercy <= -LEAN
    return inheritance, slavery


def funeral_of(region: RegionEnvironmentRow | None, levels: dict[KnowledgeBranch, int], values: dict[ValueAxis, int]) -> FuneralCustom:
    terrain = region.dominant_terrain if region is not None else None
    coastal = region is not None and region.coast_kind is not CoastKind.NONE
    magic = levels.get(KnowledgeBranch.MAGIC, 0)
    death = values.get(ValueAxis.DEATH, 0)
    kinship = values.get(ValueAxis.KINSHIP, 0)
    ladder = (
        (magic >= 3 and death >= LEAN, FuneralCustom.REANIMATION),
        (magic >= 2 and values.get(ValueAxis.PIETY, 0) >= LEAN, FuneralCustom.SOUL_BINDING),
        (levels.get(KnowledgeBranch.MEDICINE, 0) >= 2 and death >= LEAN and region is not None and region.rainfall <= LEAN, FuneralCustom.MUMMIFICATION),
        (levels.get(KnowledgeBranch.ARCHITECTURE, 0) >= 2 and values.get(ValueAxis.HIERARCHY, 0) >= LEAN and death >= 0, FuneralCustom.ENTOMBMENT),
        (kinship >= LEAN * 2, FuneralCustom.ANCESTOR_SHRINE),
        (kinship >= LEAN and death >= 0 and values.get(ValueAxis.TRADITION, 0) >= LEAN, FuneralCustom.SECONDARY_BURIAL),
        (kinship >= LEAN and values.get(ValueAxis.MERCY, 0) <= -LEAN * 2, FuneralCustom.ENDOCANNIBALISM),
        (death <= -LEAN * 2, FuneralCustom.MEMORIAL_ONLY),
        (terrain in SKY_LANDS, FuneralCustom.SKY_BURIAL),
        (coastal and levels.get(KnowledgeBranch.SEAFARING, 0) >= 1, FuneralCustom.SEA_BURIAL),
        (values.get(ValueAxis.NATURE, 0) >= LEAN, FuneralCustom.RETURN_TO_SOIL),
        (values.get(ValueAxis.PIETY, 0) >= LEAN or (region is not None and region.forest_cover >= LEAN * 2), FuneralCustom.CREMATION),
    )
    return next((rite for matched, rite in ladder if matched), FuneralCustom.BURIAL)


async def faith_tongue(session: AsyncSession, people: EntityRow) -> int | None:
    god = await patron_node(session, people.id)
    if god is None:
        return None
    worshippers = select(BondRow.source_node_id).where(BondRow.target_node_id == god, BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE)
    cults = select(EntityRow.id).where(EntityRow.id.in_(worshippers), EntityRow.entity_type == EntityType.CULT)
    doctrine = await session.scalar(
        select(CultDoctrineRow.liturgical_language_id)
        .where(CultDoctrineRow.cult_entity_id.in_(cults), CultDoctrineRow.liturgical_language_id.is_not(None))
        .order_by(CultDoctrineRow.cult_entity_id)
        .limit(1)
    )
    if doctrine is not None:
        return int(doctrine)
    eldest = await session.scalar(
        select(EntityRow)
        .where(EntityRow.id.in_(worshippers), EntityRow.entity_type.in_(list(SOCIETY_TYPES)))
        .order_by(EntityRow.birth_epoch, EntityRow.id)
        .limit(1)
    )
    tongue = await spoken_language(session, eldest.id) if eldest is not None else None
    return tongue.id if tongue is not None else None


async def liturgical_of(session: AsyncSession, people: EntityRow) -> int | None:
    own = await spoken_language(session, people.id)
    base = await faith_tongue(session, people) or (own.id if own is not None else None)
    if base is None:
        return None
    profile = await session.get(LanguageProfileRow, base)
    if profile is not None and profile.parent_language_id is not None:
        parent = await session.get(EntityRow, profile.parent_language_id)
        if parent is not None and parent.status in {EntityStatus.CANON, EntityStatus.DEAD}:
            return parent.id
    return base


async def trade_language_of(session: AsyncSession, people: EntityRow) -> int | None:
    homes = [bond.target_node_id for bond in await active_bonds(session, [BondKind.LIVES_IN], sources=[people.id])]
    ours = {people.id, *homes}
    roads = await session.scalars(
        select(BondRow).where(
            BondRow.kind == BondKind.TRADES_WITH,
            BondRow.state == BondState.ACTIVE,
            or_(BondRow.source_node_id.in_(ours), BondRow.target_node_id.in_(ours)),
        )
    )
    tally: Counter[int] = Counter()
    for road in roads:
        partner = road.target_node_id if road.source_node_id in ours else road.source_node_id
        if partner in ours:
            continue
        for tongue in await tongues_of(session, partner):
            tally[tongue] += 1
    own = await spoken_language(session, people.id)
    own_id = own.id if own is not None else None
    if not tally:
        return own_id
    francas = set(await session.scalars(select(LanguageStandingRow.language_entity_id).where(LanguageStandingRow.lingua_franca.is_(True))))
    return max(tally, key=lambda tongue: (tongue in francas, tally[tongue], tongue == own_id, -tongue))


async def culture_for(session: AsyncSession, rules: Rules, people: EntityRow, region: RegionEnvironmentRow | None) -> PeopleCultureRow:
    table = rules.peoples
    values = await culture_of(session, people.id)
    tongues = len(await active_bonds(session, [BondKind.SPEAKS], sources=[people.id]))
    levels = (await known_levels(session, [people.id])).get(people.id, {})
    homes = [await session.get(EntityRow, bond.target_node_id) for bond in await active_bonds(session, [BondKind.LIVES_IN], sources=[people.id])]
    townsfolk = sum(stat_or(home, "population", 0) for home in homes if home is not None and home.status is EntityStatus.CANON)
    inheritance, slavery = customs_of(values)
    script = await script_factor(session, rules, people.id)
    if await has_technique(session, people.id, Technique.ALPHABET):
        script = max(script, rules.script.alphabet_pct / PERCENT)
    biology = await session.get(PeopleBiologyRow, people.id)
    diet = biology.diet if biology is not None else Diet.OMNIVORE
    return PeopleCultureRow(
        people_entity_id=people.id,
        cohesion=clamp_int(table.cohesion_base - max(0, tongues - 1) * table.cohesion_per_tongue + values.get(ValueAxis.KINSHIP, 0) // 4, 0, PERCENT),
        literacy=clamp_int(round_half_up(levels.get(KnowledgeBranch.WRITING, 0) * table.literacy_per_writing_level * script), 0, PERCENT),
        urbanisation=clamp_int(townsfolk * table.urban_per_settlement / max(1, stat_or(people, "population", 0)), 0, PERCENT),
        liturgical_language_id=await liturgical_of(session, people),
        trade_language_id=await trade_language_of(session, people),
        staples=sorted({staple_for(rules, diet, region).value, *(item.value for item in edible(diet) if item in STAPLE_FOODS)}),
        **style_columns(values),
        motif_sources=[source.value for source in await canon_motifs(session, people)],
        martial_style=martial_of(region, levels, values),
        funeral_rite=funeral_of(region, levels, values),
        inheritance=inheritance,
        slavery_lawful=slavery,
        martial_record={},
        martial_epoch=0,
        locked=[],
    )


async def ensure_profiles(
    session: AsyncSession, rules: Rules, people: EntityRow, region: RegionEnvironmentRow | None
) -> tuple[PeopleBiologyRow, PeopleCultureRow]:
    biology = await session.get(PeopleBiologyRow, people.id)
    if biology is None:
        diseases = await homeland_diseases(session, [region.entity_id] if region is not None else [])
        biology = biology_for(rules, people, await member_lifespan(session, people), region, kin=await kin_of(session, people), immunities=diseases)
        if await fit_to_homeland(session, rules, biology, people.world_id):
            session.add(AppliedFixupRow(key=f"{HOMELAND_FIXUP}.{people.id}", result={"world_id": people.world_id}))
        session.add(biology)
        await session.flush()
    culture = await session.get(PeopleCultureRow, people.id)
    if culture is None:
        culture = await culture_for(session, rules, people, region)
        session.add(culture)
    if await session.get(UnionCustomRow, people.id) is None:
        spousing = spousing_for(await culture_of(session, people.id))
        session.add(fresh_custom(people.id, spousing, await session.get(KinshipSystemRow, people.id), rules.kinship.union_payment))
    await session.flush()
    return biology, culture


async def drift_union(session: AsyncSession, people: EntityRow) -> None:
    row = await session.get(UnionCustomRow, people.id)
    if row is not None:
        drift_custom(row, spousing_for(await culture_of(session, people.id)))


CULTURE_DRIFT = (
    "literacy",
    "urbanisation",
    "liturgical_language_id",
    "trade_language_id",
    "staples",
    "ornament",
    "geometry",
    "colour",
    "scale",
    "symmetry",
    "motif_sources",
    "inheritance",
    "slavery_lawful",
)


def martial_choice(rules: Rules, row: PeopleCultureRow, derived: MartialStyle, victor: MartialStyle | None) -> MartialStyle:
    table = rules.customs
    wins, losses = record_of(row, row.martial_style.value)
    if wins - losses >= table.martial_hold_wins:
        return row.martial_style
    if losses - wins >= table.martial_defeat_losses and victor is not None and victor is not row.martial_style:
        return victor
    return derived


def refresh_culture(rules: Rules, row: PeopleCultureRow, fresh: PeopleCultureRow, victor: MartialStyle | None = None) -> None:
    if "cohesion" not in row.locked:
        row.cohesion = clamp_int(row.cohesion + (fresh.cohesion - row.cohesion) / 4, 0, PERCENT)
    for key in CULTURE_DRIFT:
        if key not in row.locked:
            setattr(row, key, getattr(fresh, key))
    if "martial_style" not in row.locked:
        row.martial_style = martial_choice(rules, row, fresh.martial_style, victor)
    if "funeral_rite" not in row.locked and "funeral_rite_id" not in row.locked:
        set_rite(row, fresh.funeral_rite)


def tally_battle(row: PeopleCultureRow, *, won: bool) -> None:
    record = {key: list(value) for key, value in (row.martial_record or {}).items()}
    wins, losses = record_of(row, row.martial_style.value)
    record[row.martial_style.value] = [wins + (1 if won else 0), losses + (0 if won else 1)]
    row.martial_record = record
