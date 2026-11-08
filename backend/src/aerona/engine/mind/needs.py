from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.mind import CAREER_SKILLS, HUMILIATING_MEMORIES, NEED_LABELS, PLEASURE_TRAITS, SKILLS, THREAT_MEMORIES
from aerona.constants.units import PERCENT
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.afflictions import AfflictionRow
from aerona.db.tables.body import ConditionRow, InjuryRow
from aerona.db.tables.economy import CommunityStockRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.industry import CommunityIndustryRow
from aerona.db.tables.mind import MemoryRow, NeedRow, SkillRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.domain.enums.body import OPEN_INJURY_STATES
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityStatus, EntityType, MortalRole
from aerona.domain.enums.industry import QualityTier
from aerona.domain.enums.mind import NeedKind, PreferenceKind, PressureKind, SkillFamily, SkillKind, TraitKind, ValueAxis
from aerona.domain.enums.society import Commodity
from aerona.domain.enums.society_depth import ShortfallEffect
from aerona.engine.context import TickContext
from aerona.engine.demography.basket import effect_shortfalls, fed_index, poverty_of
from aerona.engine.gods.queries import community_of
from aerona.engine.households.homes import home_of
from aerona.engine.industry.quality import at_least
from aerona.engine.lifecycle.aging import is_notable
from aerona.engine.mind.book import Values, best_skill, is_locked, mind_of, needs_of, pressures_of, write_needs, write_pressures
from aerona.engine.mind.memories import strength_of
from aerona.engine.mind.preferences import market_fit, nature_bonus
from aerona.engine.mortal.kin import close_kin_of, partners_of
from aerona.engine.notes import note
from aerona.engine.primitives.knowledge import known_levels
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import active_bonds, living_entity
from aerona.engine.primitives.society import class_shares, stock
from aerona.engine.primitives.stats import stat
from aerona.engine.services.war import ongoing_war_count
from aerona.rules.registry import Rules

NEED_LOCK = "needs"
FULL = PERCENT
FERTILITY_KEY = "fertility"
BELONGING_BONDS = (BondKind.LOVES, BondKind.COMPANION, BondKind.MEMBER_OF, BondKind.LIVES_IN)
BEGGAR_TAG = "beggar"
LEARNED_SKILLS = frozenset(skill for skill, spec in SKILLS.items() if spec.family is SkillFamily.KNOWLEDGE)
MAKING_SKILLS = frozenset(skill for skill, spec in SKILLS.items() if spec.family is SkillFamily.CRAFT)
FIGHT_SKILLS = frozenset(skill for skill, spec in SKILLS.items() if spec.family is SkillFamily.COMBAT)
TRAVEL_SKILLS = frozenset({SkillKind.SAILING, SkillKind.NAVIGATION, SkillKind.MOUNTAINEERING, SkillKind.RIDING, SkillKind.TRACKING})


def role_status(rules: Rules, role: MortalRole) -> int:
    table = rules.needs
    statuses = {
        MortalRole.RULER: table.status_ruler,
        MortalRole.HERO: table.status_hero,
        MortalRole.CHOSEN: table.status_chosen,
        MortalRole.SAINT: table.status_saint,
        MortalRole.KNIGHT: table.status_knight,
        MortalRole.PRIEST: table.status_priest,
        MortalRole.SEER: table.status_seer,
        MortalRole.CAPTAIN: table.status_captain,
        MortalRole.SAGE: table.status_sage,
        MortalRole.MERCHANT: table.status_merchant,
        MortalRole.HEALER: table.status_healer,
        MortalRole.SCRIBE: table.status_scribe,
        MortalRole.ARTISAN: table.status_artisan,
        MortalRole.WARRIOR: table.status_warrior,
        MortalRole.EXPLORER: table.status_explorer,
        MortalRole.HUNTER: table.status_hunter,
        MortalRole.APPRENTICE: table.status_apprentice,
        MortalRole.FARMER: table.status_farmer,
        MortalRole.COMMONER: table.status_commoner,
        MortalRole.BANDIT: table.status_bandit,
    }
    return statuses.get(role, table.unknown_pressure)


async def sustenance_need(session: AsyncSession, mortal_id: int) -> float:
    found = await session.get(NeedRow, (mortal_id, NeedKind.SUSTENANCE))
    return found.value / FULL if found is not None else 1.0


def pct(value: float) -> int:
    return clamp_int(value, 0, FULL)


def gap_pct(limit: float, value: float) -> int:
    return pct((limit - value) * PERCENT / limit) if limit > 0 else 0


async def community_pressures(ctx: TickContext, community: EntityRow, culture: Values, plagued: set[int]) -> dict[PressureKind, int]:
    table = ctx.rules.needs
    session = ctx.session
    prosperity = stat(community, "prosperity")
    prosperity = prosperity if prosperity is not None else table.unknown_prosperity
    population = stat(community, "population") or 0
    fed = await fed_index(session, community.id)
    food = fed if fed is not None else await stock(session, ctx.rules, community.id, Commodity.FOOD)
    basket = await effect_shortfalls(session, community.id)
    plenty = ctx.rules.consumption
    hunger = max(
        gap_pct(table.hunger_food, food),
        gap_pct(table.hunger_prosperity, prosperity),
        basket.get(ShortfallEffect.HUNGER, 0) * plenty.hunger_pressure_pct / PERCENT,
    )
    memories = list(await session.scalars(select(MemoryRow).where(MemoryRow.holder_node_id == community.id)))
    threat = sum(-strength_of(row, ctx.epoch) for row in memories if row.kind in THREAT_MEMORIES and row.magnitude < 0)
    wars = await ongoing_war_count(session, community.id)
    insecurity = wars * table.war_insecurity + threat * table.threat_pct / PERCENT + (table.plague_insecurity if community.id in plagued else 0)
    insecurity += basket.get(ShortfallEffect.INSECURITY, 0) * plenty.insecurity_pressure_pct / PERCENT
    location = await session.get(EntityRow, community.location_id) if community.location_id is not None else None
    fertility = stat(location, FERTILITY_KEY) if location is not None else None
    room = (fertility if fertility is not None else table.default_fertility) * table.crowd_per_fertility
    crowding = pct((population - room) * PERCENT / room) if room > 0 else 0
    poverty = max(
        gap_pct(table.poverty_prosperity, prosperity),
        pct(await poverty_of(session, community.id, await class_shares(session, ctx.rules, community.id)) * plenty.poverty_pressure_pct / PERCENT),
    )
    piety_value = max(0, culture.get(ValueAxis.PIETY, 0))
    piety_stat = stat(community, "piety")
    worships = bool(await active_bonds(session, [BondKind.WORSHIPS], sources=[community.id]))
    impiety = piety_value * (PERCENT - (piety_stat if piety_stat is not None else table.unknown_piety)) / PERCENT
    if not worships:
        impiety += table.godless_impiety
    impiety += basket.get(ShortfallEffect.IMPIETY, 0) * plenty.impiety_pressure_pct / PERCENT
    shame = sum(-strength_of(row, ctx.epoch) for row in memories if row.kind in HUMILIATING_MEMORIES and row.magnitude < 0)
    tribute = len(await active_bonds(session, [BondKind.PAYS_TRIBUTE], sources=[community.id]))
    humiliation = shame * table.humiliation_pct / PERCENT + tribute * table.tribute_humiliation
    levels = (await known_levels(session, [community.id])).get(community.id)
    known = sum(levels.values()) if levels else 0
    innovation = max(0, -culture.get(ValueAxis.TRADITION, 0))
    stagnation = (
        gap_pct(table.stagnation_prosperity, prosperity) * table.stagnation_weight_pct / PERCENT
        + innovation * table.innovation_pct / PERCENT
        - known * table.knowledge_relief
        + basket.get(ShortfallEffect.ARCANE, 0) * plenty.arcane_pressure_pct / PERCENT
    )
    return {
        PressureKind.HUNGER: pct(hunger),
        PressureKind.INSECURITY: pct(insecurity),
        PressureKind.OVERCROWDING: crowding,
        PressureKind.POVERTY: poverty,
        PressureKind.IMPIETY: pct(impiety),
        PressureKind.HUMILIATION: pct(humiliation),
        PressureKind.STAGNATION: pct(stagnation),
    }


async def update_pressures(ctx: TickContext, community: EntityRow, culture: Values, plagued: set[int]) -> bool:
    if is_locked(await mind_of(ctx.session, community.id), NEED_LOCK):
        return False
    await write_pressures(ctx.session, community.id, await community_pressures(ctx, community, culture, plagued))
    return True


async def fine_fare(session: AsyncSession, rules: Rules, community: EntityRow | None) -> int:
    row = await session.get(CommunityIndustryRow, community.id) if community is not None else None
    return rules.quality.fine_meal_sustenance if row is not None and at_least(rules, row.meal_quality, QualityTier.FINE) else 0


async def fine_cloth(session: AsyncSession, rules: Rules, community_id: int) -> bool:
    rows = list(
        await session.scalars(
            select(CommunityStockRow).where(
                CommunityStockRow.community_entity_id == community_id, CommunityStockRow.commodity == CommodityKind.CLOTH, CommunityStockRow.quantity > 0
            )
        )
    )
    stocked = sum(row.quantity for row in rows)
    return stocked > 0 and at_least(rules, round_half_up(sum(row.quality * row.quantity for row in rows) / stocked), QualityTier.FINE)


async def drink_needs(session: AsyncSession, rules: Rules, community: EntityRow | None, needs: dict[NeedKind, int]) -> None:
    row = await session.get(CommunityIndustryRow, community.id) if community is not None else None
    if row is None or community is None:
        return
    table = rules.drink
    tastes = await market_fit(session, community.id)
    thirsty = max((strength for (kind, _), strength in tastes.items() if kind is PreferenceKind.DRINK), default=0) >= table.needed_at
    if thirsty:
        current = needs.get(NeedKind.DRINK, FULL)
        needs[NeedKind.DRINK] = pct(current * (PERCENT - table.need_pct) / PERCENT + row.drink * table.need_pct / PERCENT)
    else:
        needs[NeedKind.PLEASURE] = pct(needs.get(NeedKind.PLEASURE, 0) + table.pleasure * row.drink / PERCENT)


async def mortal_needs(session: AsyncSession, rules: Rules, mortal: EntityRow, *, values: Values, traits: set[TraitKind], epoch: int) -> dict[NeedKind, int]:
    table = rules.needs
    community = await community_of(session, mortal)
    pressures = await pressures_of(session, community.id) if community is not None else {}
    sustenance = FULL - pressures.get(PressureKind.HUNGER, table.unknown_pressure) + await fine_fare(session, rules, community)
    open_wounds = len(
        list(await session.scalars(select(InjuryRow.id).where(InjuryRow.bearer_node_id == mortal.id, InjuryRow.state.in_(tuple(OPEN_INJURY_STATES)))))
    )
    captive = bool(await active_bonds(session, [BondKind.HOLDS_CAPTIVE], targets=[mortal.id]))
    safety = FULL - pressures.get(PressureKind.INSECURITY, table.unknown_pressure) - open_wounds * table.wound_safety - (table.captive_safety if captive else 0)
    ties = len(await active_bonds(session, BELONGING_BONDS, sources=[mortal.id])) + len(
        await active_bonds(session, [BondKind.LOVES, BondKind.COMPANION], targets=[mortal.id])
    )
    ties += len([kin for kin in await close_kin_of(session, mortal.id) if await living_entity(session, kin) is not None])
    belonging = table.belonging_base + ties * table.belonging_per_tie
    if TraitKind.GREGARIOUS in traits:
        belonging -= table.trait_demand
    if TraitKind.RECLUSIVE in traits:
        belonging += table.trait_demand
    rules_something = bool(await active_bonds(session, [BondKind.RULES], sources=[mortal.id]))
    status = role_status(rules, mortal.mortal_role or MortalRole.COMMONER) + (table.office_status if rules_something else 0)
    status -= table.trait_demand * len(traits & {TraitKind.PROUD, TraitKind.AMBITIOUS})
    if BEGGAR_TAG in await EntityRepository(session).tags(mortal.id):
        status -= table.beggar_status_loss
    mind = await mind_of(session, mortal.id)
    role = mortal.mortal_role or MortalRole.COMMONER
    craft = await best_skill(session, mortal.id, CAREER_SKILLS.get(role, ()))
    purpose = craft * table.purpose_skill_pct / PERCENT + table.purpose_base
    if mind is not None and mind.career_ended_epoch is not None and epoch - mind.career_ended_epoch < table.career_loss_epochs:
        purpose -= table.career_loss_purpose
    piety = values.get(ValueAxis.PIETY, 0)
    worships = bool(await active_bonds(session, [BondKind.WORSHIPS], sources=[mortal.id]))
    faith = table.faith_worship + piety // 2 if worships else FULL - max(0, piety)
    if TraitKind.ZEALOUS in traits and not worships:
        faith -= table.trait_demand
    needs = {
        NeedKind.SUSTENANCE: pct(sustenance),
        NeedKind.SAFETY: pct(safety),
        NeedKind.BELONGING: pct(belonging),
        NeedKind.STATUS: pct(status),
        NeedKind.PURPOSE: pct(purpose),
        NeedKind.FAITH: pct(faith),
    }
    prosperity = stat(community, "prosperity") if community is not None else None
    needs[NeedKind.PLEASURE] = pct(prosperity if prosperity is not None else table.unknown_prosperity)
    if traits & PLEASURE_TRAITS:
        needs[NeedKind.PLEASURE] = pct(needs[NeedKind.PLEASURE] - table.trait_demand)
    needs.update(await deeper_needs(session, rules, mortal, community, pressures, sustenance=sustenance, wounds=open_wounds, epoch=epoch))
    await drink_needs(session, rules, community, needs)
    if community is not None and await fine_cloth(session, rules, community.id):
        needs[NeedKind.COMFORT] = pct(needs.get(NeedKind.COMFORT, 0) + rules.quality.fine_cloth_comfort)
    await home_needs(session, rules, mortal, needs)
    return needs


def blended(current: int, quality: int, weight_pct: int) -> int:
    return pct(current + (quality - current) * weight_pct / PERCENT)


async def home_needs(session: AsyncSession, rules: Rules, mortal: EntityRow, needs: dict[NeedKind, int]) -> None:
    _household, dwelling, quality, members = await home_of(session, rules, mortal.id)
    if dwelling is None:
        return
    table = rules.households
    needs[NeedKind.COMFORT] = blended(needs.get(NeedKind.COMFORT, 0), quality, table.comfort_home_pct)
    needs[NeedKind.BEAUTY] = blended(needs.get(NeedKind.BEAUTY, 0), quality, table.beauty_home_pct)
    needs[NeedKind.STATUS] = blended(needs.get(NeedKind.STATUS, 0), quality, table.status_home_pct)
    spare = dwelling.rooms - members
    rest = spare * table.rest_rooms if spare >= 0 else spare * table.crowding_rest
    needs[NeedKind.REST] = pct(needs.get(NeedKind.REST, 0) + rest)


async def deeper_needs(
    session: AsyncSession,
    rules: Rules,
    mortal: EntityRow,
    community: EntityRow | None,
    pressures: dict[PressureKind, int],
    *,
    sustenance: float,
    wounds: int,
    epoch: int,
) -> dict[NeedKind, int]:
    table = rules.needs_depth
    profile = await session.get(MortalProfileRow, mortal.id)
    stress = profile.stress if profile is not None else 0
    wealth = profile.wealth if profile is not None else 0
    prosperity = (stat(community, "prosperity") if community is not None else None) or rules.needs.unknown_prosperity
    settlement = await session.get(SettlementProfileRow, community.id) if community is not None else None
    sanitation = settlement.sanitation if settlement is not None else rules.needs.unknown_prosperity
    ailing = len(
        list(await session.scalars(select(ConditionRow.id).where(ConditionRow.bearer_node_id == mortal.id, ConditionRow.ended_epoch.is_(None))))
    ) + len(list(await session.scalars(select(AfflictionRow.id).where(AfflictionRow.bearer_node_id == mortal.id, AfflictionRow.cured_epoch.is_(None)))))
    kin = [relative for relative in await close_kin_of(session, mortal.id) if await living_entity(session, relative) is not None]
    loves = await partners_of(session, mortal.id) + [bond.target_node_id for bond in await active_bonds(session, [BondKind.LOVES], sources=[mortal.id])]
    companions = len(await active_bonds(session, [BondKind.COMPANION], sources=[mortal.id])) + len(
        await active_bonds(session, [BondKind.COMPANION, BondKind.PET_OF], targets=[mortal.id])
    )
    warm = len(list(await session.scalars(select(MemoryRow.id).where(MemoryRow.holder_node_id == mortal.id, MemoryRow.magnitude > 0))))
    population = (stat(community, "population") if community is not None else None) or 0
    skills = list(await session.scalars(select(SkillRow).where(SkillRow.holder_node_id == mortal.id, SkillRow.subject_node_id.is_(None))))
    levels = {row.skill: row.level for row in skills}
    used = {row.skill for row in skills if row.last_used_epoch >= epoch}
    home = [mortal.id, *([community.id] if community is not None else [])]
    branches = sum(len(found) for found in (await known_levels(session, home)).values())
    works = len(
        list(
            await session.scalars(
                select(EntityRow.id).where(EntityRow.location_id.in_(home), EntityRow.entity_type == EntityType.ARTWORK, EntityRow.status == EntityStatus.CANON)
            )
        )
    )
    place = await session.get(EntityRow, mortal.location_id) if mortal.location_id is not None else None
    fertility = (stat(place, FERTILITY_KEY) if place is not None else None) or rules.needs.default_fertility
    if community is not None and community.location_id is not None:
        land = await session.get(EntityRow, community.location_id)
        fertility = (stat(land, FERTILITY_KEY) if land is not None else None) or fertility
    at_war = bool(await ongoing_war_count(session, community.id)) if community is not None else False
    return {
        NeedKind.DRINK: pct(sustenance + (FULL - sustenance) * (PERCENT - table.drink_hunger_pct) / PERCENT),
        NeedKind.REST: pct(FULL - stress * table.rest_stress_pct / PERCENT - wounds * table.rest_wound - (table.rest_war if at_war else 0)),
        NeedKind.COMFORT: pct(
            prosperity * table.comfort_prosperity_pct / PERCENT
            + wealth * table.comfort_wealth_pct / PERCENT
            + sanitation * table.comfort_sanitation_pct / PERCENT
        ),
        NeedKind.HEALTH: pct(FULL - wounds * table.health_wound - ailing * table.health_condition),
        NeedKind.FAMILY: pct(table.family_base + len(kin) * table.family_per_kin),
        NeedKind.FRIENDS: pct(table.friends_base + (companions + warm) * table.friends_per_tie),
        NeedKind.ROMANCE: table.romance_loved if loves else table.romance_alone,
        NeedKind.SOLITUDE: pct(FULL - population * PERCENT / table.solitude_crowd),
        NeedKind.LEARNING: pct(
            table.learning_base
            + max((levels.get(skill, 0) for skill in LEARNED_SKILLS), default=0) * table.learning_skill_pct / PERCENT
            + branches * table.learning_branch
        ),
        NeedKind.CREATING: pct(
            table.creating_base
            + max((levels.get(skill, 0) for skill in MAKING_SKILLS), default=0) * table.creating_skill_pct / PERCENT
            + (table.creating_practised if used & MAKING_SKILLS else 0)
        ),
        NeedKind.BEAUTY: pct(table.beauty_base + works * table.beauty_per_work),
        NeedKind.NATURE: pct(fertility * table.nature_fertility_pct / PERCENT + await nature_bonus(session, rules, mortal)),
        NeedKind.ADVENTURE: pct(table.adventure_base + (table.adventure_travelled if used & TRAVEL_SKILLS or mortal.mortal_role is MortalRole.EXPLORER else 0)),
        NeedKind.FIGHTING: pct(table.fighting_base + (table.fighting_fought if used & FIGHT_SKILLS else 0)),
        NeedKind.WEALTH: pct(wealth * table.wealth_pct / PERCENT),
        NeedKind.ORDER: pct(
            FULL
            - pressures.get(PressureKind.INSECURITY, 0) * table.order_insecurity_pct / PERCENT
            - pressures.get(PressureKind.HUMILIATION, 0) * table.order_humiliation_pct / PERCENT
        ),
    }


async def update_needs(ctx: TickContext, mortal: EntityRow, values: Values, traits: set[TraitKind]) -> bool:
    if mortal.entity_type is not EntityType.MORTAL or is_locked(await mind_of(ctx.session, mortal.id), NEED_LOCK):
        return False
    before = await needs_of(ctx.session, mortal.id)
    after = await mortal_needs(ctx.session, ctx.rules, mortal, values=values, traits=traits, epoch=ctx.epoch)
    await write_needs(ctx.session, mortal.id, after)
    floor = ctx.rules.needs.despair_level
    fallen = [need for need, value in after.items() if value < floor <= before.get(need, FULL)]
    if fallen and is_notable(ctx.rules, mortal, await EntityRepository(ctx.session).flags(mortal.id)):
        lost = " and ".join(NEED_LABELS[need].lower() for need in sorted(fallen))
        await note(ctx, f"{mortal.name} has lost all {lost}.", key="need.despair", ids=[mortal.id])
    return True


def unmet(needs: dict[NeedKind, int]) -> int:
    return max((FULL - value for value in needs.values()), default=0)
