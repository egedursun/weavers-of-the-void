from collections.abc import Iterable, Mapping

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.command import AREAS, FAMILY_AREA, TRAIT_AREAS
from aerona.constants.units import PERCENT
from aerona.db.tables.military import CommanderTraitRow
from aerona.db.tables.mind import SkillRow
from aerona.domain.enums.military import CommandArea, CommanderTrait, UnitFamily
from aerona.domain.enums.mind import SkillKind
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.rules.registry import Rules

Areas = Mapping[CommandArea, int]


def areas_from(skills: Mapping[SkillKind, int], traits: Iterable[CommanderTrait]) -> dict[CommandArea, int]:
    held = set(traits)
    found: dict[CommandArea, int] = {}
    for area, spec in AREAS.items():
        support = max((skills.get(skill, 0) for skill in spec.support), default=0)
        value = (skills.get(spec.lead, 0) + support) / 2 + sum(TRAIT_AREAS[trait].get(area, 0) for trait in held)
        found[area] = clamp_int(round_half_up(value), 0, PERCENT)
    return found


async def command_areas(session: AsyncSession, commander_id: int | None) -> dict[CommandArea, int]:
    if commander_id is None:
        return dict.fromkeys(CommandArea, 0)
    rows = await session.execute(select(SkillRow.skill, func.max(SkillRow.level)).where(SkillRow.holder_node_id == commander_id).group_by(SkillRow.skill))
    skills = {skill: int(level or 0) for skill, level in rows.all()}
    traits = await session.scalars(select(CommanderTraitRow.trait).where(CommanderTraitRow.mortal_entity_id == commander_id))
    return areas_from(skills, list(traits))


def area_factor(rules: Rules, areas: Areas, area: CommandArea | None) -> float:
    if area is None:
        return 1.0
    return 1 + rules.army_depth.command_area_pct * areas.get(area, 0) / PERCENT / PERCENT


def family_factor(rules: Rules, areas: Areas, family: UnitFamily) -> float:
    return area_factor(rules, areas, FAMILY_AREA[family])


def best_area(areas: Areas) -> CommandArea | None:
    ranked = sorted(areas.items(), key=lambda item: (-item[1], list(CommandArea).index(item[0])))
    return ranked[0][0] if ranked and ranked[0][1] > 0 else None


def thrift(rules: Rules, areas: Areas) -> float:
    return 1 - rules.army_depth.logistics_food_pct * areas.get(CommandArea.LOGISTICS, 0) / PERCENT / PERCENT
