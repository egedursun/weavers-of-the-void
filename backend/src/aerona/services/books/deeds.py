from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.achievements import ACHIEVEMENTS
from aerona.catalog.goal_metrics import CATEGORY_LABELS, SCORE_PART_LABELS
from aerona.catalog.scenarios import SCENARIO_STATUS_LABELS, SCENARIOS, roman
from aerona.db.tables.meta import AchievementRow, ScenarioRow, ScoreRow
from aerona.domain.enums.meta import ACHIEVEMENT_TIERS, ScenarioKey, ScenarioStatus
from aerona.engine.gods.goals import scenario_description, scenario_name
from aerona.rules.registry import Rules


@dataclass(frozen=True)
class EarnedDeed:
    name: str
    category: str
    description: str
    tier: int
    points: int
    epoch: int

    @property
    def tier_label(self) -> str:
        return roman(self.tier)


@dataclass(frozen=True)
class TrialEntry:
    name: str
    category: str
    description: str
    state: str
    tier: int
    target: int
    start_epoch: int
    end_epoch: int | None
    deadline_epoch: int | None
    held: bool
    points: int
    awarded_points: int
    result: str | None

    @property
    def tier_label(self) -> str:
        return roman(self.tier)

    @property
    def span(self) -> str:
        return f"{self.start_epoch} to {self.end_epoch}" if self.end_epoch is not None else f"From {self.start_epoch}"

    @property
    def deadline(self) -> str:
        if self.deadline_epoch is None:
            return "None"
        return f"Epoch {self.deadline_epoch}" + (" (held)" if self.held else "")

    @property
    def reward(self) -> str:
        return f"{self.awarded_points} of {self.points}" if self.state == SCENARIO_STATUS_LABELS[ScenarioStatus.COMPLETED] else str(self.points)


@dataclass(frozen=True)
class ScorePart:
    label: str
    value: int


@dataclass(frozen=True)
class DeedsChapter:
    earned: list[EarnedDeed]
    tiers_total: int
    trials: list[TrialEntry]
    completed: int
    parts: list[ScorePart]
    scores: list[ScoreRow]

    @property
    def shown(self) -> bool:
        return bool(self.earned or self.trials or self.scores)

    @property
    def total(self) -> int:
        return self.scores[-1].total if self.scores else 0

    @property
    def earned_points(self) -> int:
        return sum(deed.points for deed in self.earned)


def trial_of(rules: Rules, row: ScenarioRow) -> TrialEntry:
    own = row.key is ScenarioKey.CUSTOM
    return TrialEntry(
        name=scenario_name(row),
        category="A goal of your own" if own else CATEGORY_LABELS[SCENARIOS[row.key].category],
        description=scenario_description(rules, row),
        state=SCENARIO_STATUS_LABELS[row.status],
        tier=row.tier,
        target=row.target,
        start_epoch=row.start_epoch,
        end_epoch=row.end_epoch,
        deadline_epoch=row.deadline_epoch,
        held=row.held,
        points=row.points,
        awarded_points=row.awarded_points,
        result=row.result,
    )


async def deeds_chapter(session: AsyncSession, rules: Rules) -> DeedsChapter:
    earned = [
        EarnedDeed(
            name=ACHIEVEMENTS[row.key].name(row.tier),
            category=CATEGORY_LABELS[ACHIEVEMENTS[row.key].category],
            description=ACHIEVEMENTS[row.key].description(rules, row.tier),
            tier=row.tier,
            points=ACHIEVEMENTS[row.key].points(rules, row.tier),
            epoch=row.epoch,
        )
        for row in await session.scalars(select(AchievementRow).order_by(AchievementRow.epoch, AchievementRow.key, AchievementRow.tier))
    ]
    trials = [trial_of(rules, row) for row in await session.scalars(select(ScenarioRow).order_by(ScenarioRow.id))]
    scores = list(await session.scalars(select(ScoreRow).order_by(ScoreRow.epoch)))
    latest = scores[-1].breakdown.parts if scores else {}
    return DeedsChapter(
        earned=earned,
        tiers_total=len(ACHIEVEMENTS) * len(ACHIEVEMENT_TIERS),
        trials=trials,
        completed=sum(1 for row in trials if row.state == SCENARIO_STATUS_LABELS[ScenarioStatus.COMPLETED]),
        parts=[ScorePart(label, latest[part]) for part, label in SCORE_PART_LABELS.items() if part in latest],
        scores=scores,
    )
