from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog import god_lines
from aerona.catalog.achievements import ACHIEVEMENTS
from aerona.catalog.scenarios import SCENARIOS
from aerona.core.errors import ConflictError, NotFoundError
from aerona.db.tables.meta import AchievementRow, ScenarioRow, ScoreRow
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.meta import AchievementKey, ScenarioKey, ScenarioStatus
from aerona.domain.models.records import ScoreBreakdown
from aerona.engine.gods.goals import GoalsEpochResult, ScenarioProgress, evaluate_goals, safe_measure, scenario_baseline, score
from aerona.engine.primitives.manual import manual_context
from aerona.rules.registry import Rules
from aerona.services.gods.context import require_creator


@dataclass(frozen=True)
class ScenarioHistory:
    id: int
    status: ScenarioStatus
    start_epoch: int
    end_epoch: int | None
    result: str | None


@dataclass(frozen=True)
class ScenarioView:
    key: ScenarioKey
    name: str
    description: str
    points: int
    history: tuple[ScenarioHistory, ...]


@dataclass(frozen=True)
class RunningScenario:
    id: int
    key: ScenarioKey
    name: str
    start_epoch: int
    progress: ScenarioProgress


@dataclass(frozen=True)
class AchievementView:
    key: AchievementKey
    name: str
    description: str
    points: int
    earned: bool
    epoch: int | None


@dataclass(frozen=True)
class GoalsOverview:
    scenarios: tuple[ScenarioView, ...]
    running: tuple[RunningScenario, ...]
    achievements: tuple[AchievementView, ...]
    score: ScoreBreakdown
    score_history: tuple[tuple[int, int], ...]


async def goals_overview(session: AsyncSession, rules: Rules) -> GoalsOverview:
    ctx = await manual_context(session, "goals_read", rules)
    rows = list(await session.scalars(select(ScenarioRow).order_by(ScenarioRow.id)))
    scenarios = tuple(
        ScenarioView(
            key=key,
            name=spec.name(rules),
            description=spec.description(rules),
            points=spec.points(rules),
            history=tuple(ScenarioHistory(row.id, row.status, row.start_epoch, row.end_epoch, row.result) for row in rows if row.key is key),
        )
        for key, spec in SCENARIOS.items()
    )
    running = tuple(
        [
            RunningScenario(row.id, row.key, SCENARIOS[row.key].name(rules), row.start_epoch, await safe_measure(session, rules, row, ctx.epoch))
            for row in rows
            if row.status is ScenarioStatus.RUNNING
        ]
    )
    earned = {row.key: row.epoch for row in await session.scalars(select(AchievementRow))}
    achievements = tuple(
        AchievementView(key, spec.name(rules), spec.description(rules), spec.points(rules), key in earned, earned.get(key))
        for key, spec in ACHIEVEMENTS.items()
    )
    history = tuple((row.epoch, row.total) for row in await session.scalars(select(ScoreRow).order_by(ScoreRow.epoch)))
    return GoalsOverview(scenarios, running, achievements, await score(session, rules), history)


async def start_scenario(session: AsyncSession, rules: Rules, key: ScenarioKey) -> GoalsOverview:
    ctx = await manual_context(session, "start_scenario", rules)
    spec = SCENARIOS.get(key)
    if spec is None:
        raise NotFoundError("No such scenario.")
    running = await session.scalar(select(ScenarioRow.id).where(ScenarioRow.key == key, ScenarioRow.status == ScenarioStatus.RUNNING))
    if running is not None:
        raise ConflictError("This scenario is already running.")
    row = ScenarioRow(key=key, status=ScenarioStatus.RUNNING, start_epoch=ctx.epoch)
    session.add(row)
    await scenario_baseline(session, row)
    creator = await require_creator(session)
    line = god_lines.GOAL_SET
    await ctx.chronicle(ChronicleKind.CREATOR_HAND, line.render(creator=creator.name, name=spec.name(rules)), template_key=line.key)
    return await goals_overview(session, rules)


async def abandon_scenario(session: AsyncSession, rules: Rules, scenario_id: int) -> GoalsOverview:
    ctx = await manual_context(session, "abandon_scenario", rules)
    row = await session.get(ScenarioRow, scenario_id)
    if row is None or row.status is not ScenarioStatus.RUNNING:
        raise NotFoundError("No such running scenario.")
    row.status = ScenarioStatus.ABANDONED
    row.end_epoch = ctx.epoch
    await session.flush()
    return await goals_overview(session, rules)


async def evaluate_now(session: AsyncSession, rules: Rules) -> GoalsEpochResult:
    return await evaluate_goals(await manual_context(session, "goals_evaluate", rules))
