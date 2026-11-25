from datetime import UTC, datetime

from pydantic import TypeAdapter
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.divine_will import DivineWillForecastRow, DivineWillPlanRow, DivineWillPlanStepRow
from aerona.domain.enums.divine_will import ArtifactFormat, ArtifactKind, DivineWillMode, ForecastStatus, PlanStatus
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.node import NodeKind
from aerona.engine.interconnect.flows import FlowCategory
from aerona.prompts.tools.divine_will_ids import DivineWillToolId
from aerona.services.divine_will.artifacts import store_artifact
from aerona.tools.divine_will.library_ports import (
    AppliedIntervention,
    ArtifactDraft,
    FlowDeaths,
    ForecastLine,
    ForecastReport,
    ScenarioOutcome,
    TouchedNode,
    WarTally,
)
from tests.tools.divine_will_case import WillCase, WillWorld

W = DivineWillToolId
MOOD = "creator:mood"
BODY = "The first part of the account.\n\nThe second part of the account."
STEPS = [{"title": "Settle the mood", "action_id": MOOD, "input": {"contentment": 55}, "declared_impact": "safe"}]


async def written(session: AsyncSession, world: WillWorld) -> dict[str, int]:
    draft = ArtifactDraft(
        "Account of the Vale",
        ArtifactKind.CHRONICLE,
        ArtifactFormat.MARKDOWN,
        BODY,
        "en",
        DivineWillMode.CREATIVE_WORK,
        ("record",),
        (world.realm.people_id,),
        world.cycle_id,
    )
    return {"artifact": (await store_artifact(session, draft)).id}


async def planned(session: AsyncSession, world: WillWorld) -> dict[str, int]:
    plan = DivineWillPlanRow(title="Moods", cycle_id=world.cycle_id, status=PlanStatus.DRAFT, created_at=datetime.now(UTC))
    session.add(plan)
    await session.flush()
    session.add(DivineWillPlanStepRow(plan_id=plan.id, ordinal=1, title="Settle the mood", action_id=MOOD, input={"contentment": 55}))
    await session.flush()
    return {"plan": plan.id}


def outcome(population: int, stats: dict[str, int], text: str) -> ScenarioOutcome:
    return ScenarioOutcome(
        population=population,
        prosperity=41.5,
        communities=6,
        deaths=[FlowDeaths(FlowCategory.DEATH, 120)],
        wars=WarTally(ongoing=1, begun=1, ended=0),
        nodes=[TouchedNode(7, "Kessar Folk", NodeKind.ENTITY, True, EntityStatus.CANON, stats)],
        chronicle=[ForecastLine(3, 120, text)],
        seconds=12.5,
    )


async def foreseen(session: AsyncSession, world: WillWorld) -> dict[str, int]:
    report = ForecastReport(
        start_epoch=2,
        end_epoch=3,
        start_population=900,
        start_prosperity=40.0,
        start_communities=6,
        start_wars=0,
        interventions=[AppliedIntervention("entity:stat", "Set a stat", "The stat was set.", 0)],
        baseline=outcome(950, {"population": 400}, "The Kessar Folk stayed in the vale."),
        intervened=outcome(1400, {"population": 850}, "The Kessar Folk spread along the river."),
        seconds=14.0,
    )
    row = DivineWillForecastRow(
        cycle_id=world.cycle_id,
        epochs=1,
        status=ForecastStatus.DONE,
        eta_seconds=35,
        interventions=[{"action_id": "entity:stat", "input": {"entity_id": world.realm.people_id, "stat": "population", "value": 850}}],
        report={"epochs_done": 1, "error": "", **TypeAdapter(ForecastReport).dump_python(report, mode="json")},
        job_id="",
        created_at=datetime.now(UTC),
    )
    session.add(row)
    await session.flush()
    return {"forecast": row.id}


LIBRARY_CASES: dict[DivineWillToolId, WillCase] = {
    W.ARTIFACT_CREATE: WillCase(
        mode=DivineWillMode.CREATIVE_WORK,
        arguments=lambda world: {
            "title": "Notes on the Folk",
            "kind": "notes",
            "body": BODY,
            "language": "en",
            "tags": ["folk"],
            "node_ids": [world.realm.people_id],
        },
        expect=("Created artifact", "Notes on the Folk", "Kessar Folk"),
    ),
    W.ARTIFACT_READ: WillCase(
        mode=DivineWillMode.ASK_LORE,
        setup=written,
        arguments=lambda world: {"artifact_id": world.ids["artifact"]},
        expect=("Account of the Vale", "The second part of the account.", '"total": 2'),
    ),
    W.ARTIFACT_EDIT: WillCase(
        mode=DivineWillMode.CREATIVE_WORK,
        setup=written,
        arguments=lambda world: {
            "artifact_id": world.ids["artifact"],
            "edits": [{"replace": {"old": "first part", "new": "opening part"}}, {"append": "A closing part."}],
            "summary": "Clearer opening.",
        },
        expect=("2 new versions", "version 3"),
    ),
    W.ARTIFACT_UPDATE: WillCase(
        mode=DivineWillMode.CREATIVE_WORK,
        setup=written,
        arguments=lambda world: {"artifact_id": world.ids["artifact"], "status": "final", "tags": ["opening"]},
        expect=("final", "tags: opening"),
    ),
    W.ARTIFACT_LIST: WillCase(
        mode=DivineWillMode.ASK_LORE,
        setup=written,
        arguments=lambda _world: {"q": "second part", "kind": "chronicle"},
        expect=("1 matching artifact", "Account of the Vale"),
    ),
    W.PLAN_CREATE: WillCase(
        mode=DivineWillMode.PLAN,
        arguments=lambda _world: {"title": "Moods", "steps": STEPS},
        expect=("Saved plan", "Nothing runs until the player approves"),
    ),
    W.PLAN_READ: WillCase(
        mode=DivineWillMode.PLAN,
        setup=planned,
        arguments=lambda world: {"plan_id": world.ids["plan"]},
        expect=("Settle the mood", MOOD, '"contentment": 55'),
    ),
    W.PLAN_REVISE: WillCase(
        mode=DivineWillMode.PLAN,
        setup=planned,
        arguments=lambda world: {"plan_id": world.ids["plan"], "steps": [*STEPS, {**STEPS[0], "title": "Then once more", "depends_on": [1]}]},
        expect=("Saved plan", "2 steps"),
    ),
    W.FORECAST_ESTIMATE: WillCase(mode=DivineWillMode.FORESIGHT, arguments=lambda _world: {"epochs": 1}, expect=("should take about",)),
    W.FORECAST_RUN: WillCase(
        mode=DivineWillMode.FORESIGHT,
        arguments=lambda world: {
            "epochs": 1,
            "interventions": [{"action_id": "entity:stat", "input": {"entity_id": world.realm.people_id, "stat": "population", "value": 900}}],
        },
        expect=("Started forecast", "queued", "changes nothing in the world itself"),
    ),
    W.FORECAST_READ: WillCase(
        mode=DivineWillMode.FORESIGHT,
        setup=foreseen,
        arguments=lambda world: {"forecast_id": world.ids["forecast"]},
        expect=("Population: 900 at the start; 950 without the interventions; 1400 with the interventions (+450)", "spread along the river", "death 120"),
    ),
}
