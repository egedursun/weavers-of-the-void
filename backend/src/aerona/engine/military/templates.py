from collections.abc import Mapping

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.units import STYLE_UNITS, UNITS, UnitSpec
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.military import ArmyTemplateRow
from aerona.db.tables.polity import PolityMemberRow
from aerona.domain.enums.demography import MartialStyle
from aerona.domain.enums.military import UnitKind
from aerona.engine.context import TickContext
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules

KINDS = frozenset(kind.value for kind in UnitKind)


def power(spec: UnitSpec) -> int:
    return spec.melee + spec.missile + spec.defence


def weights_of(template: ArmyTemplateRow) -> dict[UnitKind, int]:
    return {UnitKind(key): int(value) for key, value in sorted(template.composition.items()) if key in KINDS and int(value) > 0}


def blend(rules: Rules, plan: Mapping[UnitKind, float], weights: Mapping[UnitKind, int]) -> dict[UnitKind, float]:
    if not weights:
        return dict(plan)
    share = rules.army_depth.template_share / PERCENT
    planned = sum(plan.values()) or 1.0
    drawn = sum(weights.values())
    found = {kind: value / planned * (1 - share) for kind, value in plan.items()}
    for kind, weight in weights.items():
        found[kind] = found.get(kind, 0.0) + share * weight / drawn
    return found


async def realm_template(ctx: TickContext, community_id: int) -> ArmyTemplateRow | None:
    return await realm_template_of(ctx.session, community_id)


async def realm_template_of(session: AsyncSession, community_id: int) -> ArmyTemplateRow | None:
    realms = select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == community_id)
    return await session.scalar(
        select(ArmyTemplateRow)
        .where((ArmyTemplateRow.polity_entity_id == community_id) | ArmyTemplateRow.polity_entity_id.in_(realms), ArmyTemplateRow.active.is_(True))
        .order_by(ArmyTemplateRow.obsolete, ArmyTemplateRow.id)
        .limit(1)
    )


def upgrades(weights: Mapping[UnitKind, int], doctrine: MartialStyle, allowed: set[UnitKind]) -> dict[UnitKind, UnitKind]:
    preferred = set(STYLE_UNITS.get(doctrine.value, ()))
    found: dict[UnitKind, UnitKind] = {}
    for kind in weights:
        spec = UNITS[kind]
        better = [
            other
            for other in sorted(allowed)
            if other not in weights
            and other not in found.values()
            and UNITS[other].family is spec.family
            and UNITS[other].branch is not None
            and power(UNITS[other]) > power(spec)
        ]
        if better:
            found[kind] = max(better, key=lambda other: (other in preferred, power(UNITS[other]), other.value))
    return found


async def seat_of(ctx: TickContext, polity_id: int) -> EntityRow | None:
    members = [
        await living_entity(ctx.session, member)
        for member in await ctx.session.scalars(select(PolityMemberRow.member_entity_id).where(PolityMemberRow.polity_entity_id == polity_id))
    ]
    living = [member for member in members if member is not None]
    return max(living, key=lambda member: (stat(member, "population") or 0, -member.id)) if living else None
