import math

from aerona.constants.units import PERCENT
from aerona.db.tables.demography import PeopleBiologyRow, PeopleCultureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.write_guard import held
from aerona.domain.enums.divine import DomainHook
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.society import KnowledgeBranch, NaturalLaw
from aerona.domain.enums.son import PowerEffect
from aerona.engine.body.customs import people_of
from aerona.engine.collective.demography import fertility_factor
from aerona.engine.context import TickContext
from aerona.engine.cosmos.lifeforms import disease_load, habitability, habitable_growth
from aerona.engine.cycles.book import strain_of
from aerona.engine.demography.basket import fed_index
from aerona.engine.demography.biology import footprint, hunger_level
from aerona.engine.demography.cohorts import cohorts_of, reconcile
from aerona.engine.demography.urban import growth_factor
from aerona.engine.demography.vital import Pressures, demographic_step, stress_of
from aerona.engine.disease.load import DiseaseLoads
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.interconnect.guards import absorb_flow
from aerona.engine.phase import Phase
from aerona.engine.primitives.capacity import GROWING_TYPES, LAND_COMMUNITY_TYPES, CapacityModel, RegionLoad
from aerona.engine.primitives.faith import faith_dominance, faith_shares, has_unlocked_power, living_patron
from aerona.engine.primitives.knowledge import LawBook
from aerona.engine.primitives.ledger import LedgerKey, record
from aerona.engine.primitives.modifiers import GROWTH_KEY, LIVE_MODIFIERS, virtual_value
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import canon
from aerona.engine.primitives.stats import headcount_bounds, set_stats, stat, stat_or


async def total_population(ctx: TickContext) -> int:
    return sum(stat(community, "population") or 0 for community in await canon(ctx.session, LAND_COMMUNITY_TYPES))


@reads("people.population", "settlement.population")
@writes("table.epoch_stats")
async def population_baseline(ctx: TickContext) -> None:
    record(ctx, LedgerKey.POPULATION_START, await total_population(ctx))


async def bounty_multiplier(ctx: TickContext, community: EntityRow) -> float:
    if LIVE_MODIFIERS.get() is not None:
        return virtual_value(community.id, GROWTH_KEY)
    patron = await living_patron(ctx.session, community)
    if patron is not None and await has_unlocked_power(ctx.session, ctx.rules, patron, PowerEffect.BOUNTY_GIVER):
        return float(ctx.rules.world_epoch_transition.bounty_power_growth_mult)
    return 1.0


async def grow_cult(ctx: TickContext, cult: EntityRow, load: RegionLoad, multiplier: float) -> int:
    rules = ctx.rules
    transition = rules.world_epoch_transition
    engine = rules.world_engine
    patron = await living_patron(ctx.session, cult)
    charisma = patron.charisma if patron is not None else transition.cult_default_charisma
    rate_base = (
        engine.cult_growth_base_pct / PERCENT
        + (stat(cult, "influence") or 0) / engine.cult_growth_influence_divisor
        + charisma / engine.cult_growth_charisma_divisor
    ) * multiplier
    ceiling = max(transition.cult_capacity_min, load.population * rules.deep_world.cult_population_share_pct / PERCENT)
    before = max(1, stat(cult, "followers") or 0)
    rate = rate_base * (1 - load.followers / ceiling)
    if rate > 0 and patron is not None:
        rate *= faith_dominance(rules, patron.id, await faith_shares(ctx.session))
    bounded = max(-transition.cult_shrink_max_pct / PERCENT, min(transition.cult_growth_max_pct / PERCENT, rate))
    after = clamp_int(before * (1 + bounded), 1, rules.limits.cult_follower_cap)
    set_stats(cult, followers=after)
    delta = after - before
    load.followers += delta
    converted = 0
    if delta > 0 and load.population > 0:
        for community in load.communities:
            population = stat(community, "population") or 0
            share = delta * population / load.population
            floor, _ = headcount_bounds(rules, community)
            updated = max(floor, round_half_up(population - share))
            converted += population - updated
            set_stats(community, population=updated)
    return converted


async def grow_community(
    ctx: TickContext, model: CapacityModel, laws: LawBook, community: EntityRow, *, load: RegionLoad, multiplier: float, diseases: DiseaseLoads
) -> int:
    rules = ctx.rules
    engine = rules.world_engine
    transition = rules.world_epoch_transition
    fertility = model.effective_fertility(community)
    capacity = model.capacity(load, community, fertility)
    prosperity_term = 0.0
    if community.entity_type is EntityType.SETTLEMENT:
        prosperity = stat(community, "prosperity")
        value = prosperity if prosperity is not None else rules.world_effects.unknown_prosperity
        prosperity_term = (value - transition.growth_prosperity_threshold) / engine.growth_prosperity_divisor
    vigour = max(engine.growth_min_pct / PERCENT, 1 + fertility / engine.growth_fertility_divisor + prosperity_term)
    vigour *= multiplier if fertility >= transition.bounty_power_min_fertility else 1.0
    vigour *= math.sqrt(model.physics.of(community.world_id).time)
    vigour *= model.knowledge.ratio(rules, community.id, KnowledgeBranch.AGRICULTURE, engine.growth_agriculture_pct)
    mortality = 1.0
    if laws.has(NaturalLaw.IMMORTALITY, community.world_id):
        vigour *= transition.immortality_law_growth_pct / PERCENT
        mortality *= rules.demography.immortality_death_pct / PERCENT
    if laws.has(NaturalLaw.SHORT_LIFE, community.world_id):
        vigour *= transition.short_life_law_growth_pct / PERCENT
        mortality *= rules.demography.short_life_death_pct / PERCENT
    people = await people_of(ctx.session, community)
    biology = await ctx.session.get(PeopleBiologyRow, people.id) if people is not None else None
    culture = await ctx.session.get(PeopleCultureRow, people.id) if people is not None else None
    if community.entity_type is EntityType.SETTLEMENT:
        vigour *= growth_factor(rules, culture)
    fit = await habitability(ctx.session, rules, biology, community.world_id)
    vigour *= habitable_growth(rules, fit)
    region_id = model.atlas.top_region(community.id)
    ground = await ctx.session.get(RegionEnvironmentRow, region_id) if region_id is not None else None
    magic = model.knowledge.level(community.id, KnowledgeBranch.MAGIC)
    vigour *= await ctx.hook_factor(community.id, DomainHook.FERTILITY)
    vigour *= await fertility_factor(ctx, community.id)
    misery = await strain_of(ctx.session, community.id) / PERCENT
    vigour *= max(0.0, 1 - misery * rules.structural_demography.misery_growth_cut / PERCENT)
    mortality *= 1 + misery * rules.structural_demography.misery_death_pct / PERCENT
    pressures = Pressures(
        fertility=vigour,
        hunger=hunger_level(rules, biology, ground, await fed_index(ctx.session, community.id), magic),
        crowding=max(0.0, load.population * footprint(rules, biology) / max(1.0, capacity)),
        disease=diseases.of(community) + disease_load(rules, fit),
        stress=await stress_of(ctx, community),
        mortality=mortality,
    )
    floor, cap = headcount_bounds(rules, community)
    before = stat_or(community, "population", floor)
    change = await demographic_step(ctx, community, biology, pressures)
    low = before * (1 - engine.shrink_max_pct / PERCENT)
    high = before * (1 + engine.growth_max_pct / PERCENT)
    after = clamp_int(max(low, min(high, before + change)), floor, cap)
    set_stats(community, population=after)
    absorb_flow(community.id, after - before)
    rows = await cohorts_of(ctx.session, community.id)
    await reconcile(ctx.session, rules, community, rows, ctx.epoch)
    load.population += after - before
    return after - before


@reads(
    "cult.followers",
    "cult.influence",
    "people.population",
    "place.fertility",
    "region.breadth",
    "region.fertility",
    "settlement.population",
    "settlement.prosperity",
    "table.bonds",
    "table.class_standing",
    "table.community_cohorts",
    "table.community_needs",
    "table.community_societies",
    "table.demographic_transitions",
    "table.divine_wounds",
    "table.endemic_diseases",
    "table.holder_levels",
    "table.law_jurisdictions",
    "table.natural_law_profiles",
    "table.nodes",
    "table.outbreaks",
    "table.people_biology",
    "table.people_culture",
    "table.people_reproduction",
    "table.place_environment",
    "table.polity_members",
    "table.polity_profiles",
    "table.polity_stress",
    "table.region_environment",
    "table.settlement_profiles",
    "table.sex_ratios",
    "table.son_powers",
    "table.war_sides",
    "table.wars",
    "table.world_biochemistries",
    "table.world_domain_hooks",
    "table.world_maps",
    "table.world_physics",
)
@writes("cult.followers", "people.population", "settlement.population", "table.community_cohorts", "table.entities")
async def population_growth(ctx: TickContext) -> None:
    record(ctx, LedgerKey.POPULATION_BEFORE_GROWTH, await total_population(ctx))
    model = await CapacityModel.load(ctx.session, ctx.rules)
    laws = await ctx.laws()
    growing = await canon(ctx.session, GROWING_TYPES)
    loads = model.build_loads(growing)
    diseases = await DiseaseLoads.load(ctx.session, ctx.rules)
    grown = 0
    to_cults = 0
    for community in growing:
        if held(community.id):
            continue
        load = loads[model.region_key(community)]
        multiplier = await bounty_multiplier(ctx, community)
        if community.entity_type is EntityType.CULT:
            to_cults += await grow_cult(ctx, community, load, multiplier)
        else:
            grown += await grow_community(ctx, model, laws, community, load=load, multiplier=multiplier, diseases=diseases)
    record(ctx, LedgerKey.POPULATION_GROWTH, grown)
    record(ctx, LedgerKey.POPULATION_TO_CULTS, to_cults)


BASELINE_PHASES = (Phase("population_baseline", population_baseline),)
GROWTH_PHASES = (Phase("population_growth", population_growth),)
PHASES = BASELINE_PHASES + GROWTH_PHASES
