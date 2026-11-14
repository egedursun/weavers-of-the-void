from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sacred import DivinationRow
from aerona.domain.enums.sacred import DivinationQuestion, OmenVerdict
from aerona.engine.context import TickContext
from aerona.engine.sacred.places import realm_for, ruler_of


async def omen_for(ctx: TickContext, client_id: int | None, question: DivinationQuestion) -> OmenVerdict | None:
    if client_id is None:
        return None
    row = await ctx.session.scalar(
        select(DivinationRow)
        .where(
            DivinationRow.client_entity_id == client_id, DivinationRow.question == question, DivinationRow.epoch == ctx.epoch, DivinationRow.heeded.is_(True)
        )
        .order_by(DivinationRow.id.desc())
        .limit(1)
    )
    return row.verdict if row is not None else None


async def war_forbidden(ctx: TickContext, realm_id: int) -> bool:
    return await omen_for(ctx, await ruler_of(ctx.session, realm_id), DivinationQuestion.WAR) is OmenVerdict.INAUSPICIOUS


async def battle_omen(ctx: TickContext, community: EntityRow) -> float:
    realm = await realm_for(ctx.session, community)
    verdict = await omen_for(ctx, await ruler_of(ctx.session, realm), DivinationQuestion.BATTLE)
    edge = ctx.rules.divination.battle_edge_pct / PERCENT
    return edge if verdict is OmenVerdict.AUSPICIOUS else -edge if verdict is OmenVerdict.INAUSPICIOUS else 0.0
