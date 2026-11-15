from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog import god_lines
from aerona.catalog.achievements import ACHIEVEMENTS
from aerona.catalog.goal_metrics import CATEGORY_LABELS, METRICS
from aerona.catalog.scenarios import SCENARIOS, custom_description, custom_title
from aerona.constants.schema import TITLE_MAX_LENGTH
from aerona.constants.units import PERCENT
from aerona.core.errors import ConflictError, NotFoundError, ValidationFailedError
from aerona.db.tables.meta import AchievementRow, ScenarioRow, ScoreRow
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.meta import ACHIEVEMENT_TIERS, AchievementKey, GoalBasis, GoalCategory, GoalComparator, GoalMetric, ScenarioKey, ScenarioStatus
from aerona.domain.models.records import ScoreBreakdown
from aerona.engine.gods.goals import (
    GoalsEpochResult,
    ScenarioProgress,
    completed_tiers,
    custom_points,
    evaluate_goals,
    metric_total,
    preset_points,
    safe_measure,
    scenario_baseline,
    scenario_description,
    scenario_name,
    scenario_points,
    score,
)
from aerona.engine.gods.metrics import MetricReader
from aerona.engine.primitives.manual import manual_context
from aerona.rules.registry import Rules
from aerona.services.gods.context import require_creator


@dataclass(frozen=True)
class MetricView:
    metric: GoalMetric
    category: GoalCategory
    label: str
    value: int
    lower_is_better: bool


@dataclass(frozen=True)
class GoalCategoryView:
    category: GoalCategory
    label: str


@dataclass(frozen=True)
class ScenarioHistory:
    id: int
    status: ScenarioStatus
    name: str
    tier: int
    target: int
    start_epoch: int
    end_epoch: int | None
    deadline_epoch: int | None
    points: int
    awarded_points: int
    result: str | None


@dataclass(frozen=True)
class ScenarioView:
    key: ScenarioKey
    category: GoalCategory
    name: str
    description: str
    points: int
    next_tier: int
    default_target: int
    target_max: int
    history: tuple[ScenarioHistory, ...]


@dataclass(frozen=True)
class RunningScenario:
    id: int
    key: ScenarioKey
    name: str
    description: str
    tier: int
    target: int
    start_epoch: int
    deadline_epoch: int | None
    held: bool
    hold_epochs: int
    points: int
    metric: GoalMetric | None
    comparator: GoalComparator | None
    basis: GoalBasis | None
    title: str | None
    progress: ScenarioProgress


@dataclass(frozen=True)
class AchievementTierView:
    tier: int
    name: str
    description: str
    threshold: int
    points: int
    epoch: int | None


@dataclass(frozen=True)
class AchievementView:
    key: AchievementKey
    category: GoalCategory
    metric: GoalMetric
    title: str
    value: int
    tier: int
    percent: int
    tiers: tuple[AchievementTierView, ...]


@dataclass(frozen=True)
class GoalQuote:
    name: str
    description: str
    target: int
    start_value: int
    points: int


@dataclass(frozen=True)
class GoalsOverview:
    epoch: int
    categories: tuple[GoalCategoryView, ...]
    metrics: tuple[MetricView, ...]
    scenarios: tuple[ScenarioView, ...]
    running: tuple[RunningScenario, ...]
    achievements: tuple[AchievementView, ...]
    score: ScoreBreakdown
    score_history: tuple[tuple[int, int], ...]


def history_of(row: ScenarioRow) -> ScenarioHistory:
    return ScenarioHistory(
        row.id,
        row.status,
        scenario_name(row),
        row.tier,
        row.target,
        row.start_epoch,
        row.end_epoch,
        row.deadline_epoch,
        row.points,
        row.awarded_points,
        row.result,
    )


def achievement_view(rules: Rules, key: AchievementKey, value: int, earned: dict[tuple[AchievementKey, int], int]) -> AchievementView:
    spec = ACHIEVEMENTS[key]
    tiers = tuple(
        AchievementTierView(
            tier, spec.name(tier), spec.description(rules, tier), spec.threshold(rules, tier), spec.points(rules, tier), earned.get((key, tier))
        )
        for tier in ACHIEVEMENT_TIERS
    )
    reached = max((item.tier for item in tiers if item.epoch is not None), default=0)
    upcoming = next((item for item in tiers if item.epoch is None), None)
    if upcoming is None:
        percent = PERCENT
    else:
        floor = tiers[upcoming.tier - 2].threshold if upcoming.tier > 1 else 0
        span = max(1, upcoming.threshold - floor)
        percent = int(max(0, min(PERCENT, (value - floor) * PERCENT // span)))
    return AchievementView(key, spec.category, spec.metric, spec.title, value, reached, percent, tiers)


async def scenario_views(session: AsyncSession, rules: Rules, rows: list[ScenarioRow]) -> tuple[ScenarioView, ...]:
    views = []
    for key, spec in SCENARIOS.items():
        tier = await completed_tiers(session, key) + 1 if key is not ScenarioKey.CUSTOM else 1
        target = spec.target_for_tier(rules, tier)
        views.append(
            ScenarioView(
                key=key,
                category=spec.category,
                name=spec.name(target, tier),
                description=spec.description(rules, target),
                points=preset_points(rules, key, target, None) if key is not ScenarioKey.CUSTOM else rules.goals.custom_points,
                next_tier=tier,
                default_target=target,
                target_max=spec.target_max(rules) if key is not ScenarioKey.CUSTOM else rules.goals.custom_target_max,
                history=tuple(history_of(row) for row in rows if row.key is key),
            )
        )
    return tuple(views)


async def goals_overview(session: AsyncSession, rules: Rules) -> GoalsOverview:
    ctx = await manual_context(session, "goals_read", rules)
    rows = list(await session.scalars(select(ScenarioRow).order_by(ScenarioRow.id)))
    running = tuple(
        [
            RunningScenario(
                row.id,
                row.key,
                scenario_name(row),
                scenario_description(rules, row),
                row.tier,
                row.target,
                row.start_epoch,
                row.deadline_epoch,
                row.held,
                row.hold_epochs,
                row.points,
                row.metric,
                row.comparator,
                row.basis,
                row.title,
                await safe_measure(session, rules, row, ctx.epoch),
            )
            for row in rows
            if row.status is ScenarioStatus.RUNNING
        ]
    )
    reader = MetricReader(session, rules, ctx.epoch)
    metrics = tuple([MetricView(metric, spec.category, spec.label, await reader.value(metric), spec.lower_is_better) for metric, spec in METRICS.items()])
    earned = {(row.key, row.tier): row.epoch for row in await session.scalars(select(AchievementRow))}
    achievements = tuple([achievement_view(rules, key, await reader.value(spec.metric), earned) for key, spec in ACHIEVEMENTS.items()])
    history = tuple((row.epoch, row.total) for row in await session.scalars(select(ScoreRow).order_by(ScoreRow.epoch)))
    return GoalsOverview(
        epoch=ctx.epoch,
        categories=tuple(GoalCategoryView(category, label) for category, label in CATEGORY_LABELS.items()),
        metrics=metrics,
        scenarios=await scenario_views(session, rules, rows),
        running=running,
        achievements=achievements,
        score=await score(session, rules, ctx.epoch, reader),
        score_history=history,
    )


def checked_deadline(rules: Rules, epoch: int, deadline_epochs: int | None) -> int | None:
    if deadline_epochs is None:
        return None
    if not 1 <= deadline_epochs <= rules.goals.deadline_max_epochs:
        raise ValidationFailedError(f"A deadline must be between 1 and {rules.goals.deadline_max_epochs} epochs.")
    return epoch + deadline_epochs


def checked_title(title: str | None) -> str | None:
    text = (title or "").strip()
    if len(text) > TITLE_MAX_LENGTH:
        raise ValidationFailedError(f"A goal's name holds at most {TITLE_MAX_LENGTH} characters.")
    return text or None


def checked_preset_target(rules: Rules, key: ScenarioKey, target: int) -> int:
    top = SCENARIOS[key].target_max(rules)
    if not 1 <= target <= top:
        raise ValidationFailedError(f"The target of this goal must be between 1 and {top}.")
    return target


def checked_custom(rules: Rules, comparator: GoalComparator, basis: GoalBasis, target: int, hold_epochs: int) -> None:
    goals = rules.goals
    if basis is GoalBasis.GAINED and comparator is GoalComparator.AT_MOST:
        raise ValidationFailedError("A goal that counts what is gained must ask for at least its target.")
    low = 1 if basis is GoalBasis.GAINED else 0
    if not low <= target <= goals.custom_target_max:
        raise ValidationFailedError(f"The target must be between {low} and {goals.custom_target_max}.")
    if not 0 <= hold_epochs <= goals.custom_hold_max_epochs:
        raise ValidationFailedError(f"A hold must be between 0 and {goals.custom_hold_max_epochs} epochs.")


async def announce(session: AsyncSession, rules: Rules, row: ScenarioRow, reason: str) -> None:
    ctx = await manual_context(session, reason, rules)
    creator = await require_creator(session)
    line = god_lines.GOAL_SET
    await ctx.chronicle(ChronicleKind.CREATOR_HAND, line.render(creator=creator.name, name=scenario_name(row)), template_key=line.key)


async def start_scenario(session: AsyncSession, rules: Rules, key: ScenarioKey, target: int | None = None, deadline_epochs: int | None = None) -> GoalsOverview:
    ctx = await manual_context(session, "start_scenario", rules)
    spec = SCENARIOS.get(key)
    if spec is None or key is ScenarioKey.CUSTOM:
        raise NotFoundError("No such scenario.")
    running = await session.scalar(select(ScenarioRow.id).where(ScenarioRow.key == key, ScenarioRow.status == ScenarioStatus.RUNNING))
    if running is not None:
        raise ConflictError("This scenario is already running.")
    tier = await completed_tiers(session, key) + 1
    chosen = checked_preset_target(rules, key, target if target is not None else spec.target_for_tier(rules, tier))
    row = ScenarioRow(
        key=key,
        status=ScenarioStatus.RUNNING,
        start_epoch=ctx.epoch,
        tier=tier,
        target=chosen,
        deadline_epoch=checked_deadline(rules, ctx.epoch, deadline_epochs),
    )
    session.add(row)
    await scenario_baseline(session, rules, row, ctx.epoch)
    row.points = scenario_points(rules, row)
    await session.flush()
    await announce(session, rules, row, "start_scenario")
    return await goals_overview(session, rules)


async def start_custom(
    session: AsyncSession,
    rules: Rules,
    *,
    metric: GoalMetric,
    comparator: GoalComparator,
    basis: GoalBasis,
    target: int,
    hold_epochs: int = 0,
    deadline_epochs: int | None = None,
    title: str | None = None,
) -> GoalsOverview:
    ctx = await manual_context(session, "start_custom_goal", rules)
    checked_custom(rules, comparator, basis, target, hold_epochs)
    count = select(func.count(ScenarioRow.id)).where(ScenarioRow.key == ScenarioKey.CUSTOM, ScenarioRow.status == ScenarioStatus.RUNNING)
    if int(await session.scalar(count) or 0) >= rules.goals.custom_max_running:
        raise ConflictError(f"At most {rules.goals.custom_max_running} goals of your own may run at once.")
    row = ScenarioRow(
        key=ScenarioKey.CUSTOM,
        status=ScenarioStatus.RUNNING,
        start_epoch=ctx.epoch,
        metric=metric,
        comparator=comparator,
        basis=basis,
        target=target,
        hold_epochs=hold_epochs,
        deadline_epoch=checked_deadline(rules, ctx.epoch, deadline_epochs),
        title=checked_title(title),
    )
    session.add(row)
    await scenario_baseline(session, rules, row, ctx.epoch)
    row.points = scenario_points(rules, row)
    await session.flush()
    await announce(session, rules, row, "start_custom_goal")
    return await goals_overview(session, rules)


async def running_row(session: AsyncSession, scenario_id: int) -> ScenarioRow:
    row = await session.get(ScenarioRow, scenario_id)
    if row is None or row.status is not ScenarioStatus.RUNNING:
        raise NotFoundError("No such running scenario.")
    return row


async def edit_scenario(
    session: AsyncSession,
    rules: Rules,
    scenario_id: int,
    *,
    target: int,
    deadline_epochs: int | None,
    hold_epochs: int = 0,
    title: str | None = None,
) -> GoalsOverview:
    ctx = await manual_context(session, "edit_scenario", rules)
    row = await running_row(session, scenario_id)
    if row.key is ScenarioKey.CUSTOM:
        checked_custom(rules, row.comparator or GoalComparator.AT_LEAST, row.basis or GoalBasis.TOTAL, target, hold_epochs)
        row.hold_epochs = hold_epochs
        row.counter = min(row.counter, hold_epochs)
        row.title = checked_title(title)
        row.target = target
    else:
        row.target = checked_preset_target(rules, row.key, target)
    row.deadline_epoch = checked_deadline(rules, ctx.epoch, deadline_epochs)
    row.points = scenario_points(rules, row)
    await session.flush()
    return await goals_overview(session, rules)


async def hold_scenario(session: AsyncSession, rules: Rules, scenario_id: int, held: bool) -> GoalsOverview:
    row = await running_row(session, scenario_id)
    row.held = held
    await session.flush()
    return await goals_overview(session, rules)


async def abandon_scenario(session: AsyncSession, rules: Rules, scenario_id: int) -> GoalsOverview:
    ctx = await manual_context(session, "abandon_scenario", rules)
    row = await running_row(session, scenario_id)
    row.status = ScenarioStatus.ABANDONED
    row.end_epoch = ctx.epoch
    await session.flush()
    return await goals_overview(session, rules)


async def delete_scenario(session: AsyncSession, rules: Rules, scenario_id: int) -> GoalsOverview:
    row = await session.get(ScenarioRow, scenario_id)
    if row is None:
        raise NotFoundError("No such scenario.")
    await session.delete(row)
    await session.flush()
    return await goals_overview(session, rules)


async def quote_goal(
    session: AsyncSession,
    rules: Rules,
    key: ScenarioKey,
    *,
    target: int | None = None,
    deadline_epochs: int | None = None,
    metric: GoalMetric | None = None,
    comparator: GoalComparator = GoalComparator.AT_LEAST,
    basis: GoalBasis = GoalBasis.TOTAL,
    hold_epochs: int = 0,
) -> GoalQuote:
    ctx = await manual_context(session, "quote_goal", rules)
    deadline = None if deadline_epochs is None else ctx.epoch + max(1, deadline_epochs)
    if key is ScenarioKey.CUSTOM:
        chosen_metric = metric or GoalMetric.WORLDS
        start = await metric_total(session, rules, (chosen_metric,), ctx.epoch)
        wanted = target if target is not None else (1 if basis is GoalBasis.GAINED else start + 1)
        return GoalQuote(
            name=custom_title(chosen_metric, comparator, basis, wanted),
            description=custom_description(chosen_metric, comparator, basis, wanted, hold_epochs),
            target=wanted,
            start_value=start,
            points=custom_points(rules, comparator=comparator, basis=basis, start=start, target=wanted, hold_epochs=hold_epochs, deadline_epoch=deadline),
        )
    spec = SCENARIOS[key]
    tier = await completed_tiers(session, key) + 1
    wanted = target if target is not None else spec.target_for_tier(rules, tier)
    start = await metric_total(session, rules, spec.metrics, ctx.epoch) if spec.metrics else 0
    return GoalQuote(
        name=spec.name(wanted, tier),
        description=spec.description(rules, wanted),
        target=wanted,
        start_value=start,
        points=preset_points(rules, key, wanted, deadline),
    )


async def evaluate_now(session: AsyncSession, rules: Rules) -> GoalsEpochResult:
    return await evaluate_goals(await manual_context(session, "goals_evaluate", rules))
