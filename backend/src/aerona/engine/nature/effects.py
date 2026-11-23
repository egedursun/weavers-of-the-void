from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.demography import PeopleBiologyRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.nature import Thermoregulation
from aerona.engine.context import TickContext
from aerona.engine.nature.seasons import activity, band_at, softened
from aerona.engine.nature.senses import sense_holder, sense_score
from aerona.rules.registry import Rules


async def folk_warmth(session: AsyncSession, node_id: int | None) -> Thermoregulation:
    holder = await sense_holder(session, node_id)
    biology = await session.get(PeopleBiologyRow, holder) if holder is not None else None
    return biology.thermoregulation if biology is not None else Thermoregulation.ENDOTHERM


async def cold_work(ctx: TickContext, community: EntityRow) -> float:
    warmth = await folk_warmth(ctx.session, community.id)
    if warmth is Thermoregulation.ENDOTHERM:
        return 1.0
    band = await band_at(ctx.session, ctx.rules, ctx.epoch, community.id)
    return softened(min(1.0, activity(ctx.rules, warmth, band)), ctx.rules.thermoregulation.labour_pct)


async def cold_war(ctx: TickContext, community: EntityRow, place_id: int | None) -> float:
    warmth = await folk_warmth(ctx.session, community.id)
    if warmth is Thermoregulation.ENDOTHERM:
        return 1.0
    band = await band_at(ctx.session, ctx.rules, ctx.epoch, place_id)
    return softened(activity(ctx.rules, warmth, band), ctx.rules.thermoregulation.winter_war_pct)


async def sensed(session: AsyncSession, rules: Rules, node_id: int | None, purpose: str, share_pct: int) -> float:
    return await sense_score(session, rules, node_id, purpose) * share_pct / PERCENT
