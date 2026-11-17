from collections.abc import Awaitable, Callable, Mapping

from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.unions import PartnerScope, UnionPurpose
from aerona.engine.context import TickContext
from aerona.engine.cycles.lineage import union_of
from aerona.engine.primitives.stats import stat_or
from aerona.engine.relations.book import relation
from aerona.engine.unions.customs import faith_of, scope_key

Pull = Callable[[TickContext, EntityRow, EntityRow, int], Awaitable[float]]


async def alliance(ctx: TickContext, _mortal: EntityRow, _other: EntityRow, prestige: int) -> float:
    return prestige * ctx.rules.kinship.purpose_pull_pct / PERCENT


async def status(ctx: TickContext, mortal: EntityRow, other: EntityRow, _prestige: int) -> float:
    return float(ctx.rules.kinship.purpose_bonus) if other.social_class is mortal.social_class else 0.0


async def faith(ctx: TickContext, mortal: EntityRow, other: EntityRow, _prestige: int) -> float:
    shared = await faith_of(ctx.session, mortal.id) == await faith_of(ctx.session, other.id)
    return float(ctx.rules.kinship.purpose_bonus) if shared else 0.0


async def kinship(ctx: TickContext, mortal: EntityRow, other: EntityRow, _prestige: int) -> float:
    shared = await scope_key(ctx.session, mortal, PartnerScope.PEOPLE) == await scope_key(ctx.session, other, PartnerScope.PEOPLE)
    return float(ctx.rules.kinship.purpose_bonus) if shared else 0.0


async def love(ctx: TickContext, mortal: EntityRow, other: EntityRow, _prestige: int) -> float:
    view = await relation(ctx.session, mortal.id, other.id)
    return view.friendship * ctx.rules.kinship.purpose_pull_pct / PERCENT if view is not None else 0.0


async def labour(ctx: TickContext, _mortal: EntityRow, other: EntityRow, _prestige: int) -> float:
    return stat_or(other, "strength", 0) * ctx.rules.kinship.purpose_pull_pct / PERCENT


async def inheritance(ctx: TickContext, _mortal: EntityRow, other: EntityRow, _prestige: int) -> float:
    return stat_or(other, "wealth", 0) * ctx.rules.kinship.purpose_pull_pct / PERCENT


PURPOSES: Mapping[UnionPurpose, Pull] = total(
    UnionPurpose,
    {
        UnionPurpose.KINSHIP: kinship,
        UnionPurpose.ALLIANCE: alliance,
        UnionPurpose.INHERITANCE: inheritance,
        UnionPurpose.LOVE: love,
        UnionPurpose.FAITH: faith,
        UnionPurpose.LABOUR: labour,
        UnionPurpose.STATUS: status,
    },
)


async def purpose_gain(ctx: TickContext, mortal: EntityRow, other: EntityRow, prestige: int) -> float:
    custom = await union_of(ctx.session, mortal)
    return await PURPOSES[custom.purpose](ctx, mortal, other, prestige) if custom is not None else 0.0
