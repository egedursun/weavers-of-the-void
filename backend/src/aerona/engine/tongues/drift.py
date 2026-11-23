from sqlalchemy import select

from aerona.catalog.tongues import SOCIOLECTS
from aerona.constants.units import PERCENT
from aerona.db.tables.couplings import SociolectRow
from aerona.db.tables.culture import LanguageStandingRow
from aerona.db.tables.tongues import LanguagePolicyRow
from aerona.domain.enums.tongues import LanguagePolicy
from aerona.engine.context import TickContext


async def drift_scale(ctx: TickContext, language_id: int) -> float:
    table = ctx.rules.tongues
    lifted = sum(
        int(getattr(table, SOCIOLECTS[row.kind].drift_rule)) * row.salience / PERCENT
        for row in await ctx.session.scalars(
            select(SociolectRow).where(SociolectRow.language_entity_id == language_id, SociolectRow.faded_epoch.is_(None)).order_by(SociolectRow.id)
        )
    )
    academy = await ctx.session.scalar(
        select(LanguagePolicyRow.strength)
        .where(LanguagePolicyRow.language_entity_id == language_id, LanguagePolicyRow.policy == LanguagePolicy.STANDARDISED)
        .order_by(LanguagePolicyRow.strength.desc())
        .limit(1)
    )
    standing = await ctx.session.get(LanguageStandingRow, language_id)
    fixed = max(academy or 0, standing.standardisation if standing is not None and academy is not None else 0)
    return (1 + lifted / PERCENT) * (1 - table.standard_drift_cut_pct * fixed / PERCENT / PERCENT)
