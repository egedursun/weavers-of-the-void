from collections.abc import Mapping
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.quests import LEGENDARY_AIMS, OBSTACLE_EPOCHS, REWARD_WORDS, quest_name
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.grammar import an, spoken
from aerona.core.total import total
from aerona.db.record_context import current_scope
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.repositories.worlds import WorldRepository
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.horror import HorrorEventRow
from aerona.db.tables.lore import LegendaryQuestRow, ThreadRow
from aerona.db.tables.routes import JourneyRow, RouteRow
from aerona.db.tables.sons import SonRow
from aerona.db.write_guard import held
from aerona.domain.enums.chronicle import LegendaryQuestOutcome, ThreadStatus
from aerona.domain.enums.entity import EngineKind, EntityStatus, EntityType
from aerona.domain.enums.limits import PERCENT_MAX
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.quests import QuestAim, QuestObstacle, QuestReward, QuestTargetKind
from aerona.domain.enums.records import StepAction, StepOutcome
from aerona.domain.enums.son import SonStatus
from aerona.domain.enums.travel import JourneyStatus
from aerona.domain.enums.world import EXTINGUISHED_STAR_TYPES, Discovery
from aerona.engine.context import TickContext
from aerona.engine.cosmos.routes import forgotten_world_ids, world_name
from aerona.engine.primitives.doom import advance_doom
from aerona.engine.recording.record import StepDraft, record
from aerona.engine.recording.terms import explaining

T = QuestTargetKind


@dataclass(frozen=True)
class LegendaryDraft:
    aim: QuestAim
    target_kind: QuestTargetKind
    obstacle: QuestObstacle = QuestObstacle.DISTANCE
    reward: QuestReward = QuestReward.RENOWN


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
    return QuestTarget(f"the star {star.name}, whose light is out", star_id=star.id)


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
    return QuestTarget(f"the sealed route between {first} and {second}", route_id=route.id)


async def _archive_target(session: AsyncSession) -> QuestTarget:
    archive = await live_archive(session)
    if archive is None:
        raise ValidationFailedError("There is no Cosmic Archive (or its world was forgotten).")
    world = await world_name(session, archive.world_id)
    prior = tuple(await _arrived_at(session, archive.world_id))
    return QuestTarget(f"the Cosmic Archive in {world}, which a people must reach by passing between the worlds", entity_id=archive.id, prior=prior)


async def _outer_target(session: AsyncSession) -> QuestTarget:
    statement = select(EntityRow).where(EntityRow.entity_type == EntityType.OUTER_BEING, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    being: EntityRow | None = await session.scalar(statement.limit(1))
    if being is None:
        raise ValidationFailedError("Nothing from outside exists.")
    return QuestTarget(f"{being.name}, which entered {await world_name(session, being.world_id)} from outside the cosmos", entity_id=being.id)


TARGET_FINDERS = {T.STAR: _dead_star_target, T.ROUTE: _sealed_gate_target, T.KNOWLEDGE: _archive_target, T.OUTER_BEING: _outer_target}


async def quest_target(session: AsyncSession, target_kind: QuestTargetKind) -> QuestTarget:
    finder = TARGET_FINDERS.get(target_kind)
    if finder is None:
        raise ValidationFailedError("A legendary quest turns on a star, a route, knowledge or a being from outside.")
    return await finder(session)


def quest_target_node(quest: LegendaryQuestRow) -> int | None:
    return quest.target_entity_id if quest.target_entity_id is not None else quest.target_star_id


def legendary_name(quest: LegendaryQuestRow) -> str:
    return quest_name(quest.aim, quest.target_kind)


async def open_quest(ctx: TickContext, draft: LegendaryDraft, by: str, opened_by: ActorKind) -> LegendaryQuestRow:
    if draft.aim not in LEGENDARY_AIMS.get(draft.target_kind, ()):
        raise ValidationFailedError(f"A legendary quest cannot {spoken(draft.aim)} {an(spoken(draft.target_kind))}.")
    target = await quest_target(ctx.session, draft.target_kind)
    name = quest_name(draft.aim, draft.target_kind)
    if opened_by is ActorKind.FATE and held(target.entity_id, target.star_id):
        raise ValidationFailedError(f"{name} would turn on a held thing.")
    thread = ThreadRow(
        epoch=ctx.epoch,
        text=f"Legendary quest: {name}, {target.text}. Reward: {REWARD_WORDS[draft.reward]}; obstacle: {spoken(draft.obstacle)}.",
        status=ThreadStatus.OPEN,
    )
    ctx.session.add(thread)
    await ctx.session.flush()
    quest = LegendaryQuestRow(
        thread_id=thread.id,
        aim=draft.aim,
        target_kind=draft.target_kind,
        obstacle=draft.obstacle,
        reward=draft.reward,
        locked=[],
        target_star_id=target.star_id,
        target_route_id=target.route_id,
        target_entity_id=target.entity_id,
        opened_by=opened_by,
        opened_epoch=ctx.epoch,
        deadline_epoch=ctx.epoch + ctx.rules.beyond.expedition_epochs + OBSTACLE_EPOCHS[draft.obstacle],
        prior_journey_ids=list(target.prior),
    )
    ctx.session.add(quest)
    scope = current_scope()
    await record(
        ctx,
        "beyond.quest_opened",
        roles={
            IncidentRole.AUTHORITY: scope.actor_node_id if scope is not None and opened_by is not ActorKind.FATE else None,
            IncidentRole.TARGET: target.entity_id if target.entity_id is not None else target.star_id,
        },
        facts={
            "aim": draft.aim,
            "target_kind": draft.target_kind,
            "obstacle": draft.obstacle,
            "reward": draft.reward,
            "opened_by": opened_by,
            "deadline_epoch": quest.deadline_epoch,
        },
    )
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
    if quest.target_kind is T.STAR and (quest.target_star_id is None or await session.get(StarRow, quest.target_star_id) is None):
        return "the target star was removed from the sky"
    if quest.target_kind is T.ROUTE and (quest.target_route_id is None or await session.get(RouteRow, quest.target_route_id) is None):
        return "the sealed route no longer exists"
    if quest.target_kind is T.KNOWLEDGE and await live_archive(session) is None:
        return "the Cosmic Archive was lost"
    return None


async def route_open(session: AsyncSession, quest: LegendaryQuestRow) -> bool:
    route = await session.get(RouteRow, quest.target_route_id) if quest.target_route_id is not None else None
    return route is not None and route.active and route.temp_open_until_epoch is None


async def being_stirred(session: AsyncSession, quest: LegendaryQuestRow) -> bool:
    if quest.target_entity_id is None:
        return False
    found = await session.scalar(
        select(HorrorEventRow.id).where(HorrorEventRow.source_node_id == quest.target_entity_id, HorrorEventRow.epoch >= quest.opened_epoch).limit(1)
    )
    return found is not None


async def _bound(session: AsyncSession, quest: LegendaryQuestRow, epoch: int) -> bool | None:
    broken = await route_open(session, quest) if quest.target_kind is T.ROUTE else await being_stirred(session, quest)
    if broken:
        return False
    return True if epoch >= quest.deadline_epoch else None


async def _completed(session: AsyncSession, quest: LegendaryQuestRow) -> bool:
    if quest.target_kind is T.STAR:
        star = await session.get(StarRow, quest.target_star_id) if quest.target_star_id is not None else None
        return star is not None and star.star_type not in EXTINGUISHED_STAR_TYPES
    if quest.target_kind is T.ROUTE:
        return await route_open(session, quest)
    if quest.target_kind is T.KNOWLEDGE:
        archive = await live_archive(session)
        return archive is not None and bool(set(await _arrived_at(session, archive.world_id)) - set(quest.prior_journey_ids))
    target = await session.get(EntityRow, quest.target_entity_id) if quest.target_entity_id is not None else None
    return target is None or target.status is not EntityStatus.CANON


REWARD_WEIGHT: Mapping[QuestReward, tuple[int, int, int, int]] = total(
    QuestReward,
    {
        QuestReward.RENOWN: (2, 1, 1, 0),
        QuestReward.POWER: (1, 2, 1, 0),
        QuestReward.KNOWLEDGE: (1, 1, 1, 1),
        QuestReward.ITEM: (1, 2, 0, 0),
        QuestReward.STANDING: (2, 0, 1, 0),
        QuestReward.OFFICE: (2, 1, 0, 0),
        QuestReward.CURE: (1, 0, 1, 1),
        QuestReward.PEACE: (1, 1, 2, 0),
    },
)


def _close(thread: ThreadRow, quest: LegendaryQuestRow, epoch: int, outcome: LegendaryQuestOutcome, closing: str) -> None:
    thread.status = ThreadStatus.CLOSED
    thread.closed_epoch = epoch
    thread.closing_text = closing
    quest.outcome = outcome


async def _reward(ctx: TickContext, reward: QuestReward) -> None:
    beyond = ctx.rules.beyond
    weight = REWARD_WEIGHT[reward]
    for son in await ctx.session.scalars(select(SonRow).where(SonRow.status == SonStatus.ACTIVE)):
        if not held(son.id):
            son.fame += beyond.expedition_renown * weight[0]
    creator = await CosmosRepository(ctx.session).creator()
    if creator is not None:
        creator.essence += beyond.expedition_reward_essence * weight[1]
    await advance_doom(ctx.session, ctx.rules, -beyond.expedition_reward_apocalypse_push * weight[2])
    if weight[3]:
        for world in await WorldRepository(ctx.session).all_worlds():
            if not held(world.id):
                world.leakage = max(0, world.leakage - beyond.expedition_fail_leak)


async def _punish(ctx: TickContext) -> None:
    beyond = ctx.rules.beyond
    await advance_doom(ctx.session, ctx.rules, beyond.expedition_fail_apocalypse)
    for world in await WorldRepository(ctx.session).all_worlds():
        world.leakage = min(PERCENT_MAX, world.leakage + beyond.expedition_fail_leak)


async def succeeded(ctx: TickContext, quest: LegendaryQuestRow) -> bool | None:
    if quest.aim is QuestAim.BIND:
        return await _bound(ctx.session, quest, ctx.epoch)
    if await _completed(ctx.session, quest):
        return True
    return False if ctx.epoch >= quest.deadline_epoch else None


async def settle_quest(ctx: TickContext, quest: LegendaryQuestRow, thread: ThreadRow) -> LegendaryQuestOutcome | None:
    reason = await _invalid_reason(ctx.session, quest)
    if reason is not None:
        _close(thread, quest, ctx.epoch, LegendaryQuestOutcome.INVALIDATED, f"Legendary quest fell: {reason}.")
        await record(
            ctx, "beyond.quest_invalid", roles={IncidentRole.TARGET: quest_target_node(quest)}, facts={"aim": quest.aim, "target_kind": quest.target_kind}
        )
        return LegendaryQuestOutcome.INVALIDATED
    result = await succeeded(ctx, quest)
    if result:
        _close(thread, quest, ctx.epoch, LegendaryQuestOutcome.COMPLETED, "completed successfully")
        with explaining():
            await _reward(ctx, quest.reward)
            await record(
                ctx,
                "beyond.quest_completed",
                roles={IncidentRole.TARGET: quest_target_node(quest)},
                facts={
                    "aim": quest.aim,
                    "target_kind": quest.target_kind,
                    "reward": quest.reward,
                    "doom_change": -ctx.rules.beyond.expedition_reward_apocalypse_push * REWARD_WEIGHT[quest.reward][2],
                },
                steps=(StepDraft(StepAction.COMPLETE, target=quest_target_node(quest), outcome=StepOutcome.SUCCESS),),
            )
        return LegendaryQuestOutcome.COMPLETED
    if result is False:
        _close(thread, quest, ctx.epoch, LegendaryQuestOutcome.FAILED, "failed")
        with explaining():
            await _punish(ctx)
            await record(
                ctx,
                "beyond.quest_failed",
                roles={IncidentRole.TARGET: quest_target_node(quest)},
                facts={
                    "aim": quest.aim,
                    "target_kind": quest.target_kind,
                    "doom_change": ctx.rules.beyond.expedition_fail_apocalypse,
                    "leak_gain": ctx.rules.beyond.expedition_fail_leak,
                },
            )
        return LegendaryQuestOutcome.FAILED
    return None


async def legendary_quests(ctx: TickContext) -> None:
    beyond = ctx.rules.beyond
    rng = ctx.rng("quests")
    current = await open_quests(ctx.session)
    if len(current) < beyond.max_concurrent_expeditions and rng.chance(beyond.fate_expedition_chance):
        pairs = [(target, aim) for target, aims in LEGENDARY_AIMS.items() for aim in aims]
        for target_kind, aim in rng.shuffled(pairs):
            draft = LegendaryDraft(aim, target_kind, rng.pick(list(QuestObstacle)), rng.pick(list(QuestReward)))
            try:
                opened = await open_quest(ctx, draft, "Fate", ActorKind.FATE)
            except ValidationFailedError:
                continue
            await record(
                ctx, "beyond.fate_quest", roles={IncidentRole.TARGET: quest_target_node(opened)}, facts={"aim": draft.aim, "target_kind": draft.target_kind}
            )
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
    scope = current_scope()
    written = await record(
        ctx,
        "beyond.quest_abandoned",
        roles={IncidentRole.AUTHORITY: scope.actor_node_id if scope is not None else None, IncidentRole.TARGET: quest_target_node(quest)},
        facts={"aim": quest.aim, "target_kind": quest.target_kind},
        steps=(StepDraft(StepAction.ABANDON, actor=scope.actor_node_id if scope is not None else None),),
    )
    return written.text


async def worlds_known(session: AsyncSession) -> int:
    return int(await session.scalar(select(func.count()).select_from(WorldRow).where(WorldRow.discovery != Discovery.FORGOTTEN)) or 0)
