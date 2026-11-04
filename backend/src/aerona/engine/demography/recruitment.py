from collections.abc import Mapping
from types import MappingProxyType

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.domain.enums.entity import EngineKind, EntityType
from aerona.domain.enums.society import SocialClass
from aerona.engine.context import TickContext
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.queries import canon
from aerona.engine.primitives.stats import shift_stat
from aerona.rules.registry import Rules

MIDDLE = PERCENT // 2
CLASS_OF_KIND: Mapping[EngineKind, SocialClass] = MappingProxyType(
    {EngineKind.MERCHANT_GUILD: SocialClass.MERCHANT, EngineKind.PRIESTS_COUNCIL: SocialClass.PRIEST, EngineKind.WARRIOR_BAND: SocialClass.WARRIOR}
)


def faction_class(faction: EntityRow) -> SocialClass | None:
    if faction.social_class is not None:
        return faction.social_class
    kind = faction.engine_kind
    return CLASS_OF_KIND.get(kind) if isinstance(kind, EngineKind) else None


def recruitment_factor(rules: Rules, society: CommunitySocietyRow | None, social_class: SocialClass) -> float:
    if society is None:
        return 1.0
    discontent = (MIDDLE - society.satisfaction(social_class)) / MIDDLE
    return max(0.0, 1 + discontent * rules.factions.recruit_satisfaction_pct / PERCENT)


async def founding_factor(session: AsyncSession, rules: Rules, community_id: int, engine_kind: EngineKind) -> float:
    social_class = CLASS_OF_KIND.get(engine_kind)
    if social_class is None:
        return 1.0
    return recruitment_factor(rules, await session.get(CommunitySocietyRow, community_id), social_class)


def recruits(rules: Rules, society: CommunitySocietyRow, social_class: SocialClass) -> int:
    return round_half_up((MIDDLE - society.satisfaction(social_class)) * rules.factions.recruit_strength_pct / PERCENT)


async def recruit(ctx: TickContext) -> int:
    changed = 0
    for faction in await canon(ctx.session, [EntityType.FACTION]):
        social_class = faction_class(faction)
        if social_class is None or faction.affiliated_entity_id is None:
            continue
        society = await ctx.session.get(CommunitySocietyRow, faction.affiliated_entity_id)
        if society is None:
            continue
        delta = recruits(ctx.rules, society, social_class)
        if delta and shift_stat(faction, "strength", delta) is not None:
            changed += 1
    return changed
