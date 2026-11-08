from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mind import PressureKind, TraitEffect, TraitKind
from aerona.engine.mind.book import pressures_of, scaled_by, trait_effect, traits_of, values_for
from aerona.engine.mind.space import NEUTRAL_DISTANCE, value_distance
from aerona.engine.primitives.queries import active_bonds, living_entity
from aerona.rules.registry import Rules

FULL = PERCENT


async def rulers_of(session: AsyncSession, community_id: int) -> list[EntityRow]:
    rulers: list[EntityRow] = []
    for bond in await active_bonds(session, [BondKind.RULES], targets=[community_id]):
        ruler = await living_entity(session, bond.source_node_id)
        if ruler is not None and ruler.entity_type is EntityType.MORTAL:
            rulers.append(ruler)
    return rulers


async def ruler_traits(session: AsyncSession, community_id: int) -> set[TraitKind]:
    held: set[TraitKind] = set()
    for ruler in await rulers_of(session, community_id):
        held |= await traits_of(session, ruler.id)
    return held


async def ruler_effect(session: AsyncSession, rules: Rules, community_id: int, effect: TraitEffect) -> float:
    return scaled_by(trait_effect(await ruler_traits(session, community_id), effect, rules.traits.effect_scale_pct))


def pressure_lift(level: float, weight_pct: int) -> float:
    return 1 + level / FULL * weight_pct / PERCENT


async def war_drive(session: AsyncSession, rules: Rules, community_id: int) -> float:
    pressures = await pressures_of(session, community_id)
    push = (pressures.get(PressureKind.HUMILIATION, 0) + pressures.get(PressureKind.OVERCROWDING, 0)) / 2
    return pressure_lift(push, rules.needs.war_pressure_pct) * await ruler_effect(session, rules, community_id, TraitEffect.WAR_APPETITE)


async def betrayal_drive(session: AsyncSession, rules: Rules, community_id: int) -> float:
    return await ruler_effect(session, rules, community_id, TraitEffect.BETRAYAL)


async def zeal_drive(session: AsyncSession, rules: Rules, community_id: int) -> float:
    held: set[TraitKind] = set()
    for bond in await active_bonds(session, [BondKind.RULES, BondKind.MEMBER_OF], targets=[community_id]):
        member = await living_entity(session, bond.source_node_id)
        if member is not None and member.entity_type is EntityType.MORTAL:
            held |= await traits_of(session, member.id)
    return scaled_by(trait_effect(held, TraitEffect.ZEAL, rules.traits.effect_scale_pct))


async def deceit_drive(session: AsyncSession, rules: Rules, community_id: int) -> float:
    return await ruler_effect(session, rules, community_id, TraitEffect.DECEIT)


async def greed_drive(session: AsyncSession, rules: Rules, community_id: int) -> float:
    return await ruler_effect(session, rules, community_id, TraitEffect.GREED)


async def cruelty_drive(session: AsyncSession, rules: Rules, community_id: int) -> float:
    return await ruler_effect(session, rules, community_id, TraitEffect.CRUELTY)


async def closeness(session: AsyncSession, first: int, second: int) -> float:
    distance = value_distance(await values_for(session, first), await values_for(session, second))
    return max(0.0, (FULL - distance) / NEUTRAL_DISTANCE)


async def unrest(session: AsyncSession, rules: Rules, community_id: int) -> int:
    pressures = await pressures_of(session, community_id)
    weighted = (
        pressures.get(PressureKind.POVERTY, 0) * 2
        + pressures.get(PressureKind.HUMILIATION, 0)
        + pressures.get(PressureKind.INSECURITY, 0)
        + pressures.get(PressureKind.HUNGER, 0)
    ) / 5
    justice = await ruler_effect(session, rules, community_id, TraitEffect.JUSTICE)
    return round(weighted / justice) if justice else round(weighted)


async def hunger(session: AsyncSession, community_id: int) -> int:
    return (await pressures_of(session, community_id)).get(PressureKind.HUNGER, 0)


async def expedition_drive(session: AsyncSession, rules: Rules, community_id: int) -> float:
    pressures = await pressures_of(session, community_id)
    push = max(pressures.get(PressureKind.OVERCROWDING, 0), pressures.get(PressureKind.HUNGER, 0), pressures.get(PressureKind.POVERTY, 0))
    return pressure_lift(push, rules.needs.expedition_pressure_pct) * await ruler_effect(session, rules, community_id, TraitEffect.EXPLORATION)


async def faction_drive(session: AsyncSession, rules: Rules, community_id: int) -> float:
    pressures = await pressures_of(session, community_id)
    push = max(pressures.get(PressureKind.POVERTY, 0), pressures.get(PressureKind.HUMILIATION, 0), pressures.get(PressureKind.STAGNATION, 0))
    return pressure_lift(push, rules.needs.faction_pressure_pct)
