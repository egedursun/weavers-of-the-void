from collections.abc import Awaitable, Callable, Mapping

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.tables.factions import FactionMembershipRow, FactionProfileRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.powers import PowerRow, PowerSourceRow
from aerona.db.tables.urban import OrderLawRow
from aerona.db.write_guard import held
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.powers import SourceAccess
from aerona.domain.enums.urban import OrderLaw
from aerona.engine.context import TickContext
from aerona.engine.primitives.numbers import clamp_int, clamp_percent

SKILL_TOP = 100
LawEffect = Callable[[TickContext, FactionProfileRow, OrderLawRow, list[FactionMembershipRow]], Awaitable[None]]


async def outer_dealers(ctx: TickContext, members: list[FactionMembershipRow]) -> list[int]:
    ids = [member.mortal_entity_id for member in members]
    bonded = select(PowerSourceRow.id).where(PowerSourceRow.access == SourceAccess.BONDED)
    rows = await ctx.session.scalars(select(PowerRow.holder_node_id).where(PowerRow.holder_node_id.in_(ids), PowerRow.source_id.in_(bonded)).distinct())
    return sorted(set(rows))


async def no_effect(_ctx: TickContext, _profile: FactionProfileRow, _law: OrderLawRow, _members: list[FactionMembershipRow]) -> None:
    return None


async def share_discoveries(ctx: TickContext, _profile: FactionProfileRow, law: OrderLawRow, members: list[FactionMembershipRow]) -> None:
    ids = [member.mortal_entity_id for member in members if not held(member.mortal_entity_id)]
    rows = list(
        await ctx.session.scalars(
            select(SkillRow).where(SkillRow.holder_node_id.in_(ids), SkillRow.skill == SkillKind.SPELLCRAFT, SkillRow.subject_node_id.is_(None))
        )
    )
    if len(rows) < 2:
        return
    best = max(row.level for row in rows)
    step = max(1, ctx.rules.magical_orders.share_step * law.strength // PERCENT)
    for row in rows:
        if row.level < best:
            row.level = clamp_int(min(best, row.level + step), 0, SKILL_TOP)
            row.peak = max(row.peak, row.level)


async def keep_secrecy(ctx: TickContext, profile: FactionProfileRow, law: OrderLawRow, _members: list[FactionMembershipRow]) -> None:
    if "secrecy" in profile.locked or profile.secrecy >= law.strength:
        return
    profile.secrecy = clamp_percent(min(law.strength, profile.secrecy + ctx.rules.magical_orders.secrecy_step))


LAW_EFFECTS: Mapping[OrderLaw, LawEffect] = total(
    OrderLaw,
    {
        OrderLaw.SPARE_MEMBERS: no_effect,
        OrderLaw.NO_OUTER_DEALINGS: no_effect,
        OrderLaw.SHARE_DISCOVERIES: share_discoveries,
        OrderLaw.KEEP_SECRECY: keep_secrecy,
    },
)


async def keep_law(ctx: TickContext, profile: FactionProfileRow, law: OrderLawRow, members: list[FactionMembershipRow]) -> None:
    if not held(profile.faction_entity_id):
        await LAW_EFFECTS[law.law](ctx, profile, law, members)
