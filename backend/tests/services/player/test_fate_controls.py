from collections.abc import AsyncIterator

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.session import Database
from aerona.db.tables.entities import CreationVerdictRow
from aerona.db.tables.lore import HistorianViewRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import Verdict
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.job import JobStatus
from aerona.domain.models.entity_stats import ItemStats
from aerona.events.bus import EventBus
from aerona.jobs.manager import JobManager
from aerona.rules.registry import Rules
from aerona.rules.registry.costs import CostsRules
from aerona.services.player import catalog, fate_controls
from aerona.services.player.ports import CreativePorts
from aerona.services.player.runtime import PlayerRuntime
from aerona.services.player.scope import PlayerScope
from tests.polling import until
from tests.services.player.factories import PlayerWorld, action_kinds, make_entity, seed_player_world


class FakeFate:
    def __init__(self, fail: bool = False) -> None:
        self.calls: list[str] = []
        self.fail = fail

    async def record(self, name: str) -> dict[str, int]:
        self.calls.append(name)
        if self.fail:
            raise RuntimeError("model unavailable")
        return {"epoch": 1}

    async def retry_fate(self) -> dict[str, int]:
        return await self.record("retry_fate")

    async def rejudge_debt(self) -> dict[str, int]:
        return await self.record("rejudge_debt")

    async def rejudge_limbo(self) -> dict[str, int]:
        return await self.record("rejudge_limbo")

    async def retry_voices(self) -> dict[str, int]:
        return await self.record("retry_voices")

    async def retry_births(self) -> dict[str, int]:
        return await self.record("retry_births")

    async def audit_chronicle(self, epoch: int) -> dict[str, int]:
        return await self.record(f"audit_chronicle:{epoch}")


@pytest.fixture
async def runtime(database: Database) -> AsyncIterator[PlayerRuntime]:
    async with database.write() as seeding:
        await seed_player_world(seeding)
    bus = EventBus()
    jobs = JobManager(database, bus)
    yield PlayerRuntime(database, jobs, bus, CreativePorts(fate=FakeFate()))
    await jobs.shutdown()


async def finish(runtime: PlayerRuntime, job_id: object) -> JobStatus:
    assert isinstance(job_id, str)
    statuses: list[str] = []

    async def settled() -> bool:
        statuses.append((await runtime.jobs.get(job_id)).status)
        return statuses[-1] in (JobStatus.SUCCEEDED.value, JobStatus.FAILED.value)

    if not await until(settled):
        raise AssertionError("job did not finish")
    return JobStatus(statuses[-1])


async def test_every_fate_control_is_in_the_catalog(rules: Rules) -> None:
    ids = {
        "fate:retry",
        "fate:rejudge_debt",
        "fate:rejudge_limbo",
        "fate:override_verdict",
        "voices:retry",
        "voices:edit_view",
        "voices:delete_view",
        "births:retry",
    }
    assert ids <= {descriptor.id for descriptor in catalog.describe(rules)}


@pytest.mark.parametrize(
    ("action_id", "call"),
    [
        ("fate:retry", "retry_fate"),
        ("fate:rejudge_debt", "rejudge_debt"),
        ("fate:rejudge_limbo", "rejudge_limbo"),
        ("voices:retry", "retry_voices"),
        ("births:retry", "retry_births"),
    ],
)
async def test_job_controls_run_the_port(runtime: PlayerRuntime, rules: Rules, action_id: str, call: str) -> None:
    outcome = await catalog.run_job(runtime, rules, action_id, {})
    assert await finish(runtime, outcome.values["job_id"]) is JobStatus.SUCCEEDED
    fate = runtime.ports.fate
    assert isinstance(fate, FakeFate) and fate.calls == [call]


async def test_job_controls_charge_and_refund_on_failure(database: Database, runtime: PlayerRuntime) -> None:
    priced = Rules(costs=CostsRules(rejudge_fate=7))
    failing = PlayerRuntime(runtime.database, runtime.jobs, runtime.bus, CreativePorts(fate=FakeFate(fail=True)))
    async with database.read() as session:
        before = (await CosmosRepository(session).require_creator()).essence
    outcome = await fate_controls.retry_fate(failing, priced, fate_controls.NoInput())
    assert outcome.essence_spent == 7
    assert await finish(failing, outcome.values["job_id"]) is JobStatus.FAILED
    async with database.read() as session:
        assert (await CosmosRepository(session).require_creator()).essence == before


async def test_job_controls_need_the_language_model(database: Database, runtime: PlayerRuntime, rules: Rules) -> None:
    empty = PlayerRuntime(runtime.database, runtime.jobs, runtime.bus)
    with pytest.raises(ValidationFailedError):
        await fate_controls.retry_fate(empty, rules, fate_controls.NoInput())


async def test_override_to_reject_rolls_back_and_records(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    entity = await make_entity(session, "Salt Crown", EntityType.ITEM, world_id=world.world.id, stats=ItemStats(might=1))
    outcome = await fate_controls.override_verdict(scope, fate_controls.OverrideVerdict(entity_id=entity.id, choice=fate_controls.VerdictChoice.REJECT))
    verdict = await session.get(CreationVerdictRow, entity.id)
    assert entity.status is EntityStatus.REJECTED
    assert verdict is not None and verdict.verdict is Verdict.REJECTED
    assert outcome.target_node_id == entity.id
    assert ActionKind.OVERRIDE_VERDICT in await action_kinds(session)
    with pytest.raises(ValidationFailedError):
        await fate_controls.override_verdict(scope, fate_controls.OverrideVerdict(entity_id=entity.id, choice=fate_controls.VerdictChoice.ACCEPT))


async def test_override_to_accept_settles_limbo(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    entity = await make_entity(session, "Salt Crown", EntityType.ITEM, world_id=world.world.id, stats=ItemStats(might=1))
    session.add(CreationVerdictRow(entity_id=entity.id, epoch=entity.birth_epoch, verdict=Verdict.LIMBO, judged_epoch=1))
    await session.flush()
    await fate_controls.override_verdict(
        scope, fate_controls.OverrideVerdict(entity_id=entity.id, choice=fate_controls.VerdictChoice.ACCEPT, rationale="Fine.")
    )
    verdict = await session.get(CreationVerdictRow, entity.id)
    assert verdict is not None and verdict.verdict is Verdict.ACCEPTED and entity.status is EntityStatus.CANON
    assert entity.fate_note == "Fine."


async def test_historian_view_edit_and_delete(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    people = await make_entity(session, "Orrin Folk", EntityType.PEOPLE, world_id=world.world.id)
    view = HistorianViewRow(epoch=1, people_entity_id=people.id, historian="Ehmel", text="We were first.")
    session.add(view)
    await session.flush()
    await fate_controls.edit_view(scope, fate_controls.EditHistorianView(view_id=view.id, text="We came later."))
    assert view.text == "We came later."
    with pytest.raises(ValidationFailedError):
        await fate_controls.edit_view(scope, fate_controls.EditHistorianView(view_id=view.id, text="   "))
    await fate_controls.delete_view(scope, fate_controls.HistorianViewTarget(view_id=view.id))
    assert (await session.scalars(select(HistorianViewRow))).first() is None
    with pytest.raises(NotFoundError):
        await fate_controls.delete_view(scope, fate_controls.HistorianViewTarget(view_id=view.id))
