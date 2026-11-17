from collections.abc import Sequence

from aerona.core.errors import ConflictError, NotFoundError
from aerona.db.repositories.worlds import WorldRepository
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.foreign_god import ForeignGodStatus
from aerona.domain.enums.son import SonStatus
from aerona.engine.context import TickContext
from aerona.engine.cosmos.foreign_gods import GodWarResult, resolve_god_war
from aerona.engine.divine.decrees import truce_in_force
from aerona.engine.divine.foreign import pact_between

FIGHTING_GOD_STATUSES = frozenset({ForeignGodStatus.AWAKE, ForeignGodStatus.ASLEEP, ForeignGodStatus.DEFEATED})
DEFAULT_REASON = "to protect their worshippers and temples"


async def foreign_god_war(
    ctx: TickContext, son_id: int, god_id: int, reason: str = DEFAULT_REASON, allies: Sequence[SonRow] = (), *, key: str = "pantheon.god_war"
) -> GodWarResult:
    son = await ctx.session.get(SonRow, son_id)
    god = await ctx.session.get(ForeignGodRow, god_id)
    if son is None:
        raise NotFoundError("No such son.")
    if god is None:
        raise NotFoundError("No such foreign god.")
    if son.status is not SonStatus.ACTIVE:
        raise ConflictError(f"{son.name} is in no state to wage war.")
    if god.status not in FIGHTING_GOD_STATUSES:
        raise ConflictError(f"{god.name} is beyond any war.")
    if son.current_world_id is not None and not await WorldRepository(ctx.session).connected(son.current_world_id, god.world_id):
        raise ConflictError(f"{son.name} cannot reach the world of {god.name}.")
    if await pact_between(ctx, son.id, god.id) is not None:
        raise ConflictError(f"{son.name} and {god.name} are bound by a divine pact.")
    if await truce_in_force(ctx):
        raise ConflictError("A cosmic truce of the council forbids war between gods.")
    result = await resolve_god_war(ctx, son, god, reason, allies=allies, key=key)
    ctx.count("god_wars")
    return result
