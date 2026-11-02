import copy
from typing import Any

import pytest
from sqlalchemy import select

from aerona.agents.runtime import AgentRuntime
from aerona.core.errors import ValidationFailedError
from aerona.db.session import Database
from aerona.db.tables.entities import CreationVerdictRow
from aerona.db.tables.epochs import DeferredStepRow, EpochRunRow, EpochStepRow
from aerona.db.tables.lore import HistorianViewRow
from aerona.domain.enums.agent import Verdict
from aerona.domain.enums.epoch import DeferredStepKind, DeferredStepStatus, EpochPhase, EpochStepKind, EpochStepStatus
from aerona.epoch import retry
from aerona.prompts import PromptId, output_model
from aerona.prompts.schemas.base import OutputModel
from aerona.prompts.schemas.fate import FateJudgmentOutput, NamingsOutput, VerdictDecision
from tests.agents.fakes import FakeModel
from tests.agents.outputs import judgment, naming
from tests.agents.world import AgentWorld
from tests.prompts.payloads import PAYLOADS


def payload(prompt: PromptId, **changes: Any) -> OutputModel:
    data = copy.deepcopy(PAYLOADS[prompt])
    data.update(changes)
    return output_model(prompt).model_validate(data)


async def seed_run(database: Database) -> None:
    async with database.write() as session:
        session.add(EpochRunRow(epoch=1, phase=EpochPhase.FATE, started=True, finished=False, engine_notes=["The rivers rose."]))


async def step_status(database: Database, step: EpochStepKind) -> EpochStepStatus | None:
    async with database.read() as session:
        row = await session.get(EpochStepRow, (1, step))
        return row.status if row is not None else None


async def test_retry_fate_judges_and_marks_the_step(runtime: AgentRuntime, model: FakeModel, database: Database, world: AgentWorld) -> None:
    await seed_run(database)
    model.script(FateJudgmentOutput, judgment(world))
    result = await retry.retry_fate(runtime)
    async with database.read() as session:
        verdict = await session.get(CreationVerdictRow, world.creation.id)
    assert result["epoch"] == 1
    assert verdict is not None and verdict.verdict is Verdict.ACCEPTED
    assert await step_status(database, EpochStepKind.FATE_JUDGMENT) is EpochStepStatus.DONE


async def test_rejudge_debt_requires_a_debt(runtime: AgentRuntime, database: Database, world: AgentWorld) -> None:
    await seed_run(database)
    with pytest.raises(ValidationFailedError, match="no debt"):
        await retry.rejudge_debt(runtime)


async def test_rejudge_limbo_settles_limbo_records(runtime: AgentRuntime, model: FakeModel, database: Database, world: AgentWorld) -> None:
    await seed_run(database)
    model.script(FateJudgmentOutput, judgment(world, VerdictDecision.FIX), judgment(world))
    await retry.retry_fate(runtime)
    async with database.read() as session:
        first = await session.get(CreationVerdictRow, world.creation.id)
    assert first is not None and first.verdict is Verdict.LIMBO
    result = await retry.rejudge_limbo(runtime)
    async with database.read() as session:
        second = await session.get(CreationVerdictRow, world.creation.id)
    assert second is not None and second.verdict is Verdict.ACCEPTED
    assert result["limbo"] == 0


async def test_rejudge_limbo_without_limbo_is_refused(runtime: AgentRuntime, database: Database, world: AgentWorld) -> None:
    await seed_run(database)
    with pytest.raises(ValidationFailedError, match="limbo"):
        await retry.rejudge_limbo(runtime)


async def test_retry_voices_writes_views_again(runtime: AgentRuntime, model: FakeModel, database: Database, world: AgentWorld) -> None:
    await seed_run(database)
    output = payload(PromptId.VOICES_USER, views=[{"people_id": world.core.people.id, "historian": "Ehmel", "text": "We were first."}], beliefs=[])
    model.script(type(output), output)
    result = await retry.retry_voices(runtime)
    async with database.read() as session:
        views = list(await session.scalars(select(HistorianViewRow)))
    assert result["views"] == 1 and len(views) == 1
    assert await step_status(database, EpochStepKind.VOICES) is EpochStepStatus.DONE


async def test_retry_births_requeues_failed_steps(runtime: AgentRuntime, model: FakeModel, database: Database, world: AgentWorld) -> None:
    await seed_run(database)
    async with database.write() as session:
        session.add(DeferredStepRow(epoch=1, kind=DeferredStepKind.WORLD_BIRTH, status=DeferredStepStatus.FAILED, payload={}, attempts=1, error="boom"))
    model.script(NamingsOutput, NamingsOutput(namings=[naming(world.pending.id)]))
    result = await retry.retry_births(runtime)
    async with database.read() as session:
        step = (await session.scalars(select(DeferredStepRow))).one()
    assert step.attempts == 2
    assert result == {"epoch": 1, "born": 0}
    assert await step_status(database, EpochStepKind.WORLD_BIRTH) is EpochStepStatus.DONE
