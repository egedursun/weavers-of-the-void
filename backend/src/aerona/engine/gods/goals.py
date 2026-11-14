import logging
import math
from collections import Counter
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from sqlalchemy import Select, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog import god_lines
from aerona.catalog.achievements import ACHIEVEMENTS
from aerona.catalog.scenarios import SCENARIOS, doom_limit
from aerona.constants.units import PERCENT
from aerona.core.errors import AeronaError
from aerona.core.grammar import several
from aerona.db.repositories.notifications import NotificationDraft, NotificationRepository, fitted_texts, raw_title
from aerona.db.tables.agency import ActionRecordRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import ChronicleRow, LegendaryQuestRow, MessageRow
from aerona.db.tables.meta import AchievementRow, ScenarioRow, ScoreRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.routes import HorizonIntuitionRow, JourneyRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import MessageIntent
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ChronicleKind, LegendaryQuestOutcome, NotificationCategory
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.meta import AchievementKey, ScenarioKey, ScenarioStatus, ScoreComponent
from aerona.domain.enums.node import NodeKind
from aerona.domain.enums.son import SonStatus
from aerona.domain.enums.travel import HorizonStatus, JourneyStatus
from aerona.domain.enums.world import DARK_STAR_TYPES, EXTINGUISHED_STAR_TYPES, Discovery, StarType
from aerona.domain.models.records import ScoreBreakdown
from aerona.engine.context import TickContext
from aerona.engine.gods.queries import canon_count, cosmos_row, world_count
from aerona.engine.gods.stats import Trait, trait_or
from aerona.engine.gods.worship import creator_node_id
from aerona.engine.primitives.faith import patron_node
from aerona.engine.primitives.queries import canon
from aerona.engine.services.war import ongoing_war_count
from aerona.rules.registry import Rules

logger = logging.getLogger(__name__)
COMMUNITY_TIER_TYPES = (EntityType.PEOPLE, EntityType.SETTLEMENT)
GOAL_SEVERITY = 3
ACHIEVEMENT_SEVERITY = 2
MEASURE_FAILURES = (AeronaError, SQLAlchemyError, ValueError, ArithmeticError, LookupError)


@dataclass(frozen=True)
class ScenarioProgress:
    percent: int
    text: str
    done: bool = False
    failed: bool = False


@dataclass(frozen=True)
class GoalsEpochResult:
    completed: tuple[ScenarioKey, ...] = ()
    failed: tuple[ScenarioKey, ...] = ()
    earned: tuple[AchievementKey, ...] = ()
    score: ScoreBreakdown = field(default_factory=ScoreBreakdown)


def _percent(value: float) -> int:
    return int(max(0, min(PERCENT, round(value))))


async def star_count(session: AsyncSession, types: frozenset[StarType] | None = None) -> int:
    statement = select(func.count(StarRow.id))
    if types is not None:
        statement = statement.where(StarRow.star_type.in_(list(types)))
    return int(await session.scalar(statement) or 0)


async def max_entity_id(session: AsyncSession) -> int:
    return int(await session.scalar(select(func.max(EntityRow.id))) or 0)


async def max_chronicle_id(session: AsyncSession) -> int:
    return int(await session.scalar(select(func.max(ChronicleRow.id))) or 0)


async def scenario_baseline(session: AsyncSession, row: ScenarioRow) -> None:
    if row.key is ScenarioKey.LOST_STAR:
        row.baseline_count = await star_count(session, frozenset({StarType.REBORN_STAR}))
    elif row.key is ScenarioKey.LOYAL_PANTHEON:
        rebels = await session.scalars(select(SonRow.id).where(SonRow.rebel.is_(True), SonRow.status != SonStatus.DEAD))
        row.baseline_rebel_ids = list(rebels)
        row.baseline_chronicle_id = await max_chronicle_id(session)
    elif row.key is ScenarioKey.NEW_HORIZONS:
        row.baseline_entity_id = await max_entity_id(session)


async def scenario_epoch_end(session: AsyncSession, row: ScenarioRow) -> None:
    if row.key is ScenarioKey.LONG_PEACE:
        row.counter = 0 if await ongoing_war_count(session) else row.counter + 1


async def _one_faith(session: AsyncSession, rules: Rules) -> ScenarioProgress:
    peoples = await canon(session, [EntityType.PEOPLE])
    gods = Counter([god for god in [await patron_node(session, people) for people in peoples] if god is not None])
    most = max(gods.values(), default=0)
    total = len(peoples)
    return ScenarioProgress(
        _percent(most / total * PERCENT if total else 0),
        f"{most}/{several(total, 'people', 'peoples')} worship the same god",
        done=total >= rules.goals.one_faith_min_peoples and most == total,
    )


async def _many_worlds(session: AsyncSession, rules: Rules) -> ScenarioProgress:
    target = rules.goals.inhabited_worlds
    worlds = list(await session.scalars(select(WorldRow.id).where(WorldRow.discovery != Discovery.FORGOTTEN)))
    statement = select(EntityRow.world_id).where(EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON)
    inhabited = len(set(await session.scalars(statement)) & set(worlds))
    return ScenarioProgress(
        _percent(inhabited / target * PERCENT), f"{inhabited}/{target} worlds inhabited ({several(len(worlds), 'world', 'worlds')})", done=inhabited >= target
    )


async def _loyal_pantheon(session: AsyncSession, rules: Rules, row: ScenarioRow, epoch: int) -> ScenarioProgress:
    goals = rules.goals
    rebels = set(await session.scalars(select(SonRow.id).where(SonRow.rebel.is_(True), SonRow.status != SonStatus.DEAD)))
    new_rebels = rebels - set(row.baseline_rebel_ids)
    declared = select(func.count(ChronicleRow.id)).where(ChronicleRow.template_key == god_lines.REBELLION.key)
    if row.baseline_chronicle_id is not None:
        declared = declared.where(ChronicleRow.id > row.baseline_chronicle_id)
    else:
        declared = declared.where(ChronicleRow.epoch > row.start_epoch)
    if new_rebels or int(await session.scalar(declared) or 0):
        return ScenarioProgress(0, "A son rebelled; the pantheon is not loyal.", failed=True)
    elapsed = epoch - row.start_epoch
    loyalties = list(await session.scalars(select(SonRow.loyalty).where(SonRow.status == SonStatus.ACTIVE)))
    loyal = sum(1 for value in loyalties if value > goals.loyal_min_loyalty)
    return ScenarioProgress(
        _percent(elapsed / goals.loyal_epochs * PERCENT),
        f"{elapsed}/{goals.loyal_epochs} epochs without rebellion · {loyal}/{len(loyalties)} loyal",
        done=elapsed >= goals.loyal_epochs and loyal == len(loyalties),
    )


async def _new_horizons(session: AsyncSession, rules: Rules, row: ScenarioRow) -> ScenarioProgress:
    goals = rules.goals
    baseline = row.baseline_entity_id or 0

    async def lands(entity_type: EntityType) -> int:
        statement = select(func.count(EntityRow.id)).where(
            EntityRow.id > baseline, EntityRow.entity_type == entity_type, EntityRow.status.in_([EntityStatus.CANON, EntityStatus.DEAD])
        )
        return int(await session.scalar(statement) or 0)

    regions = await lands(EntityType.REGION)
    total = regions + await lands(EntityType.PLACE)
    region_share = regions / goals.horizon_regions if goals.horizon_regions else 1.0
    return ScenarioProgress(
        _percent(min(total / goals.horizon_lands, region_share) * PERCENT),
        f"{total}/{goals.horizon_lands} new lands · {regions}/{goals.horizon_regions} regions",
        done=total >= goals.horizon_lands and regions >= goals.horizon_regions,
    )


async def _doom_far(session: AsyncSession, rules: Rules, row: ScenarioRow, epoch: int) -> ScenarioProgress:
    cosmos = await cosmos_row(session)
    clock = cosmos.doom_clock if cosmos is not None else 0
    threshold = max(1, rules.balance.apocalypse_threshold)
    if clock >= doom_limit(rules):
        return ScenarioProgress(0, f"Doomsday clock reached {clock}/{threshold}.", failed=True)
    elapsed = epoch - row.start_epoch
    duration = rules.goals.keep_apocalypse_away_epochs
    return ScenarioProgress(_percent(elapsed / duration * PERCENT), f"{elapsed}/{duration} epochs · clock {clock}/{threshold}", done=elapsed >= duration)


async def _lost_star(session: AsyncSession, rules: Rules, row: ScenarioRow, epoch: int) -> ScenarioProgress:
    reborn = await star_count(session, frozenset({StarType.REBORN_STAR}))
    dead = await star_count(session, EXTINGUISHED_STAR_TYPES & DARK_STAR_TYPES)
    if not reborn and not dead:
        return ScenarioProgress(0, "There is no dead star in the cosmos yet; one must die first.")
    done = reborn > (row.baseline_count or 0)
    return ScenarioProgress(PERCENT if done else 0, f"{dead} dead stars are waiting", done=done)


async def _long_peace(session: AsyncSession, rules: Rules, row: ScenarioRow, epoch: int) -> ScenarioProgress:
    wars = await ongoing_war_count(session)
    if wars:
        return ScenarioProgress(0, f"{wars} wars ongoing; counter reset")
    goal = rules.goals.peace_epochs
    return ScenarioProgress(_percent(row.counter / goal * PERCENT), f"{row.counter}/{goal} peace epochs", done=row.counter >= goal)


async def _cosmic_power(session: AsyncSession, rules: Rules, row: ScenarioRow, epoch: int) -> ScenarioProgress:
    goal = rules.goals.cosmic_stage
    best = max([entity.civ_tier or 0 for entity in await canon(session, COMMUNITY_TIER_TYPES)], default=0)
    return ScenarioProgress(_percent(best / goal * PERCENT), f"highest tier {best}/{goal}", done=best >= goal)


async def _one_faith_measure(session: AsyncSession, rules: Rules, row: ScenarioRow, epoch: int) -> ScenarioProgress:
    return await _one_faith(session, rules)


async def _many_worlds_measure(session: AsyncSession, rules: Rules, row: ScenarioRow, epoch: int) -> ScenarioProgress:
    return await _many_worlds(session, rules)


async def _new_horizons_measure(session: AsyncSession, rules: Rules, row: ScenarioRow, epoch: int) -> ScenarioProgress:
    return await _new_horizons(session, rules, row)


Measure = Callable[[AsyncSession, Rules, ScenarioRow, int], Awaitable[ScenarioProgress]]
MEASURES: dict[ScenarioKey, Measure] = {
    ScenarioKey.DOOM_FAR: _doom_far,
    ScenarioKey.ONE_FAITH: _one_faith_measure,
    ScenarioKey.LOST_STAR: _lost_star,
    ScenarioKey.MANY_WORLDS: _many_worlds_measure,
    ScenarioKey.LONG_PEACE: _long_peace,
    ScenarioKey.COSMIC_POWER: _cosmic_power,
    ScenarioKey.LOYAL_PANTHEON: _loyal_pantheon,
    ScenarioKey.NEW_HORIZONS: _new_horizons_measure,
}


async def measure(session: AsyncSession, rules: Rules, row: ScenarioRow, epoch: int) -> ScenarioProgress:
    return await MEASURES[row.key](session, rules, row, epoch)


async def safe_measure(session: AsyncSession, rules: Rules, row: ScenarioRow, epoch: int) -> ScenarioProgress:
    try:
        async with session.begin_nested():
            return await measure(session, rules, row, epoch)
    except MEASURE_FAILURES as error:
        logger.warning("Scenario %s could not be measured: %s", row.id, error)
        return ScenarioProgress(0, f"could not be measured: {error}")


async def _count(session: AsyncSession, statement: Select[int]) -> int:
    return int(await session.scalar(statement) or 0)


async def peoples_population(session: AsyncSession) -> int:
    return sum(max(0, trait_or(people, Trait.POPULATION, 0)) for people in await canon(session, [EntityType.PEOPLE]))


async def _creator_count(session: AsyncSession, build: Callable[[int], Select[int]]) -> int:
    creator_id = await creator_node_id(session)
    return await _count(session, build(creator_id)) if creator_id is not None else 0


def _prayers_to(creator_id: int) -> Select[int]:
    return (
        select(func.count(MessageRow.id))
        .join(NodeRow, NodeRow.id == MessageRow.sender_node_id)
        .where(MessageRow.recipient_node_id == creator_id, MessageRow.intent == MessageIntent.PRAYER, NodeRow.kind == NodeKind.ENTITY)
    )


def _cult_of(creator_id: int) -> Select[int]:
    return (
        select(func.count(BondRow.id))
        .join(NodeRow, NodeRow.id == BondRow.source_node_id)
        .where(BondRow.target_node_id == creator_id, BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE, NodeRow.kind == NodeKind.ENTITY)
    )


async def _weapons_silent(session: AsyncSession, rules: Rules) -> bool:
    return await canon_count(session, [EntityType.PEOPLE]) >= rules.goals.ach_peace_min_peoples and await ongoing_war_count(session) == 0


Condition = Callable[[AsyncSession, Rules, int], Awaitable[bool]]


async def _at_least(value: Awaitable[int], threshold: int) -> bool:
    return await value >= threshold


async def _any(value: Awaitable[int]) -> bool:
    return await value > 0


async def _flag(value: bool) -> bool:
    return value


CONDITIONS: dict[AchievementKey, Condition] = {
    AchievementKey.SECOND_SKY: lambda session, rules, epoch: _at_least(world_count(session), rules.goals.ach_worlds),
    AchievementKey.CONSTELLATION: lambda session, rules, epoch: _at_least(star_count(session), rules.goals.ach_stars),
    AchievementKey.PROPHECY_FULFILLED: lambda session, rules, epoch: _any(
        _count(session, select(func.count(EntityRow.id)).where(EntityRow.entity_type == EntityType.PROPHECY, EntityRow.status == EntityStatus.FULFILLED))
    ),
    AchievementKey.RETURN_FROM_DEATH: lambda session, rules, epoch: _any(
        _count(session, select(func.count(ChronicleRow.id)).where(ChronicleRow.template_key == god_lines.SON_RESURRECTED.key))
    ),
    AchievementKey.FATHERS_HAND: lambda session, rules, epoch: _any(
        _count(session, select(func.count(ActionRecordRow.id)).where(ActionRecordRow.kind == ActionKind.SUPPRESS_REBELLION))
    ),
    AchievementKey.BABEL: lambda session, rules, epoch: _at_least(canon_count(session, [EntityType.LANGUAGE]), rules.goals.ach_languages),
    AchievementKey.CROWDED_WORLD: lambda session, rules, epoch: _at_least(peoples_population(session), rules.goals.ach_population),
    AchievementKey.FIRST_PRAYER: lambda session, rules, epoch: _any(_creator_count(session, _prayers_to)),
    AchievementKey.CREATORS_CULT: lambda session, rules, epoch: _at_least(_creator_count(session, _cult_of), rules.goals.ach_cult),
    AchievementKey.INTERSTELLAR_TRAVELLER: lambda session, rules, epoch: _any(
        _count(session, select(func.count(JourneyRow.id)).where(JourneyRow.status == JourneyStatus.ARRIVED))
    ),
    AchievementKey.SAGA_COMPLETED: lambda session, rules, epoch: _any(
        _count(session, select(func.count(LegendaryQuestRow.thread_id)).where(LegendaryQuestRow.outcome == LegendaryQuestOutcome.COMPLETED))
    ),
    AchievementKey.GOD_OF_EPOCHS: lambda session, rules, epoch: _flag(epoch >= rules.goals.ach_epochs),
    AchievementKey.ANCIENT: lambda session, rules, epoch: _flag(epoch >= rules.goals.ach_ancient_epochs),
    AchievementKey.CROWDED_PANTHEON: lambda session, rules, epoch: _at_least(
        _count(session, select(func.count(SonRow.id)).where(SonRow.status != SonStatus.DEAD)), rules.goals.ach_sons
    ),
    AchievementKey.FIRST_EXPLORERS: lambda session, rules, epoch: _any(
        _count(session, select(func.count(BondRow.id)).where(BondRow.kind == BondKind.DISCOVERED))
    ),
    AchievementKey.SENSED_WORLD: lambda session, rules, epoch: _any(
        _count(session, select(func.count(HorizonIntuitionRow.id)).where(HorizonIntuitionRow.status == HorizonStatus.BORN))
    ),
    AchievementKey.WEAPONS_SILENT: lambda session, rules, epoch: _weapons_silent(session, rules),
}


async def achieved(session: AsyncSession, rules: Rules, key: AchievementKey, epoch: int) -> bool:
    return await CONDITIONS[key](session, rules, epoch)


async def score(session: AsyncSession, rules: Rules) -> ScoreBreakdown:
    goals = rules.goals
    cosmos = await cosmos_row(session)
    clock = cosmos.doom_clock if cosmos is not None else 0
    earned = list(await session.scalars(select(AchievementRow.key)))
    awarded = set(await session.scalars(select(ScenarioRow.key).where(ScenarioRow.status == ScenarioStatus.COMPLETED, ScenarioRow.points_awarded.is_(True))))
    peoples = await canon(session, [EntityType.PEOPLE])
    parts = {
        ScoreComponent.POPULATION: round(math.log10(1 + await peoples_population(session)) * goals.score_population),
        ScoreComponent.DIVERSITY: min(goals.score_diversity_cap, await canon_count(session)),
        ScoreComponent.LANGUAGES: await canon_count(session, [EntityType.LANGUAGE]) * goals.score_language,
        ScoreComponent.WORLDS: await world_count(session) * goals.score_world,
        ScoreComponent.CIVILIZATION: max([people.civ_tier or 0 for people in peoples], default=0) * goals.score_stage,
        ScoreComponent.DOOMSDAY: -round(clock / max(1, rules.balance.apocalypse_threshold) * goals.score_apocalypse_penalty),
        ScoreComponent.ACHIEVEMENTS: sum(ACHIEVEMENTS[key].points(rules) for key in earned),
        ScoreComponent.SCENARIOS: sum(SCENARIOS[key].points(rules) for key in awarded),
    }
    return ScoreBreakdown(parts=parts)


async def store_score(session: AsyncSession, epoch: int, breakdown: ScoreBreakdown) -> ScoreRow:
    row = await session.get(ScoreRow, epoch)
    if row is None:
        row = ScoreRow(epoch=epoch, total=breakdown.total, breakdown=breakdown)
        session.add(row)
    else:
        row.total = breakdown.total
        row.breakdown = breakdown
    await session.flush()
    return row


async def notify(session: AsyncSession, epoch: int, title: str, body: str | None, severity: int) -> None:
    raw = raw_title(NotificationCategory.ACHIEVEMENT, title, body)
    shown, detail = fitted_texts(raw, raw, body)
    await NotificationRepository(session).add(
        NotificationDraft(category=NotificationCategory.ACHIEVEMENT, title=shown, body=detail, severity=severity, epoch=epoch)
    )


async def finish_scenario(ctx: TickContext, row: ScenarioRow, progress: ScenarioProgress) -> None:
    spec = SCENARIOS[row.key]
    name = spec.name(ctx.rules)
    row.status = ScenarioStatus.COMPLETED if progress.done else ScenarioStatus.FAILED
    row.end_epoch = ctx.epoch
    row.result = progress.text
    if progress.done:
        earlier = select(func.count(ScenarioRow.id)).where(ScenarioRow.key == row.key, ScenarioRow.points_awarded.is_(True), ScenarioRow.id != row.id)
        row.points_awarded = not int(await ctx.session.scalar(earlier) or 0)
    line = god_lines.GOAL_ACHIEVED if progress.done else god_lines.GOAL_LOST
    text = line.render(name=name, detail=progress.text)
    await ctx.chronicle(ChronicleKind.CREATOR_HAND, text, template_key=line.key)
    await notify(ctx.session, ctx.epoch, text, None, GOAL_SEVERITY)


async def epoch_end_goals(ctx: TickContext) -> GoalsEpochResult:
    running = await running_scenarios(ctx.session)
    for row in running:
        await scenario_epoch_end(ctx.session, row)
    return await evaluate_goals(ctx)


async def running_scenarios(session: AsyncSession) -> list[ScenarioRow]:
    return list(await session.scalars(select(ScenarioRow).where(ScenarioRow.status == ScenarioStatus.RUNNING).order_by(ScenarioRow.id)))


async def evaluate_goals(ctx: TickContext) -> GoalsEpochResult:
    session = ctx.session
    completed: list[ScenarioKey] = []
    failed: list[ScenarioKey] = []
    for row in await running_scenarios(session):
        progress = await safe_measure(session, ctx.rules, row, ctx.epoch)
        if progress.done or progress.failed:
            await finish_scenario(ctx, row, progress)
            (completed if progress.done else failed).append(row.key)
    earned_keys = set(await session.scalars(select(AchievementRow.key)))
    earned: list[AchievementKey] = []
    for key, spec in ACHIEVEMENTS.items():
        if key in earned_keys:
            continue
        try:
            async with session.begin_nested():
                reached = await achieved(session, ctx.rules, key, ctx.epoch)
        except MEASURE_FAILURES as error:
            logger.warning("Achievement %s could not be checked: %s", key, error)
            continue
        if reached:
            session.add(AchievementRow(key=key, epoch=ctx.epoch))
            await notify(session, ctx.epoch, god_lines.ACHIEVEMENT_TITLE.format(name=spec.name(ctx.rules)), spec.description(ctx.rules), ACHIEVEMENT_SEVERITY)
            earned.append(key)
    await session.flush()
    breakdown = await score(session, ctx.rules)
    await store_score(session, ctx.epoch, breakdown)
    ctx.count("achievements", len(earned))
    return GoalsEpochResult(tuple(completed), tuple(failed), tuple(earned), breakdown)
