from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.body import BodyRow
from aerona.db.tables.ecology import BeastProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.body import BodyPlan
from aerona.domain.enums.economy import FoeNature
from aerona.domain.enums.entity import EntityFlag, EntityType
from aerona.engine.economy.equipment import weapon_of
from aerona.engine.economy.materials import holy_edge
from aerona.rules.registry import Rules

UNDEAD_TYPES = frozenset({EntityType.SPIRIT})
VOID_TYPES = frozenset({EntityType.OUTER_BEING})
UNDEAD_FLAGS = frozenset({EntityFlag.CROSSED_TO_THE_DEAD})
VOID_FLAGS = frozenset({EntityFlag.VOID})
CURSED_FLAGS = frozenset({EntityFlag.CURSED})


async def plan_of(session: AsyncSession, foe: EntityRow) -> BodyPlan | None:
    body = await session.get(BodyRow, foe.id)
    if body is None and foe.entity_type is EntityType.BEAST:
        beast = await session.get(BeastProfileRow, foe.id)
        body = await session.get(BodyRow, beast.species_entity_id) if beast is not None and beast.species_entity_id is not None else None
    return body.plan if body is not None else None


async def natures_of(session: AsyncSession, foe: EntityRow | None) -> frozenset[FoeNature]:
    if foe is None:
        return frozenset()
    flags = await EntityRepository(session).flags(foe.id)
    found: set[FoeNature] = set()
    if foe.entity_type in UNDEAD_TYPES or flags & UNDEAD_FLAGS or await plan_of(session, foe) is BodyPlan.INCORPOREAL:
        found.add(FoeNature.UNDEAD)
    if flags & CURSED_FLAGS:
        found.add(FoeNature.CURSED)
    if foe.entity_type in VOID_TYPES or flags & VOID_FLAGS:
        found.add(FoeNature.VOID)
    return frozenset(found)


async def holy_strike(session: AsyncSession, rules: Rules, wielder_id: int | None, foe: EntityRow | None) -> float:
    natures = await natures_of(session, foe)
    if not natures or wielder_id is None:
        return 1.0
    return holy_edge(rules, await weapon_of(session, wielder_id), natures)
