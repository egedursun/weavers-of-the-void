from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.epochs import EpochRunRow
from aerona.db.tables.lore import ThreadRow
from aerona.db.tables.meta import ImageRow, NotificationRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.chronicle import ThreadStatus
from aerona.domain.enums.son import SonStatus
from aerona.engine.gods.mortal_opportunities import mortal_opportunities
from aerona.engine.gods.opportunities import CreatorHints, creator_hints, son_opportunities
from aerona.engine.primitives.manual import manual_context
from aerona.prompts.contexts.opportunities import CreatorOpportunitiesContext, MortalOpportunity, SonOpportunity
from aerona.rules.registry import Rules
from aerona.services.gods.context import require


@dataclass(frozen=True)
class PlayerHints:
    creator: CreatorHints
    sons_waiting: tuple[str, ...]
    sons_without_orders: tuple[str, ...]
    sleeping_sons: tuple[str, ...]
    dead_sons: tuple[str, ...]
    open_threads: int
    sons_without_image: int
    unread_notifications: int
    epoch_in_progress: bool


async def son_lines(session: AsyncSession, rules: Rules, son_id: int) -> list[SonOpportunity]:
    ctx = await manual_context(session, "son_opportunities", rules)
    son = require(await session.get(SonRow, son_id), "son")
    return await son_opportunities(session, rules, son, ctx.epoch)


async def mortal_lines(session: AsyncSession, rules: Rules, entity_id: int) -> list[MortalOpportunity]:
    return await mortal_opportunities(session, rules, require(await session.get(EntityRow, entity_id), "record"))


async def creator_context(session: AsyncSession, rules: Rules) -> CreatorOpportunitiesContext:
    ctx = await manual_context(session, "creator_opportunities", rules)
    hints = await creator_hints(session, rules, ctx.epoch)
    return CreatorOpportunitiesContext(
        rules=rules,
        unanswered_prayers=hints.unanswered_prayers,
        unclaimed_count=len(hints.unclaimed),
        unclaimed_examples=list(hints.unclaimed[: rules.opportunities.list_narrow]),
        rebel_sons=list(hints.rebel_sons),
        fading_sons=list(hints.fading_sons),
        doom=hints.doom,
        doom_threshold=hints.doom_threshold,
        godless_worlds=list(hints.godless_worlds),
        stale_threads=hints.stale_threads,
        essence=hints.essence,
    )


async def player_hints(session: AsyncSession, rules: Rules) -> PlayerHints:
    ctx = await manual_context(session, "player_hints", rules)
    sons = list(await session.scalars(select(SonRow).order_by(SonRow.id)))
    active = [son for son in sons if son.status is SonStatus.ACTIVE]
    pictured = set(await session.scalars(select(ImageRow.target_node_id)))
    run = await session.get(EpochRunRow, ctx.epoch)
    return PlayerHints(
        creator=await creator_hints(session, rules, ctx.epoch),
        sons_waiting=tuple(son.name for son in active if son.last_acted_epoch < ctx.epoch),
        sons_without_orders=tuple(son.name for son in active if not son.standing_order),
        sleeping_sons=tuple(son.name for son in sons if son.status is SonStatus.ASLEEP),
        dead_sons=tuple(son.name for son in sons if son.status is SonStatus.DEAD),
        open_threads=int(await session.scalar(select(func.count(ThreadRow.id)).where(ThreadRow.status == ThreadStatus.OPEN)) or 0),
        sons_without_image=sum(1 for son in sons if son.id not in pictured),
        unread_notifications=int(await session.scalar(select(func.count(NotificationRow.id)).where(NotificationRow.is_read.is_(False))) or 0),
        epoch_in_progress=run is not None and run.started and not run.finished,
    )
