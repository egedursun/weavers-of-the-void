from collections.abc import Mapping
from dataclasses import dataclass, field, replace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.commodities import COMMODITIES
from aerona.catalog.society import SOCIAL_CLASSES
from aerona.constants.units import PERCENT, TENTHS
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.society_depth import CorveeRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind, FeedCategory
from aerona.domain.enums.economy import CommodityKind, GoodsFlow, MaterialSlot
from aerona.domain.enums.entity import SOCIETY_TYPES, EngineKind, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.society import Commodity, KnowledgeBranch, NaturalLaw, SocialClass
from aerona.domain.enums.war import WarCause
from aerona.domain.enums.world import WorldType
from aerona.domain.models.entity_stats import FactionStats, ItemStats
from aerona.engine.body.cohorts import labour_factor
from aerona.engine.context import TickContext
from aerona.engine.cosmos.world_types import ore_yield_pct
from aerona.engine.demography.backfill import society_depth_backfill
from aerona.engine.demography.basket import (
    Basket,
    ClassNeed,
    apply_shortfalls,
    build_basket,
    class_need_penalty,
    held_needs,
    needs_of,
    save_basket,
    serve_order,
    standing_of,
    staples_of,
)
from aerona.engine.demography.prices import local_prices
from aerona.engine.demography.wealth import settle_wealth
from aerona.engine.economy.book import EconomyBook
from aerona.engine.economy.household import Meal, eat, enforce_storage, gather_commons, harvest_goods, wear
from aerona.engine.economy.materials import MaterialBook, armour_protection, curse_bonus, enchantment_cap, set_node_material, weapon_damage
from aerona.engine.economy.stocks import aggregate_need, goods_of, holding, lots_of, sync_aggregates
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.lore.items import craft
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.phases.society_support.community import CommunityBook
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.faith import FaithIndex
from aerona.engine.primitives.knowledge import ratio_of
from aerona.engine.primitives.numbers import clamp_float, clamp_int, fraction, round_half_up
from aerona.engine.primitives.prosperity import add_prosperity
from aerona.engine.primitives.queries import canon
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.society import default_class_shares
from aerona.engine.primitives.stats import headcount, set_stats, shift_stat, stat, stat_or
from aerona.engine.services.war import declare_war, uprising_target
from aerona.engine.settlement.storage import community_capacity, storage_index
from aerona.rules.registry import Rules
from aerona.rules.registry.knowledge import KnowledgeRules
from aerona.rules.registry.society import SocietyRules

WEAPON_SUBTYPE = "weapon"


@dataclass
class Society:
    shares: dict[SocialClass, float]
    satisfaction: dict[SocialClass, int]
    stocks: dict[Commodity, int]
    prices: dict[Commodity, int]


@dataclass(frozen=True)
class SocietyView:
    entity_id: int
    society: Society
    stored: bool
    unhappiest: SocialClass | None
    bankruptcy_risk: bool
    uprising_risk: bool


@dataclass(frozen=True)
class EconomyWorld:
    book: CommunityBook
    entities: Mapping[int, EntityRow]
    atlas: RegionAtlas
    faith: FaithIndex
    harvests: Mapping[int, int] = field(default_factory=dict)
    world_types: Mapping[int, WorldType] = field(default_factory=dict)
    ledger: EconomyBook | None = None

    @property
    def economy(self) -> EconomyBook:
        assert self.ledger is not None
        return self.ledger

    @classmethod
    async def load(cls, session: AsyncSession) -> "EconomyWorld":
        entities = {entity.id: entity for entity in await canon(session)}
        harvests = {region_id: value for region_id, value in await session.execute(select(RegionEnvironmentRow.entity_id, RegionEnvironmentRow.harvest_pct))}
        world_types = {world_id: world_type for world_id, world_type in await session.execute(select(WorldRow.id, WorldRow.world_type))}
        return cls(await CommunityBook.load(session), entities, await RegionAtlas.load(session), await FaithIndex.load(session), harvests, world_types)

    def ore_yield(self, rules: Rules, world_id: int | None) -> float:
        world_type = self.world_types.get(world_id) if world_id is not None else None
        return fraction(ore_yield_pct(rules, world_type)) if world_type is not None else 1.0


@dataclass
class EconomyCounters:
    famines: int = 0
    uprisings: int = 0
    bankruptcies: int = 0
    weapons: int = 0
    touched: set[int] = field(default_factory=set)


@dataclass(frozen=True)
class EconomyInputs:
    harvest_pct: int
    at_war: bool
    routes: int
    pays_tribute: bool
    has_god: bool
    godless: bool
    cursed: bool
    bounty_law: bool
    justice: float | None
    fertility: int
    branches: frozenset[KnowledgeBranch]
    piety: int
    prosperity: int
    skilled_crafts: bool
    levels: Mapping[KnowledgeBranch, int] = field(default_factory=dict)


def round_tenth(value: float) -> float:
    return round_half_up(value * TENTHS) / TENTHS


def normalized_shares(shares: Mapping[SocialClass, float]) -> dict[SocialClass, float]:
    clean = {social_class: max(0.0, float(shares.get(social_class, 0.0))) for social_class in SocialClass}
    total = sum(clean.values())
    if total <= 0:
        return {social_class: round_tenth(PERCENT / len(SocialClass)) for social_class in SocialClass}
    return {social_class: clamp_float(round_tenth(value * PERCENT / total), 0.0, float(PERCENT)) for social_class, value in clean.items()}


def default_society(rules: Rules) -> Society:
    settings = rules.society
    return Society(
        shares=normalized_shares(default_class_shares(rules)),
        satisfaction=dict.fromkeys(SocialClass, settings.class_initial_satisfaction),
        stocks={Commodity.FOOD: settings.initial_food, Commodity.ORE: settings.initial_ore, Commodity.GOODS: settings.initial_goods},
        prices=dict.fromkeys(Commodity, PERCENT),
    )


def society_from_row(row: CommunitySocietyRow) -> Society:
    return Society(
        shares={social_class: row.share(social_class) for social_class in SocialClass},
        satisfaction={social_class: row.satisfaction(social_class) for social_class in SocialClass},
        stocks={commodity: row.stock(commodity) for commodity in Commodity},
        prices={commodity: row.price(commodity) for commodity in Commodity},
    )


async def society_of(session: AsyncSession, rules: Rules, entity_id: int) -> Society:
    row = await session.get(CommunitySocietyRow, entity_id)
    return society_from_row(row) if row is not None else default_society(rules)


async def save_society(session: AsyncSession, entity_id: int, society: Society, *, stocks: bool = True) -> CommunitySocietyRow:
    row = await session.get(CommunitySocietyRow, entity_id)
    if row is None:
        row = CommunitySocietyRow(entity_id=entity_id)
        session.add(row)
        stocks = True
    for social_class in SocialClass:
        setattr(row, f"share_{social_class.value}", clamp_float(society.shares[social_class], 0.0, float(PERCENT)))
        setattr(row, f"satisfaction_{social_class.value}", clamp_int(society.satisfaction[social_class], 0, PERCENT))
    for commodity in Commodity:
        if stocks:
            setattr(row, f"stock_{commodity.value}", max(0, round_half_up(society.stocks[commodity])))
        setattr(row, f"price_{commodity.value}", max(0, round_half_up(society.prices[commodity])))
    await session.flush()
    return row


async def seed_stocks(ctx: TickContext, entity: EntityRow) -> None:
    if await lots_of(ctx.session, entity.id):
        return
    row = await ctx.session.get(CommunitySocietyRow, entity.id)
    if row is None:
        return
    for aggregate in Commodity:
        await goods_of(ctx.session, ctx.epoch).shift_aggregate(ctx.rules, entity, aggregate, row.stock(aggregate), flow=GoodsFlow.SEED)


def class_targets(rules: Rules, inputs: EconomyInputs) -> dict[SocialClass, float]:
    settings = rules.society
    target = dict(default_class_shares(rules))
    if KnowledgeBranch.AGRICULTURE in inputs.branches:
        target[SocialClass.FARMER] += settings.target_agriculture_farmer
    if KnowledgeBranch.TRADE in inputs.branches or inputs.routes > 0:
        target[SocialClass.MERCHANT] += settings.target_trade_merchant + min(settings.target_route_merchant_cap, inputs.routes * settings.target_route_merchant)
    if KnowledgeBranch.WRITING in inputs.branches:
        target[SocialClass.SCRIBE] += settings.target_writing_scribe
    if KnowledgeBranch.METALLURGY in inputs.branches or inputs.skilled_crafts:
        target[SocialClass.ARTISAN] += settings.target_artisan
    if KnowledgeBranch.SEAFARING in inputs.branches:
        target[SocialClass.MERCHANT] += settings.target_seafaring_merchant
    if inputs.at_war:
        target[SocialClass.WARRIOR] += settings.target_war_warrior
    if inputs.has_god and inputs.piety >= settings.target_piety_threshold:
        target[SocialClass.PRIEST] += settings.target_priest
    if inputs.godless:
        target[SocialClass.PRIEST] = float(settings.target_godless_priest)
    return normalized_shares(target)


def drift_shares(rules: Rules, shares: Mapping[SocialClass, float], target: Mapping[SocialClass, float]) -> dict[SocialClass, float]:
    rate = fraction(rules.society.class_drift_pct)
    drifted = {social_class: round_tenth(shares[social_class] + (target[social_class] - shares[social_class]) * rate) for social_class in SocialClass}
    return normalized_shares(drifted)


def food_rate(settings: SocietyRules, inputs: EconomyInputs, farmer_share: float, knowledge: KnowledgeRules | None = None) -> float:
    production = (farmer_share / settings.food_farmer_divisor) * (fraction(settings.food_base_pct) + inputs.fertility / settings.food_fertility_divisor)
    if KnowledgeBranch.AGRICULTURE in inputs.branches:
        level = inputs.levels.get(KnowledgeBranch.AGRICULTURE, 1)
        production *= ratio_of(knowledge, level, settings.food_agriculture_pct) if knowledge is not None else fraction(settings.food_agriculture_pct)
    if inputs.bounty_law:
        production *= fraction(settings.food_bounty_law_pct)
    production *= 1 + (inputs.harvest_pct - PERCENT) * fraction(settings.food_harvest_weight_pct) / PERCENT
    return clamp_float(production, fraction(settings.food_rate_min_pct), fraction(settings.food_rate_max_pct))


def _signed(condition: bool, gain: int, loss: int) -> int:
    return gain if condition else -loss


def _when(condition: bool, value: int) -> int:
    return value if condition else 0


def satisfaction_targets(
    rules: Rules,
    inputs: EconomyInputs,
    stocks: Mapping[Commodity, int],
    needs: Mapping[SocialClass, ClassNeed] | None = None,
    corvee_pct: int = 0,
) -> dict[SocialClass, int]:
    settings = rules.society
    prosperity = inputs.prosperity
    war = inputs.at_war
    fed = stocks[Commodity.FOOD] >= settings.sat_hungry_food
    ore_plenty = stocks[Commodity.ORE] > settings.ore_plenty_threshold
    writing = KnowledgeBranch.WRITING in inputs.branches
    targets: dict[SocialClass, float] = {
        SocialClass.FARMER: prosperity + _signed(fed, settings.sat_farmer_fed, settings.sat_farmer_hungry) - _when(war, settings.sat_farmer_war),
        SocialClass.ARTISAN: prosperity + _signed(ore_plenty, settings.sat_artisan_ore_plenty, settings.sat_artisan_ore_scarce),
        SocialClass.MERCHANT: prosperity
        + inputs.routes * settings.sat_merchant_per_route
        - _when(war, settings.sat_merchant_war)
        - _when(inputs.routes == 0, settings.sat_merchant_no_route),
        SocialClass.PRIEST: inputs.piety
        + _signed(inputs.has_god, settings.sat_priest_with_god, settings.sat_priest_godless)
        - _when(inputs.godless, settings.sat_priest_denial),
        SocialClass.WARRIOR: settings.sat_warrior_base
        + _signed(war, settings.sat_warrior_war, settings.sat_warrior_peace)
        + _when(KnowledgeBranch.WARFARE in inputs.branches, settings.sat_warrior_warcraft),
        SocialClass.SCRIBE: prosperity + _signed(writing, settings.sat_scribe_writing, settings.sat_scribe_no_writing),
        SocialClass.NOBLE: settings.sat_noble_base
        + _when(needs is None and stocks[Commodity.GOODS] > settings.effect_goods_plenty, settings.sat_noble_luxury)
        - _when(war, settings.sat_merchant_war),
        SocialClass.SERF_OR_SLAVE: settings.sat_serf_base + _signed(fed, settings.sat_farmer_fed, settings.sat_farmer_hungry),
        SocialClass.OUTCAST: settings.sat_outcast_base + _when(inputs.has_god and inputs.piety >= settings.target_piety_threshold, settings.sat_outcast_alms),
        SocialClass.MONASTIC: settings.sat_monastic_base
        + _signed(writing, settings.sat_scribe_writing, settings.sat_scribe_no_writing)
        + _signed(inputs.has_god, settings.sat_priest_with_god, settings.sat_priest_godless),
    }
    shared: float = -_when(inputs.pays_tribute, settings.sat_tribute) - _when(inputs.cursed, settings.sat_curse)
    if inputs.justice is not None:
        shared += (inputs.justice - settings.sat_justice_midpoint) / settings.sat_justice_divisor
    for social_class, need in (needs or {}).items():
        targets[social_class] -= class_need_penalty(rules, social_class, need)
    for social_class in (SocialClass.FARMER, SocialClass.SERF_OR_SLAVE):
        targets[social_class] -= rules.labour.corvee_satisfaction * corvee_pct / PERCENT
    return {social_class: clamp_int(value + shared, 0, PERCENT) for social_class, value in targets.items()}


def drift_satisfaction(rules: Rules, current: Mapping[SocialClass, int], targets: Mapping[SocialClass, int]) -> dict[SocialClass, int]:
    rate = fraction(rules.society.sat_drift_pct)
    return {social_class: clamp_int(current[social_class] + (targets[social_class] - current[social_class]) * rate, 0, PERCENT) for social_class in SocialClass}


def unhappiest_class(rules: Rules, society: Society) -> SocialClass | None:
    eligible = [social_class for social_class in SocialClass if society.shares[social_class] >= rules.society.revolt_min_class_pct]
    if not eligible:
        return None
    return min(eligible, key=lambda social_class: (society.satisfaction[social_class], list(SocialClass).index(social_class)))


def population_bounds(rules: Rules, entity: EntityRow) -> tuple[int, int]:
    limits = rules.limits
    if entity.entity_type is EntityType.PEOPLE:
        return limits.people_population_floor, limits.people_population_cap
    return limits.population_floor, limits.settlement_population_cap


def land_fertility(rules: Rules, entity: EntityRow, entities: Mapping[int, EntityRow], atlas: RegionAtlas) -> int:
    settings = rules.society
    place = entities.get(entity.location_id) if entity.location_id is not None else None
    if place is None:
        return settings.default_stat
    region_id = atlas.top_region(entity.id)
    region = entities.get(region_id) if region_id is not None else None
    region_fertility = stat(region, "fertility") if region is not None else None
    place_fertility = stat_or(place, "fertility", settings.default_stat)
    if place.entity_type is EntityType.REGION or region_fertility is None:
        return place_fertility
    return round_half_up(place_fertility * fraction(settings.fertility_place_share_pct) + region_fertility * fraction(settings.fertility_region_share_pct))


async def gather_inputs(ctx: TickContext, entity: EntityRow, world: EconomyWorld) -> EconomyInputs:
    settings = ctx.rules.society
    book = world.book
    craft = stat(entity, "craft")
    return EconomyInputs(
        harvest_pct=world.harvests.get(world.atlas.top_region(entity.id) or -1, PERCENT),
        at_war=book.at_war(entity.id),
        routes=book.routes(entity.id),
        pays_tribute=book.pays_tribute(entity.id),
        has_god=world.faith.has_living_god(entity.id),
        godless=book.flagged(entity.id, EntityFlag.GODLESS),
        cursed=book.flagged(entity.id, EntityFlag.CURSED),
        bounty_law=book.laws.has(NaturalLaw.BOUNTY, entity.world_id),
        justice=book.mean_justice(entity.id),
        fertility=land_fertility(ctx.rules, entity, world.entities, world.atlas),
        branches=frozenset(book.knowledge.branches(entity.id)),
        levels={branch: book.knowledge.level(entity.id, branch) for branch in book.knowledge.branches(entity.id)},
        piety=stat_or(entity, "piety", settings.default_stat),
        prosperity=stat_or(entity, "prosperity", settings.default_stat),
        skilled_crafts=craft is not None and craft >= settings.target_craft_threshold,
    )


def apply_class_effects(rules: Rules, entity: EntityRow, society: Society) -> None:
    settings = rules.society
    base = default_class_shares(rules)
    merchant_gain = round_half_up((society.shares[SocialClass.MERCHANT] - base[SocialClass.MERCHANT]) / settings.effect_prosperity_divisor)
    goods_gain = settings.effect_goods_prosperity if society.stocks[Commodity.GOODS] > settings.effect_goods_plenty else 0
    add_prosperity(rules, entity, merchant_gain + goods_gain)
    shift_stat(entity, "piety", round_half_up((society.shares[SocialClass.PRIEST] - base[SocialClass.PRIEST]) / settings.effect_piety_divisor))
    warrior_delta = society.shares[SocialClass.WARRIOR] - base[SocialClass.WARRIOR]
    if entity.entity_type is EntityType.SETTLEMENT:
        shift_stat(entity, "defense", round_half_up(warrior_delta / settings.effect_defense_divisor), settings.effect_default_defense)
    if entity.entity_type is EntityType.PEOPLE:
        shift_stat(entity, "martiality", round_half_up(warrior_delta / settings.effect_martiality_divisor))


async def strike_famine(ctx: TickContext, entity: EntityRow, society: Society) -> None:
    settings = ctx.rules.society
    floor, ceiling = population_bounds(ctx.rules, entity)
    population = stat(entity, "population")
    if population is not None:
        set_stats(entity, population=clamp_int(population * fraction(settings.famine_population_kept_pct), floor, ceiling))
    shift_stat(entity, "prosperity", -settings.famine_prosperity_loss)
    multiple = society.prices[Commodity.FOOD] / PERCENT
    await note(
        ctx,
        f"{entity.name}'s granaries emptied: bread now costs {multiple:.1f}x as much, the farmers are hungry.",
        key="society.famine",
        ids=[entity.id, *([entity.location_id] if entity.location_id else [])],
        feed=FeedCategory.DISASTER,
        kind=ChronicleKind.WORLD,
    )


async def forge_weapons(ctx: TickContext, entity: EntityRow, society: Society) -> EntityRow:
    settings = ctx.rules.society
    rng = ctx.rng("forge")
    lots = await goods_of(ctx.session, ctx.epoch).take(entity.id, CommodityKind.WEAPONS, ctx.rules.refining.weapon_batch_threshold, GoodsFlow.INPUT)
    best = max(lots, key=lambda lot: (lot.quality, lot.quantity), default=None)
    book = await MaterialBook.load(ctx.session)
    material = best.material if best is not None and best.material is not None else MaterialKind.BRONZE
    props = book.props(entity.world_id, material, best.world_material_id if best is not None else None) or book.props(entity.world_id, MaterialKind.BRONZE)
    quality = best.quality if best is not None else settings.default_stat
    assert props is not None
    location = entity.id if entity.entity_type is EntityType.SETTLEMENT else entity.location_id
    weapon = await create_record(
        ctx,
        RecordSpec(
            name=f"{props.label} Swords of {entity.name}",
            entity_type=EntityType.ITEM,
            stats=ItemStats(
                damage=weapon_damage(ctx.rules, props, quality),
                protection=clamp_int(armour_protection(ctx.rules, props, quality) // 4, 0, PERCENT),
                might=min(enchantment_cap(ctx.rules, props), rng.die(max(1, props.conductivity // 4))),
                curse=clamp_int(curse_bonus(ctx.rules, props), 0, PERCENT),
            ),
            body=f"The smiths of {entity.name} forged a batch of {props.label.lower()} weapons.",
            power=settings.weapon_power,
            world_id=entity.world_id,
            location_id=location,
            subtype=WEAPON_SUBTYPE,
        ),
    )
    await set_node_material(ctx.session, weapon.id, MaterialSlot.BODY, props.kind if props.world_material_id is None else None, props.world_material_id)
    if await craft(ctx, weapon, location, quality):
        ctx.count("masterworks")
    bonds = BondRepository(ctx.session)
    await bonds.connect(BondDraft(entity.id, weapon.id, BondKind.PRODUCED, ctx.epoch, "forge"))
    await bonds.connect(BondDraft(entity.id, weapon.id, BondKind.OWNS, ctx.epoch, "forge"))
    await note(
        ctx,
        f"The forges of {entity.name} hammered out new {props.label.lower()} weapons.",
        key="material.weapons_forged",
        ids=[entity.id, weapon.id],
        kind=ChronicleKind.PRODUCTION,
    )
    return weapon


async def bankrupt_guilds(ctx: TickContext, entity: EntityRow, society: Society) -> None:
    settings = ctx.rules.society
    society.satisfaction[SocialClass.MERCHANT] = clamp_int(society.satisfaction[SocialClass.MERCHANT] - settings.bankruptcy_satisfaction_loss, 0, PERCENT)
    society.shares[SocialClass.MERCHANT] = max(0.0, society.shares[SocialClass.MERCHANT] - settings.bankruptcy_share_loss)
    society.shares = normalized_shares(society.shares)
    shift_stat(entity, "prosperity", -settings.bankruptcy_prosperity_loss)
    await note(
        ctx,
        f"The merchant guilds of {entity.name} went bankrupt; debtors are on the streets.",
        key="society.bankruptcy",
        ids=[entity.id],
        kind=ChronicleKind.TRADE,
    )


def spoken_language_id(book: CommunityBook, entity_id: int) -> int | None:
    spoken = book.bonds.outgoing(entity_id, BondKind.SPEAKS)
    return spoken[-1].target_node_id if spoken else None


async def raise_class_uprising(ctx: TickContext, entity: EntityRow, society: Society, social_class: SocialClass, world: EconomyWorld) -> EntityRow:
    settings = ctx.rules.society
    rng = ctx.rng("class_uprising")
    spec = SOCIAL_CLASSES[social_class]
    mood = society.satisfaction[social_class]
    faction = await create_record(
        ctx,
        RecordSpec(
            name=f"{entity.name} {spec.singular} Uprising",
            entity_type=EntityType.FACTION,
            stats=FactionStats(
                strength=clamp_int(settings.revolt_faction_strength + rng.die(settings.revolt_faction_strength_die), 0, PERCENT),
                wealth=clamp_int(settings.revolt_faction_wealth + rng.die(settings.revolt_faction_wealth_die), 0, PERCENT),
                sway=clamp_int(settings.revolt_faction_sway + rng.die(settings.revolt_faction_sway_die), 0, PERCENT),
            ),
            body=f"The {spec.plural.lower()} of {entity.name} rose up when their satisfaction fell to {mood}.",
            power=settings.revolt_faction_power,
            world_id=entity.world_id,
            location_id=entity.id if entity.entity_type is EntityType.SETTLEMENT else entity.location_id,
            subtype=f"{spec.singular.lower()} uprising",
            engine_kind=EngineKind.REBELS,
            social_class=social_class,
            affiliated_entity_id=entity.id,
        ),
    )
    target = await uprising_target(ctx.session, entity)
    await declare_war(ctx, faction.id, target.id, f"{spec.plural.lower()} uprising", cause=WarCause.UPRISING, world_cap=False)
    language = spoken_language_id(world.book, entity.id)
    if language is not None:
        await BondRepository(ctx.session).connect(BondDraft(faction.id, language, BondKind.SPEAKS, ctx.epoch, "the tongue of the uprising"))
    society.satisfaction[social_class] = clamp_int(mood + settings.revolt_relief, 0, PERCENT)
    await note(
        ctx,
        f"In {entity.name} the {spec.plural.lower()} rose up: their satisfaction had fallen to {mood}.",
        key="society.class_uprising",
        ids=[entity.id, faction.id],
        feed=FeedCategory.WAR,
        kind=ChronicleKind.WORLD,
    )
    return faction


async def consume(ctx: TickContext, entity: EntityRow, society: Society, world: EconomyWorld) -> tuple[Meal, Basket]:
    staples = await staples_of(ctx.session, entity)
    meal = await eat(ctx, entity, staples)
    worn = await wear(ctx, entity)
    standing = await standing_of(ctx.session, entity.id)
    found = await needs_of(ctx.session, entity.id)
    basket = build_basket(
        society.shares,
        meal,
        worn,
        staples=staples,
        order=serve_order(standing, society.shares),
        held={key: row.held_pct for key, row in found.items() if row.held_pct is not None},
        luxuries_left=await holding(ctx.session, entity.id, CommodityKind.LUXURIES),
    )
    await save_basket(ctx, entity, basket, found)
    basket = held_needs(await standing_of(ctx.session, entity.id), basket)
    region = world.economy.ground.region_of(entity.id)
    await apply_shortfalls(ctx, entity, basket, region.temperature_band if region is not None else None)
    return meal, basket


async def run_community(ctx: TickContext, entity: EntityRow, inputs: EconomyInputs, world: EconomyWorld, counters: EconomyCounters) -> Society:
    rules = ctx.rules
    settings = rules.society
    society = await society_of(ctx.session, rules, entity.id)
    rng = ctx.rng(f"community.{entity.id}")
    society.shares = drift_shares(rules, society.shares, class_targets(rules, inputs))
    labour = await labour_factor(ctx, entity)
    rate = food_rate(settings, inputs, society.shares[SocialClass.FARMER], rules.knowledge) * labour
    await save_society(ctx.session, entity.id, society, stocks=False)
    await seed_stocks(ctx, entity)
    await harvest_goods(ctx, world.economy, entity, rate, society.shares[SocialClass.FARMER])
    await gather_commons(ctx, world.economy, entity, society.shares[SocialClass.FARMER])
    meal, basket = await consume(ctx, entity, society, world)
    await enforce_storage(ctx, world.economy, entity)
    row = await sync_aggregates(ctx.session, rules, entity)
    if row is not None:
        society.stocks = {commodity: row.stock(commodity) for commodity in Commodity}
        await settle_wealth(ctx, entity, row, society.shares, await local_prices(ctx.session, rules, entity.id, stat_or(entity, "population", 0)))
    corvee = await ctx.session.get(CorveeRow, entity.id)
    targets = satisfaction_targets(rules, inputs, society.stocks, basket.classes, corvee.share_pct if corvee is not None else 0)
    society.satisfaction = drift_satisfaction(rules, society.satisfaction, targets)
    apply_class_effects(rules, entity, society)
    hungry = society.stocks[Commodity.FOOD] <= settings.famine_food or meal.fed_pct < settings.famine_fed_pct
    if hungry and rate < fraction(settings.famine_rate_pct) and counters.famines < settings.famine_cap:
        counters.famines += 1
        await strike_famine(ctx, entity, society)
    weapons = await holding(ctx.session, entity.id, CommodityKind.WEAPONS)
    metallurgy = KnowledgeBranch.METALLURGY in inputs.branches
    can_forge = weapons >= rules.refining.weapon_batch_threshold and metallurgy and society.shares[SocialClass.WARRIOR] >= settings.weapon_warrior_pct
    if can_forge and counters.weapons < settings.weapon_batch_cap and rng.chance(settings.forge_weapon_chance):
        counters.weapons += 1
        await forge_weapons(ctx, entity, society)
    merchants = society.shares[SocialClass.MERCHANT] >= settings.bankruptcy_merchant_pct
    struggling = inputs.routes == 0 and stat_or(entity, "prosperity", settings.default_stat) < settings.bankruptcy_prosperity
    if merchants and struggling and counters.bankruptcies < settings.bankruptcy_cap and rng.chance(settings.guild_bankruptcy_chance):
        counters.bankruptcies += 1
        await bankrupt_guilds(ctx, entity, society)
    restless = unhappiest_class(rules, society)
    population = stat_or(entity, "population", 0)
    if (
        restless is not None
        and society.satisfaction[restless] < settings.revolt_satisfaction
        and population > settings.revolt_min_population
        and counters.uprisings < settings.revolt_cap
        and rng.chance(settings.class_revolt_chance)
    ):
        counters.uprisings += 1
        await raise_class_uprising(ctx, entity, society, restless, world)
    await save_society(ctx.session, entity.id, society, stocks=False)
    counters.touched.add(entity.id)
    return society


@reads(
    "law.justice",
    "people.craft",
    "people.martiality",
    "people.piety",
    "people.population",
    "people.prosperity",
    "place.fertility",
    "region.fertility",
    "settlement.defense",
    "settlement.piety",
    "settlement.population",
    "settlement.prosperity",
    "table.applied_fixups",
    "table.army_profiles",
    "table.bonds",
    "table.calendars",
    "table.class_standing",
    "table.community_cohorts",
    "table.community_labour",
    "table.community_needs",
    "table.community_societies",
    "table.community_stocks",
    "table.corvee_levies",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.forced_weather",
    "table.goods_flows",
    "table.holder_levels",
    "table.holder_techniques",
    "table.incident_participants",
    "table.incidents",
    "table.maimed_cohorts",
    "table.market_prices",
    "table.mobility_events",
    "table.name_registry",
    "table.nodes",
    "table.people_biology",
    "table.people_culture",
    "table.place_environment",
    "table.region_environment",
    "table.resource_commodities",
    "table.resource_profiles",
    "table.resource_workers",
    "table.reverences",
    "table.settlement_infrastructure",
    "table.skills",
    "table.sky_events",
    "table.treaty_parties",
    "table.tributes",
    "table.workshop_designs",
    "table.workshops",
    "table.world_maps",
    "table.world_materials",
    "table.world_seasons",
)
@writes(
    "people.martiality",
    "people.piety",
    "people.population",
    "people.prosperity",
    "settlement.defense",
    "settlement.piety",
    "settlement.population",
    "settlement.prosperity",
    "table.applied_fixups",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.class_standing",
    "table.community_cohorts",
    "table.community_needs",
    "table.community_societies",
    "table.community_stocks",
    "table.entities",
    "table.epoch_year_cursors",
    "table.goods_flows",
    "table.incident_participants",
    "table.incidents",
    "table.mobility_events",
    "table.name_registry",
)
async def society_economy(ctx: TickContext) -> None:
    session = ctx.session
    world = replace(await EconomyWorld.load(session), ledger=await EconomyBook.load(ctx))
    counters = EconomyCounters()
    for key, value in (await society_depth_backfill(ctx, list(await canon(session, SOCIETY_TYPES)))).items():
        ctx.count(f"backfill.{key}", value)
    for entity in await canon(session, SOCIETY_TYPES):
        if entity.status is not EntityStatus.CANON:
            continue
        await run_community(ctx, entity, await gather_inputs(ctx, entity, world), world, counters)
    ctx.count("communities", len(counters.touched))
    ctx.count("famines", counters.famines)
    ctx.count("uprisings", counters.uprisings)
    ctx.count("bankruptcies", counters.bankruptcies)
    ctx.count("weapons", counters.weapons)


async def require_society_entity(session: AsyncSession, entity_id: int) -> EntityRow:
    entity = await session.get(EntityRow, entity_id)
    if entity is None:
        raise NotFoundError("No such community.")
    if entity.entity_type not in SOCIETY_TYPES:
        raise ValidationFailedError("Only peoples and settlements have a society.")
    if entity.status is not EntityStatus.CANON:
        raise ValidationFailedError("The community is no longer part of the world.")
    return entity


async def society_view(session: AsyncSession, rules: Rules, entity_id: int) -> SocietyView:
    entity = await require_society_entity(session, entity_id)
    stored = await session.get(CommunitySocietyRow, entity_id) is not None
    society = await society_of(session, rules, entity_id)
    book = await CommunityBook.load(session)
    settings = rules.society
    unhappiest = unhappiest_class(rules, society)
    bankruptcy = (
        society.shares[SocialClass.MERCHANT] >= settings.bankruptcy_merchant_pct
        and book.routes(entity_id) == 0
        and stat_or(entity, "prosperity", settings.default_stat) < settings.bankruptcy_prosperity
    )
    uprising = (
        unhappiest is not None
        and society.satisfaction[unhappiest] < settings.revolt_satisfaction
        and stat_or(entity, "population", 0) > settings.revolt_min_population
    )
    return SocietyView(entity_id, society, stored, unhappiest, bankruptcy, uprising)


async def set_class_shares(ctx: TickContext, entity_id: int, shares: Mapping[SocialClass, float]) -> Society:
    await require_society_entity(ctx.session, entity_id)
    if any(value < 0 for value in shares.values()) or sum(shares.values()) <= 0:
        raise ValidationFailedError("Class shares must be non-negative and not all zero.")
    society = await society_of(ctx.session, ctx.rules, entity_id)
    society.shares = normalized_shares({**society.shares, **shares})
    await save_society(ctx.session, entity_id, society)
    return society


async def set_satisfaction(ctx: TickContext, entity_id: int, values: Mapping[SocialClass, int]) -> Society:
    await require_society_entity(ctx.session, entity_id)
    if any(value < 0 or value > PERCENT for value in values.values()):
        raise ValidationFailedError(f"Satisfaction must be between 0 and {PERCENT}.")
    society = await society_of(ctx.session, ctx.rules, entity_id)
    society.satisfaction.update(values)
    await save_society(ctx.session, entity_id, society)
    return society


async def storage_room(ctx: TickContext, entity: EntityRow, commodity: Commodity) -> int:
    capacity = await community_capacity(ctx.session, ctx.rules, entity.id, commodity)
    return storage_index(ctx.rules, capacity, aggregate_need(ctx.rules, headcount(entity), commodity))


async def set_stores(ctx: TickContext, entity_id: int, stocks: Mapping[Commodity, int]) -> Society:
    entity = await require_society_entity(ctx.session, entity_id)
    for commodity, value in stocks.items():
        room = await storage_room(ctx, entity, commodity)
        if value < 0 or value > room:
            raise ValidationFailedError(f"{commodity.value.capitalize()} stores must be between 0 and {room}, what the granaries and warehouses can hold.")
    ledger = goods_of(ctx.session, ctx.epoch)
    for commodity, value in stocks.items():
        current = (await society_of(ctx.session, ctx.rules, entity_id)).stocks[commodity]
        await ledger.shift_aggregate(ctx.rules, entity, commodity, value - current, flow=GoodsFlow.PLAYER)
    return await society_of(ctx.session, ctx.rules, entity_id)


async def send_famine(ctx: TickContext, entity_id: int) -> Society:
    entity = await require_society_entity(ctx.session, entity_id)
    ledger = goods_of(ctx.session, ctx.epoch)
    for row in await lots_of(ctx.session, entity.id):
        if COMMODITIES[row.commodity].nourishment > 0 and row.quantity > 0:
            await ledger.take(entity.id, row.commodity, row.quantity, GoodsFlow.PLAYER)
    await sync_aggregates(ctx.session, ctx.rules, entity)
    society = await society_of(ctx.session, ctx.rules, entity_id)
    society.prices[Commodity.FOOD] = ctx.rules.markets.price_cap_pct
    await strike_famine(ctx, entity, society)
    await save_society(ctx.session, entity_id, society, stocks=False)
    return society


async def send_plenty(ctx: TickContext, entity_id: int) -> Society:
    entity = await require_society_entity(ctx.session, entity_id)
    society = await society_of(ctx.session, ctx.rules, entity_id)
    room = await storage_room(ctx, entity, Commodity.FOOD)
    await goods_of(ctx.session, ctx.epoch).shift_aggregate(ctx.rules, entity, Commodity.FOOD, room - society.stocks[Commodity.FOOD], flow=GoodsFlow.PLAYER)
    society = await society_of(ctx.session, ctx.rules, entity_id)
    society.prices[Commodity.FOOD] = ctx.rules.markets.price_floor_pct
    await save_society(ctx.session, entity_id, society, stocks=False)
    await note(ctx, f"Plenty filled the granaries of {entity.name}.", key="society.plenty", ids=[entity.id], kind=ChronicleKind.CREATOR_HAND)
    return society


async def order_forge(ctx: TickContext, entity_id: int) -> EntityRow:
    entity = await require_society_entity(ctx.session, entity_id)
    society = await society_of(ctx.session, ctx.rules, entity_id)
    if await holding(ctx.session, entity.id, CommodityKind.WEAPONS) < ctx.rules.refining.weapon_batch_threshold:
        raise ValidationFailedError(f"There are fewer than {ctx.rules.refining.weapon_batch_threshold} weapons in the stores to forge a named batch from.")
    weapon = await forge_weapons(ctx, entity, society)
    await save_society(ctx.session, entity_id, society, stocks=False)
    return weapon


async def incite_class_uprising(ctx: TickContext, entity_id: int, social_class: SocialClass | None = None) -> EntityRow:
    entity = await require_society_entity(ctx.session, entity_id)
    society = await society_of(ctx.session, ctx.rules, entity_id)
    chosen = social_class or unhappiest_class(ctx.rules, society)
    if chosen is None:
        raise ValidationFailedError("No class is large enough to rise up.")
    faction = await raise_class_uprising(ctx, entity, society, chosen, await EconomyWorld.load(ctx.session))
    await save_society(ctx.session, entity_id, society)
    return faction


PHASES = (Phase("society_economy", society_economy),)
