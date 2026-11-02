from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.repositories.worlds import WorldRepository
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import LegendaryQuestRow, ThreadRow
from aerona.db.tables.routes import JourneyRow, RouteRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.chronicle import ChronicleKind, LegendaryQuestKind, LegendaryQuestOutcome, ThreadStatus
from aerona.domain.enums.entity import EngineKind, EntityStatus, EntityType
from aerona.domain.enums.limits import PERCENT_MAX
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.son import SonStatus
from aerona.domain.enums.travel import JourneyStatus
from aerona.domain.enums.world import EXTINGUISHED_STAR_TYPES, Discovery
from aerona.engine.context import TickContext
from aerona.engine.cosmos.routes import forgotten_world_ids, world_name
from aerona.engine.notes import note
from aerona.engine.primitives.doom import advance_doom

Q = LegendaryQuestKind
QUEST_NAMES: dict[LegendaryQuestKind, str] = {
    Q.DEAD_STAR: "Rekindle the dead star",
    Q.SEALED_GATE: "Reopen the sealed gate",
    Q.ARCHIVE: "Reach the Cosmic Archive",
    Q.EXPEL_OUTER: "Expel the one from outside",
}


@dataclass(frozen=True)
class QuestTarget:
    text: str
    star_id: int | None = None
    route_id: int | None = None
    entity_id: int | None = None
    prior: tuple[int, ...] = ()


async def live_archive(session: AsyncSession) -> EntityRow | None:
    forgotten = await forgotten_world_ids(session)
    statement = select(EntityRow).where(EntityRow.engine_kind == EngineKind.COSMIC_ARCHIVE, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    return next((item for item in await session.scalars(statement) if item.world_id not in forgotten), None)


async def _arrived_at(session: AsyncSession, world_id: int) -> list[int]:
    statement = select(JourneyRow.id).where(JourneyRow.destination_world_id == world_id, JourneyRow.status == JourneyStatus.ARRIVED)
    return list(await session.scalars(statement.order_by(JourneyRow.id)))


async def _dead_star_target(session: AsyncSession) -> QuestTarget:
    star: StarRow | None = await session.scalar(select(StarRow).where(StarRow.star_type.in_(list(EXTINGUISHED_STAR_TYPES))).order_by(StarRow.id).limit(1))
    if star is None:
        raise ValidationFailedError("There is no dead star.")
    return QuestTarget(f"{star.name} must be rekindled.", star_id=star.id)


async def _sealed_gate_target(session: AsyncSession) -> QuestTarget:
    forgotten = await forgotten_world_ids(session)
    statement = (
        select(RouteRow)
        .where(RouteRow.active.is_(False), RouteRow.temp_closed_until_epoch.is_(None), RouteRow.temp_open_until_epoch.is_(None))
        .order_by(RouteRow.id)
    )
    route = next((item for item in await session.scalars(statement) if item.world_a_id not in forgotten and item.world_b_id not in forgotten), None)
    if route is None:
        raise ValidationFailedError("There is no sealed route.")
    first, second = await world_name(session, route.world_a_id), await world_name(session, route.world_b_id)
    return QuestTarget(f"The sealed route between {first} and {second} must be reopened.", route_id=route.id)


async def _archive_target(session: AsyncSession) -> QuestTarget:
    archive = await live_archive(session)
    if archive is None:
        raise ValidationFailedError("There is no Cosmic Archive (or its world was forgotten).")
    world = await world_name(session, archive.world_id)
    prior = tuple(await _arrived_at(session, archive.world_id))
    return QuestTarget(f"A people must pass between the worlds and reach the Cosmic Archive in {world}.", entity_id=archive.id, prior=prior)


async def _outer_target(session: AsyncSession) -> QuestTarget:
    statement = select(EntityRow).where(EntityRow.entity_type == EntityType.OUTER_BEING, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    being: EntityRow | None = await session.scalar(statement.limit(1))
    if being is None:
        raise ValidationFailedError("Nothing from outside exists.")
    return QuestTarget(f"The thing that entered {await world_name(session, being.world_id)} must be pushed outside.", entity_id=being.id)


async def quest_target(session: AsyncSession, kind: LegendaryQuestKind) -> QuestTarget:
    readers = {Q.DEAD_STAR: _dead_star_target, Q.SEALED_GATE: _sealed_gate_target, Q.ARCHIVE: _archive_target, Q.EXPEL_OUTER: _outer_target}
    return await readers[kind](session)


async def open_quest(ctx: TickContext, kind: LegendaryQuestKind, by: str, opened_by: ActorKind) -> LegendaryQuestRow:
    target = await quest_target(ctx.session, kind)
    name = QUEST_NAMES[kind]
    thread = ThreadRow(
        epoch=ctx.epoch,
        text=f"LEGENDARY QUEST — {name}: {target.text} Those who succeed will enter the epic of the cosmos; if it fails the price will be heavy.",
        status=ThreadStatus.OPEN,
    )
    ctx.session.add(thread)
    await ctx.session.flush()
    quest = LegendaryQuestRow(
        thread_id=thread.id,
        kind=kind,
        target_star_id=target.star_id,
        target_route_id=target.route_id,
        target_entity_id=target.entity_id,
        opened_by=opened_by,
        opened_epoch=ctx.epoch,
        deadline_epoch=ctx.epoch + ctx.rules.beyond.expedition_epochs,
        prior_journey_ids=list(target.prior),
    )
    ctx.session.add(quest)
    await ctx.chronicle(ChronicleKind.LEGENDARY_QUEST, f"{by} opened a legendary quest: {name}. {target.text}", template_key="beyond.quest_opened")
    await ctx.session.flush()
    return quest


async def open_quests(session: AsyncSession) -> list[tuple[LegendaryQuestRow, ThreadRow]]:
    statement = (
        select(LegendaryQuestRow, ThreadRow)
        .join(ThreadRow, ThreadRow.id == LegendaryQuestRow.thread_id)
        .where(ThreadRow.status == ThreadStatus.OPEN, LegendaryQuestRow.outcome.is_(None))
        .order_by(LegendaryQuestRow.thread_id)
    )
    return [(quest, thread) for quest, thread in await session.execute(statement)]


async def _invalid_reason(session: AsyncSession, quest: LegendaryQuestRow) -> str | None:
    if quest.kind is Q.DEAD_STAR and (quest.target_star_id is None or await session.get(StarRow, quest.target_star_id) is None):
        return "the target star was removed from the sky"
    if quest.kind is Q.SEALED_GATE and (quest.target_route_id is None or await session.get(RouteRow, quest.target_route_id) is None):
        return "the sealed route no longer exists"
    if quest.kind is Q.ARCHIVE and await live_archive(session) is None:
        return "the Cosmic Archive vanished or was buried in mist"
    return None


async def _completed(session: AsyncSession, quest: LegendaryQuestRow) -> bool:
    if quest.kind is Q.DEAD_STAR:
        star = await session.get(StarRow, quest.target_star_id) if quest.target_star_id is not None else None
        return star is not None and star.star_type not in EXTINGUISHED_STAR_TYPES
    if quest.kind is Q.SEALED_GATE:
        route = await session.get(RouteRow, quest.target_route_id) if quest.target_route_id is not None else None
        return route is not None and route.active and route.temp_open_until_epoch is None
    if quest.kind is Q.ARCHIVE:
        archive = await live_archive(session)
        return archive is not None and bool(set(await _arrived_at(session, archive.world_id)) - set(quest.prior_journey_ids))
    target = await session.get(EntityRow, quest.target_entity_id) if quest.target_entity_id is not None else None
    return target is None or target.status is not EntityStatus.CANON


def _close(thread: ThreadRow, quest: LegendaryQuestRow, epoch: int, outcome: LegendaryQuestOutcome, closing: str) -> None:
    thread.status = ThreadStatus.CLOSED
    thread.closed_epoch = epoch
    thread.closing_text = closing
    quest.outcome = outcome


async def _reward(ctx: TickContext) -> None:
    beyond = ctx.rules.beyond
    for son in await ctx.session.scalars(select(SonRow).where(SonRow.status == SonStatus.ACTIVE)):
        son.fame += beyond.expedition_renown
    creator = await CosmosRepository(ctx.session).creator()
    if creator is not None:
        creator.essence += beyond.expedition_reward_essence
    await advance_doom(ctx.session, ctx.rules, -beyond.expedition_reward_apocalypse_push)


async def _punish(ctx: TickContext) -> None:
    beyond = ctx.rules.beyond
    await advance_doom(ctx.session, ctx.rules, beyond.expedition_fail_apocalypse)
    for world in await WorldRepository(ctx.session).all_worlds():
        world.leakage = min(PERCENT_MAX, world.leakage + beyond.expedition_fail_leak)


async def settle_quest(ctx: TickContext, quest: LegendaryQuestRow, thread: ThreadRow) -> LegendaryQuestOutcome | None:
    name = QUEST_NAMES[quest.kind]
    reason = await _invalid_reason(ctx.session, quest)
    if reason is not None:
        _close(thread, quest, ctx.epoch, LegendaryQuestOutcome.INVALIDATED, f"Legendary quest fell: {reason}.")
        text = f"Legendary quest fell: {name}. Its target vanished ({reason}); no one was rewarded, nor did the cosmos pay a price."
        await ctx.chronicle(ChronicleKind.LEGENDARY_QUEST, text, template_key="beyond.quest_invalid")
        return LegendaryQuestOutcome.INVALIDATED
    if await _completed(ctx.session, quest):
        _close(thread, quest, ctx.epoch, LegendaryQuestOutcome.COMPLETED, "completed successfully")
        await _reward(ctx)
        text = f"Legendary quest completed: {name}. The cosmos took a breath; doom receded, the gods' fame grew."
        await ctx.chronicle(ChronicleKind.LEGENDARY_QUEST, text, template_key="beyond.quest_completed")
        return LegendaryQuestOutcome.COMPLETED
    if ctx.epoch >= quest.deadline_epoch:
        _close(thread, quest, ctx.epoch, LegendaryQuestOutcome.FAILED, "failed")
        await _punish(ctx)
        text = f"Legendary quest failed: {name}. The cosmos pays the price: doom came closer, something leaked into the worlds."
        await ctx.chronicle(ChronicleKind.LEGENDARY_QUEST, text, template_key="beyond.quest_failed")
        return LegendaryQuestOutcome.FAILED
    return None


async def legendary_quests(ctx: TickContext) -> None:
    beyond = ctx.rules.beyond
    rng = ctx.rng("quests")
    current = await open_quests(ctx.session)
    if len(current) < beyond.max_concurrent_expeditions and rng.chance(beyond.fate_expedition_chance):
        for kind in rng.shuffled(list(LegendaryQuestKind)):
            try:
                await open_quest(ctx, kind, "Fate", ActorKind.FATE)
            except ValidationFailedError:
                continue
            await note(ctx, "Fate opened a new legendary quest.", key="beyond.fate_quest")
            break
    for quest, thread in await open_quests(ctx.session):
        await settle_quest(ctx, quest, thread)
    await ctx.session.flush()


async def abandon_quest(ctx: TickContext, thread_id: int, by: str) -> str:
    quest = await ctx.session.get(LegendaryQuestRow, thread_id)
    thread = await ctx.session.get(ThreadRow, thread_id)
    if quest is None or thread is None or thread.status is not ThreadStatus.OPEN:
        raise NotFoundError("No such open legendary quest.")
    _close(thread, quest, ctx.epoch, LegendaryQuestOutcome.INVALIDATED, f"abandoned by {by}")
    text = f"{by} let the legendary quest go: {QUEST_NAMES[quest.kind]}. No one was rewarded, nor did the cosmos pay a price."
    await ctx.chronicle(ChronicleKind.LEGENDARY_QUEST, text, template_key="beyond.quest_abandoned")
    return text


async def open_quest_count(session: AsyncSession) -> int:
    statement = (
        select(func.count())
        .select_from(LegendaryQuestRow)
        .join(ThreadRow, ThreadRow.id == LegendaryQuestRow.thread_id)
        .where(ThreadRow.status == ThreadStatus.OPEN)
    )
    return int(await session.scalar(statement) or 0)


async def worlds_known(session: AsyncSession) -> int:
    return int(await session.scalar(select(func.count()).select_from(WorldRow).where(WorldRow.discovery != Discovery.FORGOTTEN)) or 0)
