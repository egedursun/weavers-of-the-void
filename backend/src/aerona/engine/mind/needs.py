from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.mind import CAREER_SKILLS, HUMILIATING_MEMORIES, NEED_LABELS, PLEASURE_TRAITS, THREAT_MEMORIES
from aerona.constants.units import PERCENT
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.body import InjuryRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import MemoryRow
from aerona.domain.enums.body import OPEN_INJURY_STATES
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityType, MortalRole
from aerona.domain.enums.mind import NeedKind, PressureKind, TraitKind, ValueAxis
from aerona.domain.enums.society import Commodity
from aerona.domain.enums.society_depth import ShortfallEffect
from aerona.engine.context import TickContext
from aerona.engine.demography.basket import effect_shortfalls, poverty_of
from aerona.engine.gods.queries import community_of
from aerona.engine.lifecycle.aging import is_notable
from aerona.engine.mind.book import Values, best_skill, is_locked, mind_of, needs_of, pressures_of, write_needs, write_pressures
from aerona.engine.mind.memories import strength_of
from aerona.engine.notes import note
from aerona.engine.primitives.knowledge import known_levels
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import active_bonds
from aerona.engine.primitives.society import class_shares, stock
from aerona.engine.primitives.stats import stat
from aerona.engine.services.war import ongoing_war_count
from aerona.rules.registry import Rules

NEED_LOCK = "needs"
FULL = PERCENT
FERTILITY_KEY = "fertility"
BELONGING_BONDS = (BondKind.LOVES, BondKind.COMPANION, BondKind.DESCENDS_FROM, BondKind.MEMBER_OF, BondKind.LIVES_IN)
BEGGAR_TAG = "beggar"
ROLE_STATUS = {
    MortalRole.RULER: 95,
    MortalRole.HERO: 85,
    MortalRole.CHOSEN: 85,
    MortalRole.SAINT: 80,
    MortalRole.KNIGHT: 75,
    MortalRole.PRIEST: 70,
    MortalRole.SEER: 70,
    MortalRole.CAPTAIN: 70,
    MortalRole.SAGE: 65,
    MortalRole.MERCHANT: 60,
    MortalRole.HEALER: 60,
    MortalRole.SCRIBE: 55,
    MortalRole.ARTISAN: 50,
    MortalRole.WARRIOR: 50,
    MortalRole.EXPLORER: 50,
    MortalRole.HUNTER: 45,
    MortalRole.APPRENTICE: 40,
    MortalRole.FARMER: 35,
    MortalRole.COMMONER: 30,
    MortalRole.BANDIT: 20,
}


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
    food = await stock(session, ctx.rules, community.id, Commodity.FOOD)
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


async def mortal_needs(session: AsyncSession, rules: Rules, mortal: EntityRow, *, values: Values, traits: set[TraitKind], epoch: int) -> dict[NeedKind, int]:
    table = rules.needs
    community = await community_of(session, mortal)
    pressures = await pressures_of(session, community.id) if community is not None else {}
    sustenance = FULL - pressures.get(PressureKind.HUNGER, table.unknown_pressure)
    open_wounds = len(
        list(await session.scalars(select(InjuryRow.id).where(InjuryRow.bearer_node_id == mortal.id, InjuryRow.state.in_(tuple(OPEN_INJURY_STATES)))))
    )
    captive = bool(await active_bonds(session, [BondKind.HOLDS_CAPTIVE], targets=[mortal.id]))
    safety = FULL - pressures.get(PressureKind.INSECURITY, table.unknown_pressure) - open_wounds * table.wound_safety - (table.captive_safety if captive else 0)
    ties = len(await active_bonds(session, BELONGING_BONDS, sources=[mortal.id])) + len(
        await active_bonds(session, [BondKind.LOVES, BondKind.COMPANION, BondKind.DESCENDS_FROM], targets=[mortal.id])
    )
    belonging = table.belonging_base + ties * table.belonging_per_tie
    if TraitKind.GREGARIOUS in traits:
        belonging -= table.trait_demand
    if TraitKind.RECLUSIVE in traits:
        belonging += table.trait_demand
    rules_something = bool(await active_bonds(session, [BondKind.RULES], sources=[mortal.id]))
    status = ROLE_STATUS.get(mortal.mortal_role or MortalRole.COMMONER, table.unknown_pressure) + (table.office_status if rules_something else 0)
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
    if traits & PLEASURE_TRAITS:
        prosperity = stat(community, "prosperity") if community is not None else None
        needs[NeedKind.PLEASURE] = pct(prosperity if prosperity is not None else table.unknown_prosperity)
    return needs


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
