import math

from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.society import KnowledgeBranch, NaturalLaw
from aerona.domain.enums.son import PowerEffect
from aerona.engine.context import TickContext
from aerona.engine.phase import Phase
from aerona.engine.primitives.capacity import GROWING_TYPES, LAND_COMMUNITY_TYPES, CapacityModel, RegionLoad
from aerona.engine.primitives.faith import faith_dominance, faith_shares, has_unlocked_power, living_patron
from aerona.engine.primitives.knowledge import LawBook
from aerona.engine.primitives.ledger import LedgerKey, record
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import canon
from aerona.engine.primitives.stats import headcount_bounds, set_stats, stat


async def total_population(ctx: TickContext) -> int:
    return sum(stat(community, "population") or 0 for community in await canon(ctx.session, LAND_COMMUNITY_TYPES))


async def population_baseline(ctx: TickContext) -> None:
    record(ctx, LedgerKey.POPULATION_START, await total_population(ctx))


async def bounty_multiplier(ctx: TickContext, community: EntityRow) -> float:
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
    before = stat(cult, "followers") or 1
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


async def grow_community(ctx: TickContext, model: CapacityModel, laws: LawBook, community: EntityRow, *, load: RegionLoad, multiplier: float) -> int:
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
    rate_base = max(engine.growth_min_pct / PERCENT, engine.growth_base_pct / PERCENT + fertility / engine.growth_fertility_divisor + prosperity_term)
    rate_base *= multiplier if fertility >= transition.bounty_power_min_fertility else 1.0
    rate_base *= math.sqrt(model.physics.of(community.world_id).time)
    rate_base *= model.knowledge.ratio(rules, community.id, KnowledgeBranch.AGRICULTURE, engine.growth_agriculture_pct)
    if laws.has(NaturalLaw.IMMORTALITY, community.world_id):
        rate_base *= transition.immortality_law_growth_pct / PERCENT
    if laws.has(NaturalLaw.SHORT_LIFE, community.world_id):
        rate_base *= transition.short_life_law_growth_pct / PERCENT
    rate = rate_base * (1 - load.population / max(1.0, capacity))
    floor, cap = headcount_bounds(rules, community)
    before = stat(community, "population") or floor
    bounded = max(-engine.shrink_max_pct / PERCENT, min(engine.growth_max_pct / PERCENT, rate))
    after = clamp_int(before * (1 + bounded), floor, cap)
    set_stats(community, population=after)
    load.population += after - before
    return after - before


async def population_growth(ctx: TickContext) -> None:
    record(ctx, LedgerKey.POPULATION_BEFORE_GROWTH, await total_population(ctx))
    model = await CapacityModel.load(ctx.session, ctx.rules)
    laws = await ctx.laws()
    growing = await canon(ctx.session, GROWING_TYPES)
    loads = model.build_loads(growing)
    grown = 0
    to_cults = 0
    for community in growing:
        load = loads[model.region_key(community)]
        multiplier = await bounty_multiplier(ctx, community)
        if community.entity_type is EntityType.CULT:
            to_cults += await grow_cult(ctx, community, load, multiplier)
        else:
            grown += await grow_community(ctx, model, laws, community, load=load, multiplier=multiplier)
    record(ctx, LedgerKey.POPULATION_GROWTH, grown)
    record(ctx, LedgerKey.POPULATION_TO_CULTS, to_cults)


BASELINE_PHASES = (Phase("population_baseline", population_baseline),)
GROWTH_PHASES = (Phase("population_growth", population_growth),)
PHASES = BASELINE_PHASES + GROWTH_PHASES
