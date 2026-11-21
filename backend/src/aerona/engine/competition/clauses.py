from sqlalchemy import func, select

from aerona.constants.units import PERCENT
from aerona.db.tables.made import CompanyPresenceRow
from aerona.domain.enums.competition import CompetitionClause
from aerona.domain.enums.polity import LawKind
from aerona.engine.context import TickContext
from aerona.engine.factions.companies import realm_of
from aerona.engine.polity.laws import law_param
from aerona.engine.primitives.numbers import round_half_up


async def captured_share(ctx: TickContext, realm_id: int) -> int:
    found = await ctx.session.scalar(select(func.max(CompanyPresenceRow.influence)).where(CompanyPresenceRow.polity_entity_id == realm_id))
    return int(found or 0)


async def clause_strength(ctx: TickContext, place_id: int, clause: CompetitionClause) -> int:
    value = await law_param(ctx.session, place_id, LawKind.COMPETITION_LAW, clause.value)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        return 0
    realm = await realm_of(ctx, place_id)
    capture = await captured_share(ctx, realm) if realm is not None else 0
    return round_half_up(value * (PERCENT - capture) / PERCENT)
