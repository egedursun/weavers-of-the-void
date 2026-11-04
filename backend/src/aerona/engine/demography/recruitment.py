from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.society import SocialClass
from aerona.engine.context import TickContext
from aerona.engine.factions.book import CLASS_OF_KIND, ENGINE_OF_KIND
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.queries import canon
from aerona.engine.primitives.stats import shift_stat
from aerona.rules.registry import Rules

MIDDLE = PERCENT // 2
KIND_OF_ENGINE = {engine: kind for kind, engine in ENGINE_OF_KIND.items()}


async def faction_class(session: AsyncSession, faction: EntityRow) -> SocialClass | None:
    if faction.social_class is not None:
        return faction.social_class
    profile = await session.get(FactionProfileRow, faction.id)
    kind = profile.kind if profile is not None else KIND_OF_ENGINE.get(faction.engine_kind) if faction.engine_kind is not None else None
    return CLASS_OF_KIND.get(kind) if kind is not None else None


def recruitment_factor(rules: Rules, society: CommunitySocietyRow | None, social_class: SocialClass) -> float:
    if society is None:
        return 1.0
    discontent = (MIDDLE - society.satisfaction(social_class)) / MIDDLE
    return max(0.0, 1 + discontent * rules.factions.recruit_satisfaction_pct / PERCENT)


async def founding_factor(session: AsyncSession, rules: Rules, community_id: int, kind: FactionKind) -> float:
    social_class = CLASS_OF_KIND.get(kind)
    if social_class is None:
        return 1.0
    return recruitment_factor(rules, await session.get(CommunitySocietyRow, community_id), social_class)


def recruits(rules: Rules, society: CommunitySocietyRow, social_class: SocialClass) -> int:
    return round_half_up((MIDDLE - society.satisfaction(social_class)) * rules.factions.recruit_strength_pct / PERCENT)


async def recruit(ctx: TickContext) -> int:
    changed = 0
    for faction in await canon(ctx.session, [EntityType.FACTION]):
        social_class = await faction_class(ctx.session, faction)
        if social_class is None or faction.affiliated_entity_id is None:
            continue
        society = await ctx.session.get(CommunitySocietyRow, faction.affiliated_entity_id)
        if society is None:
            continue
        delta = recruits(ctx.rules, society, social_class)
        if delta and shift_stat(faction, "strength", delta) is not None:
            changed += 1
    return changed
