import logging
import math
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog import god_lines
from aerona.catalog.achievements import ACHIEVEMENTS
from aerona.catalog.goal_metrics import METRICS
from aerona.catalog.scenarios import SCENARIOS, custom_description, custom_title, doom_limit, epochs
from aerona.constants.units import PERCENT
from aerona.core.errors import AeronaError
from aerona.core.grammar import several
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.repositories.notifications import NotificationDraft, NotificationRepository, fitted_texts, raw_title
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.meta import AchievementRow, ScenarioRow, ScoreRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.chronicle import ChronicleKind, NotificationCategory
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.meta import ACHIEVEMENT_TIERS, AchievementKey, GoalBasis, GoalComparator, GoalMetric, ScenarioKey, ScenarioStatus, ScoreComponent
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.son import SonStatus
from aerona.domain.models.records import ScoreBreakdown
from aerona.engine.context import TickContext
from aerona.engine.gods.metrics import MetricReader, faith_counts, measure_metric
from aerona.engine.gods.queries import canon_count, cosmos_row
from aerona.engine.recording.record import record
from aerona.engine.services.war import ongoing_war_count
from aerona.rules.registry import Rules

logger = logging.getLogger(__name__)
GOAL_SEVERITY = 3
ACHIEVEMENT_SEVERITY = 2
MEASURE_FAILURES = (AeronaError, SQLAlchemyError, ValueError, ArithmeticError, LookupError)
M = GoalMetric


@dataclass(frozen=True)
class ScenarioProgress:
    percent: int
    text: str
    value: int | None = None
    done: bool = False
    failed: bool = False


@dataclass(frozen=True)
class GoalsEpochResult:
    completed: tuple[ScenarioKey, ...] = ()
    failed: tuple[ScenarioKey, ...] = ()
    earned: tuple[tuple[AchievementKey, int], ...] = ()
    score: ScoreBreakdown = field(default_factory=ScoreBreakdown)


def _percent(value: float) -> int:
    return int(max(0, min(PERCENT, round(value))))


def scenario_metrics(row: ScenarioRow) -> tuple[GoalMetric, ...]:
    if row.key is ScenarioKey.CUSTOM:
        return (row.metric,) if row.metric is not None else ()
    return SCENARIOS[row.key].metrics


def scenario_basis(row: ScenarioRow) -> GoalBasis:
    if row.key is ScenarioKey.CUSTOM:
        return row.basis or GoalBasis.TOTAL
    return SCENARIOS[row.key].basis


def scenario_comparator(row: ScenarioRow) -> GoalComparator:
    if row.key is ScenarioKey.CUSTOM and row.comparator is not None:
        return row.comparator
    return GoalComparator.AT_LEAST


def scenario_name(row: ScenarioRow) -> str:
    if row.key is ScenarioKey.CUSTOM:
        if row.title:
            return row.title
        if row.metric is None:
            return SCENARIOS[row.key].name(row.target)
        return custom_title(row.metric, scenario_comparator(row), scenario_basis(row), row.target)
    return SCENARIOS[row.key].name(row.target, row.tier)


def scenario_description(rules: Rules, row: ScenarioRow) -> str:
    if row.key is ScenarioKey.CUSTOM and row.metric is not None:
        return custom_description(row.metric, scenario_comparator(row), scenario_basis(row), row.target, row.hold_epochs)
    return SCENARIOS[row.key].description(rules, row.target)


async def metric_total(session: AsyncSession, rules: Rules, metrics: tuple[GoalMetric, ...], epoch: int) -> int:
    return sum([await measure_metric(session, rules, metric, epoch) for metric in metrics])


async def max_entity_id(session: AsyncSession) -> int:
    return int(await session.scalar(select(func.max(EntityRow.id))) or 0)


async def max_chronicle_id(session: AsyncSession) -> int:
    return int(await session.scalar(select(func.max(ChronicleRow.id))) or 0)


async def scenario_baseline(session: AsyncSession, rules: Rules, row: ScenarioRow, epoch: int) -> None:
    if row.key is ScenarioKey.LOYAL_PANTHEON:
        rebels = await session.scalars(select(SonRow.id).where(SonRow.rebel.is_(True), SonRow.status != SonStatus.DEAD))
        row.baseline_rebel_ids = list(rebels)
        row.baseline_chronicle_id = await max_chronicle_id(session)
    elif row.key is ScenarioKey.NEW_HORIZONS:
        row.baseline_entity_id = await max_entity_id(session)
    metrics = scenario_metrics(row)
    if metrics:
        row.baseline_value = await metric_total(session, rules, metrics, epoch)


async def goal_value(session: AsyncSession, rules: Rules, row: ScenarioRow, epoch: int) -> int:
    total = await metric_total(session, rules, scenario_metrics(row), epoch)
    return total - (row.baseline_value or 0) if scenario_basis(row) is GoalBasis.GAINED else total


def reached(row: ScenarioRow, value: int) -> bool:
    return value <= row.target if scenario_comparator(row) is GoalComparator.AT_MOST else value >= row.target


def toward(row: ScenarioRow, value: int) -> int:
    if reached(row, value):
        return PERCENT
    if scenario_comparator(row) is GoalComparator.AT_MOST:
        return _percent(row.target / value * PERCENT) if value > 0 else PERCENT
    return _percent(value / row.target * PERCENT) if row.target > 0 else PERCENT


def value_text(row: ScenarioRow, value: int) -> str:
    label = METRICS[scenario_metrics(row)[0]].label if len(scenario_metrics(row)) == 1 else "Measured"
    if scenario_basis(row) is GoalBasis.GAINED:
        return f"{label}: +{value}/{row.target} since the goal began"
    if scenario_comparator(row) is GoalComparator.AT_MOST:
        return f"{label}: {value} (at most {row.target})"
    return f"{label}: {value}/{row.target}"


async def scenario_epoch_end(session: AsyncSession, rules: Rules, row: ScenarioRow, epoch: int) -> None:
    if row.held:
        if row.deadline_epoch is not None:
            row.deadline_epoch += 1
        return
    if row.key is ScenarioKey.LONG_PEACE:
        row.counter = 0 if await ongoing_war_count(session) else row.counter + 1
    elif row.key is ScenarioKey.CUSTOM and row.hold_epochs:
        row.counter = row.counter + 1 if reached(row, await goal_value(session, rules, row, epoch)) else 0


async def _metric_goal(session: AsyncSession, rules: Rules, row: ScenarioRow, epoch: int) -> ScenarioProgress:
    value = await goal_value(session, rules, row, epoch)
    return ScenarioProgress(toward(row, value), value_text(row, value), value=value, done=reached(row, value))


async def _custom(session: AsyncSession, rules: Rules, row: ScenarioRow, epoch: int) -> ScenarioProgress:
    value = await goal_value(session, rules, row, epoch)
    if not row.hold_epochs:
        return ScenarioProgress(toward(row, value), value_text(row, value), value=value, done=reached(row, value))
    held_for = min(row.counter, row.hold_epochs)
    return ScenarioProgress(
        _percent(held_for / row.hold_epochs * PERCENT),
        f"{value_text(row, value)} · held {held_for}/{epochs(row.hold_epochs)}",
        value=value,
        done=row.counter >= row.hold_epochs,
    )


async def _one_faith(session: AsyncSession, rules: Rules, row: ScenarioRow, epoch: int) -> ScenarioProgress:
    most, total = await faith_counts(session)
    return ScenarioProgress(
        _percent(most / total * PERCENT if total else 0),
        f"{most}/{several(total, 'people', 'peoples')} worship the same god (at least {row.target})",
        value=most,
        done=total >= row.target and most == total,
    )


async def _loyal_pantheon(session: AsyncSession, rules: Rules, row: ScenarioRow, epoch: int) -> ScenarioProgress:
    goals = rules.goals
    rebels = set(await session.scalars(select(SonRow.id).where(SonRow.rebel.is_(True), SonRow.status != SonStatus.DEAD)))
    new_rebels = rebels - set(row.baseline_rebel_ids)
    declared = select(func.count(ChronicleRow.id)).where(ChronicleRow.template_key == "gods.power.rebellion_declared")
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
        _percent(elapsed / max(1, row.target) * PERCENT),
        f"{elapsed}/{epochs(row.target)} without rebellion · {loyal}/{len(loyalties)} loyal",
        value=elapsed,
        done=elapsed >= row.target and loyal == len(loyalties),
    )


async def _new_horizons(session: AsyncSession, rules: Rules, row: ScenarioRow, epoch: int) -> ScenarioProgress:
    baseline = row.baseline_entity_id or 0
    needed_regions = min(row.target, rules.goals.horizon_regions)

    async def lands(entity_type: EntityType) -> int:
        statement = select(func.count(EntityRow.id)).where(
            EntityRow.id > baseline, EntityRow.entity_type == entity_type, EntityRow.status.in_([EntityStatus.CANON, EntityStatus.DEAD])
        )
        return int(await session.scalar(statement) or 0)

    regions = await lands(EntityType.REGION)
    total = regions + await lands(EntityType.PLACE)
    region_share = regions / needed_regions if needed_regions else 1.0
    return ScenarioProgress(
        _percent(min(total / max(1, row.target), region_share) * PERCENT),
        f"{total}/{several(row.target, 'new land', 'new lands')} · {regions}/{several(needed_regions, 'region', 'regions')}",
        value=total,
        done=total >= row.target and regions >= needed_regions,
    )


async def _doom_far(session: AsyncSession, rules: Rules, row: ScenarioRow, epoch: int) -> ScenarioProgress:
    cosmos = await cosmos_row(session)
    clock = cosmos.doom_clock if cosmos is not None else 0
    threshold = max(1, rules.balance.apocalypse_threshold)
    if clock >= doom_limit(rules):
        return ScenarioProgress(0, f"Doomsday clock reached {clock}/{threshold}.", value=clock, failed=True)
    elapsed = epoch - row.start_epoch
    return ScenarioProgress(
        _percent(elapsed / max(1, row.target) * PERCENT),
        f"{elapsed}/{epochs(row.target)} · clock {clock}/{threshold}",
        value=elapsed,
        done=elapsed >= row.target,
    )


async def _lost_star(session: AsyncSession, rules: Rules, row: ScenarioRow, epoch: int) -> ScenarioProgress:
    progress = await _metric_goal(session, rules, row, epoch)
    if progress.done:
        return progress
    dead = await measure_metric(session, rules, M.DEAD_STARS, epoch)
    if not dead:
        return ScenarioProgress(progress.percent, "There is no dead star in the cosmos yet; one must die first.", value=progress.value)
    return ScenarioProgress(progress.percent, f"{progress.text} · {several(dead, 'dead star is', 'dead stars are')} waiting", value=progress.value)


async def _long_peace(session: AsyncSession, rules: Rules, row: ScenarioRow, epoch: int) -> ScenarioProgress:
    wars = await ongoing_war_count(session)
    if wars:
        return ScenarioProgress(0, f"{several(wars, 'war', 'wars')} ongoing; counter reset", value=0)
    return ScenarioProgress(
        _percent(row.counter / max(1, row.target) * PERCENT), f"{row.counter}/{row.target} peace epochs", value=row.counter, done=row.counter >= row.target
    )


Measure = Callable[[AsyncSession, Rules, ScenarioRow, int], Awaitable[ScenarioProgress]]
MEASURES: dict[ScenarioKey, Measure] = {
    ScenarioKey.DOOM_FAR: _doom_far,
    ScenarioKey.ONE_FAITH: _one_faith,
    ScenarioKey.LOST_STAR: _lost_star,
    ScenarioKey.MANY_WORLDS: _metric_goal,
    ScenarioKey.LONG_PEACE: _long_peace,
    ScenarioKey.COSMIC_POWER: _metric_goal,
    ScenarioKey.LOYAL_PANTHEON: _loyal_pantheon,
    ScenarioKey.NEW_HORIZONS: _new_horizons,
    ScenarioKey.GOLDEN_AGE: _metric_goal,
    ScenarioKey.AGE_OF_WONDERS: _metric_goal,
    ScenarioKey.BRIDGE_THE_GALAXIES: _metric_goal,
    ScenarioKey.AGE_OF_LEARNING: _metric_goal,
    ScenarioKey.TEEMING_LIFE: _metric_goal,
    ScenarioKey.CREATORS_FAITHFUL: _metric_goal,
    ScenarioKey.CUSTOM: _custom,
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


def with_deadline(rules: Rules, points: int, deadline_epoch: int | None) -> int:
    return round(points * (PERCENT + rules.goals.deadline_bonus_pct) / PERCENT) if deadline_epoch is not None else points


def preset_points(rules: Rules, key: ScenarioKey, target: int, deadline_epoch: int | None) -> int:
    spec = SCENARIOS[key]
    ratio = min(rules.goals.target_points_cap_pct / PERCENT, target / max(1, spec.default_target(rules)))
    return with_deadline(rules, round(spec.points(rules) * ratio), deadline_epoch)


def custom_points(rules: Rules, *, comparator: GoalComparator, basis: GoalBasis, start: int, target: int, hold_epochs: int, deadline_epoch: int | None) -> int:
    goals = rules.goals
    if basis is GoalBasis.GAINED:
        ratio = target / max(1, start)
    elif comparator is GoalComparator.AT_MOST:
        ratio = (start - target) / max(1, target) if start > target else 0.0
    else:
        ratio = (target - start) / max(1, start) if target > start else 0.0
    reach = round(goals.custom_points * min(goals.custom_ratio_cap_pct / PERCENT, ratio))
    return with_deadline(rules, reach + hold_epochs * goals.custom_hold_points, deadline_epoch)


def scenario_points(rules: Rules, row: ScenarioRow) -> int:
    if row.key is not ScenarioKey.CUSTOM:
        return preset_points(rules, row.key, row.target, row.deadline_epoch)
    return custom_points(
        rules,
        comparator=scenario_comparator(row),
        basis=scenario_basis(row),
        start=row.baseline_value or 0,
        target=row.target,
        hold_epochs=row.hold_epochs,
        deadline_epoch=row.deadline_epoch,
    )


async def completed_tiers(session: AsyncSession, key: ScenarioKey) -> int:
    statement = select(func.count(ScenarioRow.id)).where(ScenarioRow.key == key, ScenarioRow.status == ScenarioStatus.COMPLETED)
    return int(await session.scalar(statement) or 0)


async def best_earlier_points(session: AsyncSession, row: ScenarioRow) -> int:
    statement = select(func.max(ScenarioRow.points)).where(ScenarioRow.key == row.key, ScenarioRow.status == ScenarioStatus.COMPLETED, ScenarioRow.id != row.id)
    if row.key is ScenarioKey.CUSTOM:
        statement = statement.where(ScenarioRow.metric == row.metric)
    return int(await session.scalar(statement) or 0)


async def score(session: AsyncSession, rules: Rules, epoch: int = 0, reader: MetricReader | None = None) -> ScoreBreakdown:
    goals = rules.goals
    reader = reader or MetricReader(session, rules, epoch)
    cosmos = await cosmos_row(session)
    clock = cosmos.doom_clock if cosmos is not None else 0
    earned = list(await session.scalars(select(AchievementRow)))
    awarded = int(await session.scalar(select(func.sum(ScenarioRow.awarded_points)).where(ScenarioRow.status == ScenarioStatus.COMPLETED)) or 0)

    async def capped(per: int, cap: int, *metrics: GoalMetric) -> int:
        return min(cap, await reader.total(*metrics) * per)

    parts = {
        ScoreComponent.POPULATION: round(math.log10(1 + await reader.value(M.POPULATION)) * goals.score_population),
        ScoreComponent.DIVERSITY: min(goals.score_diversity_cap, await canon_count(session)),
        ScoreComponent.LANGUAGES: await reader.value(M.LANGUAGES) * goals.score_language,
        ScoreComponent.WORLDS: await reader.value(M.WORLDS) * goals.score_world,
        ScoreComponent.CIVILIZATION: await reader.value(M.HIGHEST_CIV_TIER) * goals.score_stage,
        ScoreComponent.LIFE: await capped(goals.score_life, goals.score_life_cap, M.SPECIES, M.BEASTS, M.SPIRITS),
        ScoreComponent.FAITH: await capped(goals.score_faith, goals.score_faith_cap, M.CULTS, M.CREATOR_WORSHIPPERS),
        ScoreComponent.CULTURE: await capped(goals.score_culture, goals.score_culture_cap, M.ARTWORKS, M.ART_FORMS, M.LEGENDS, M.TRADITIONS),
        ScoreComponent.KNOWLEDGE: await capped(goals.score_knowledge, goals.score_knowledge_cap, M.KNOWLEDGE, M.THEORIES),
        ScoreComponent.WONDERS: await capped(goals.score_wonder, goals.score_wonder_cap, M.WONDERS, M.MUSEUMS),
        ScoreComponent.SCALES: await capped(goals.score_scale, goals.score_scale_cap, M.GALAXIES, M.CLUSTERS, M.DIMENSIONS),
        ScoreComponent.EXPLORATION: await capped(goals.score_exploration, goals.score_exploration_cap, M.DISCOVERIES, M.ARRIVED_JOURNEYS),
        ScoreComponent.DOOMSDAY: -round(clock / max(1, rules.balance.apocalypse_threshold) * goals.score_apocalypse_penalty),
        ScoreComponent.ACHIEVEMENTS: sum(ACHIEVEMENTS[row.key].points(rules, row.tier) for row in earned),
        ScoreComponent.SCENARIOS: awarded,
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
    name = scenario_name(row)
    row.status = ScenarioStatus.COMPLETED if progress.done else ScenarioStatus.FAILED
    row.end_epoch = ctx.epoch
    row.result = progress.text
    if progress.done:
        row.awarded_points = max(0, row.points - await best_earlier_points(ctx.session, row))
    text = (
        await record(
            ctx,
            "gods.goals.achieved" if progress.done else "gods.goals.lost",
            roles={IncidentRole.ACTOR: creator.id if (creator := await CosmosRepository(ctx.session).creator()) is not None else None},
            facts={"name": name, "detail": progress.text},
            kind=ChronicleKind.CREATOR_HAND,
        )
    ).text
    await notify(ctx.session, ctx.epoch, text, None, GOAL_SEVERITY)


async def epoch_end_goals(ctx: TickContext) -> GoalsEpochResult:
    for row in await running_scenarios(ctx.session):
        await scenario_epoch_end(ctx.session, ctx.rules, row, ctx.epoch)
    return await evaluate_goals(ctx, closing=True)


async def running_scenarios(session: AsyncSession) -> list[ScenarioRow]:
    return list(await session.scalars(select(ScenarioRow).where(ScenarioRow.status == ScenarioStatus.RUNNING).order_by(ScenarioRow.id)))


def past_deadline(row: ScenarioRow, epoch: int, closing: bool) -> bool:
    if row.deadline_epoch is None:
        return False
    return epoch >= row.deadline_epoch if closing else epoch > row.deadline_epoch


async def evaluate_scenarios(ctx: TickContext, closing: bool) -> tuple[list[ScenarioKey], list[ScenarioKey]]:
    completed: list[ScenarioKey] = []
    failed: list[ScenarioKey] = []
    for row in await running_scenarios(ctx.session):
        if row.held:
            continue
        progress = await safe_measure(ctx.session, ctx.rules, row, ctx.epoch)
        if not (progress.done or progress.failed) and past_deadline(row, ctx.epoch, closing):
            progress = ScenarioProgress(
                progress.percent, f"The deadline of epoch {row.deadline_epoch} passed. {progress.text}", value=progress.value, failed=True
            )
        if progress.done or progress.failed:
            await finish_scenario(ctx, row, progress)
            (completed if progress.done else failed).append(row.key)
    return completed, failed


async def evaluate_achievements(ctx: TickContext, reader: MetricReader) -> list[tuple[AchievementKey, int]]:
    session = ctx.session
    have = {(row.key, row.tier) for row in await session.scalars(select(AchievementRow))}
    earned: list[tuple[AchievementKey, int]] = []
    for key, spec in ACHIEVEMENTS.items():
        if all((key, tier) in have for tier in ACHIEVEMENT_TIERS):
            continue
        try:
            async with session.begin_nested():
                value = await reader.value(spec.metric)
        except MEASURE_FAILURES as error:
            logger.warning("Achievement %s could not be checked: %s", key, error)
            continue
        for tier in ACHIEVEMENT_TIERS:
            if (key, tier) in have or value < spec.threshold(ctx.rules, tier):
                continue
            session.add(AchievementRow(key=key, tier=tier, epoch=ctx.epoch))
            await notify(session, ctx.epoch, god_lines.ACHIEVEMENT_TITLE.format(name=spec.name(tier)), spec.description(ctx.rules, tier), ACHIEVEMENT_SEVERITY)
            earned.append((key, tier))
    return earned


async def evaluate_goals(ctx: TickContext, closing: bool = False) -> GoalsEpochResult:
    completed, failed = await evaluate_scenarios(ctx, closing)
    reader = MetricReader(ctx.session, ctx.rules, ctx.epoch)
    earned = await evaluate_achievements(ctx, reader)
    await ctx.session.flush()
    breakdown = await score(ctx.session, ctx.rules, ctx.epoch, reader)
    await store_score(ctx.session, ctx.epoch, breakdown)
    ctx.count("achievements", len(earned))
    return GoalsEpochResult(tuple(completed), tuple(failed), tuple(earned), breakdown)
