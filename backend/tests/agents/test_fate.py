import pytest
from sqlalchemy import select

from aerona.agents.chronicler import complete_chronicle, record_age, write_chronicle
from aerona.agents.context.scope import load_scope
from aerona.agents.fate.judge import run_fate
from aerona.agents.fate.naming import name_pending_records
from aerona.agents.fate.rollback import roll_back_rejection
from aerona.agents.runtime import AgentRuntime
from aerona.db.ledger_capture import LedgerDraft, capture_changes
from aerona.db.repositories.entities import EntityDraft, EntityRepository
from aerona.db.session import Database
from aerona.db.tables.cosmos import CosmosRow
from aerona.db.tables.entities import CreationVerdictRow, EntityRow
from aerona.db.tables.epochs import EpochRow
from aerona.db.tables.ledger import LedgerEntryRow
from aerona.db.tables.lore import CanonFactRow, FateRewardRow, LexemeRow, ThreadRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import Verdict
from aerona.domain.enums.entity import EntityOrigin, EntityStatus, EntityType
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.world import FateMode
from aerona.domain.models.entity_stats import ItemStats
from aerona.prompts.schemas.fate import ChronicleOutput, FateJudgmentOutput, NamingsOutput, VerdictDecision
from aerona.rules.registry import Rules
from tests.agents.fakes import FakeModel
from tests.agents.outputs import chronicle, judgment, naming
from tests.agents.world import AgentWorld


async def test_accepted_verdict_applies_everything_with_the_marker(runtime: AgentRuntime, model: FakeModel, database: Database, world: AgentWorld) -> None:
    model.script(FateJudgmentOutput, judgment(world))
    marked: list[bool] = []

    async def marker(_session: object) -> None:
        marked.append(True)

    applied = await run_fate(runtime, 1, ["The rivers rose."], marker)
    async with database.read() as session:
        creation = await session.get(EntityRow, world.creation.id)
        pending = await session.get(EntityRow, world.pending.id)
        verdict = await session.get(CreationVerdictRow, world.creation.id)
        son = await session.get(SonRow, world.core.son.id)
        threads = list(await session.scalars(select(ThreadRow)))
        facts = list(await session.scalars(select(CanonFactRow).where(CanonFactRow.subject_entity_id == world.creation.id)))
        words = list(await session.scalars(select(LexemeRow).where(LexemeRow.word == "teska")))
        rewards = list(await session.scalars(select(FateRewardRow)))
    assert marked == [True]
    assert applied.fate_debt is None
    assert creation is not None and creation.fate_note == "It binds the salt to the stone."
    assert verdict is not None and verdict.verdict is Verdict.ACCEPTED
    assert pending is not None and pending.name == "Teskaro" and not pending.pending_name
    assert son is not None and son.fame == 5 and son.xp == 5 * 2
    assert [thread.text for thread in threads] == ["The Orrin Folk want the river back."]
    assert {fact.predicate for fact in facts} >= {"is made of", "was created by", "is located in"}
    assert len(words) == 1 and len(rewards) == 1


async def test_rejection_and_limbo(runtime: AgentRuntime, model: FakeModel, database: Database, world: AgentWorld) -> None:
    model.script(FateJudgmentOutput, judgment(world, VerdictDecision.REJECT))
    applied = await run_fate(runtime, 1, [])
    async with database.read() as session:
        creation = await session.get(EntityRow, world.creation.id)
    assert applied.rejected == ["Orrin Folk"]
    assert creation is not None and creation.status is EntityStatus.REJECTED


async def test_fix_without_description_becomes_debt(runtime: AgentRuntime, model: FakeModel, database: Database, world: AgentWorld) -> None:
    model.script(FateJudgmentOutput, judgment(world, VerdictDecision.FIX))
    applied = await run_fate(runtime, 1, [])
    async with database.read() as session:
        cosmos = (await session.scalars(select(CosmosRow))).one()
        verdict = await session.get(CreationVerdictRow, world.creation.id)
    assert applied.limbo == [world.creation.id]
    assert cosmos.fate_debt_epoch == 1
    assert verdict is not None and verdict.verdict is Verdict.LIMBO


async def test_failed_judgment_records_debt(runtime: AgentRuntime, model: FakeModel, database: Database, world: AgentWorld) -> None:
    model.script(FateJudgmentOutput, RuntimeError("overloaded"))
    applied = await run_fate(runtime, 1, [])
    assert applied.fate_debt == 1


async def test_fate_off_stores_unjudged_verdicts(runtime: AgentRuntime, model: FakeModel, database: Database, world: AgentWorld) -> None:
    async with database.write() as session:
        (await session.scalars(select(CosmosRow))).one().fate_mode = FateMode.OFF
    model.script(FateJudgmentOutput, judgment(world, VerdictDecision.REJECT))
    await run_fate(runtime, 1, [])
    async with database.read() as session:
        creation = await session.get(EntityRow, world.creation.id)
        verdict = await session.get(CreationVerdictRow, world.creation.id)
    assert creation is not None and creation.status is EntityStatus.CANON
    assert verdict is not None and verdict.verdict is Verdict.UNJUDGED


async def test_disabled_llm_keeps_creations_as_debt(database: Database, world: AgentWorld) -> None:
    runtime = AgentRuntime(database=database, model=FakeModel(enabled=False))
    applied = await run_fate(runtime, 1, [])
    assert applied.fate_debt == 1


async def test_naming_loop_names_and_cleans(runtime: AgentRuntime, model: FakeModel, database: Database, world: AgentWorld, rules: Rules) -> None:
    model.script(NamingsOutput, NamingsOutput(namings=[naming(world.pending.id, "Teskuu")]), NamingsOutput(namings=[naming(world.pending.id, "Teskara")]))
    report = await name_pending_records(runtime)
    async with database.read() as session:
        pending = await session.get(EntityRow, world.pending.id)
    assert report.named == 1
    assert pending is not None and pending.name == "Teskara"


async def test_chronicler_writes_and_records_a_unique_age(runtime: AgentRuntime, model: FakeModel, database: Database, rules: Rules, world: AgentWorld) -> None:
    async with database.write() as session:
        session.add(EpochRow(epoch=0, name="Age of Dry Wells"))
    model.script(ChronicleOutput, chronicle())
    written = await write_chronicle(runtime, 1, [])
    await complete_chronicle(runtime, written, 1)
    async with database.write() as session:
        row = await record_age(await load_scope(session, rules), written, 1)
    assert row.name == "Second Age of Dry Wells"
    assert row.chronicler_name == "Ehmel"


async def test_rejection_rollback_undoes_the_creating_ledger_entry(database: Database, world: AgentWorld) -> None:
    async with database.write() as session:
        son = await session.get(SonRow, world.core.son.id)
        assert son is not None
        before = son.essence
        draft = LedgerDraft(1, ActorKind.SON, son.id, son.name, "create_relic", ActionKind.CREATE_ENTITY, None)
        async with capture_changes(session) as capture:
            relic = await EntityRepository(session).create(
                EntityDraft(
                    name="Salt Crown",
                    entity_type=EntityType.ITEM,
                    description="A crown of white salt.",
                    stats=ItemStats(might=10),
                    power_level=1,
                    origin=EntityOrigin.SON,
                    birth_epoch=1,
                    world_id=world.core.world.id,
                    creator_son_id=son.id,
                )
            )
            son.essence -= 5
            entry_id = await capture.seal(draft)
    assert entry_id is not None
    async with database.write() as session:
        assert await roll_back_rejection(session, Rules(), relic.id)
    async with database.read() as session:
        entry = await session.get(LedgerEntryRow, entry_id)
        restored = await session.get(SonRow, world.core.son.id)
        rejected = await session.get(EntityRow, relic.id)
    assert entry is not None and entry.undone
    assert restored is not None and restored.essence == before
    assert rejected is not None and rejected.status is EntityStatus.REJECTED


async def test_rollback_failure_discards_verdict_rewards_and_marker(
    runtime: AgentRuntime, model: FakeModel, database: Database, world: AgentWorld, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def crash(_session: object, _rules: object, _entity_id: int) -> bool:
        raise RuntimeError("crash during rollback")

    monkeypatch.setattr("aerona.agents.fate.apply.roll_back_rejection", crash)
    model.script(FateJudgmentOutput, judgment(world, VerdictDecision.REJECT))
    marked: list[bool] = []

    async def marker(_session: object) -> None:
        marked.append(True)

    with pytest.raises(RuntimeError, match="crash during rollback"):
        await run_fate(runtime, 1, [], marker)
    async with database.read() as session:
        creation = await session.get(EntityRow, world.creation.id)
        verdict = await session.get(CreationVerdictRow, world.creation.id)
        threads = list(await session.scalars(select(ThreadRow)))
        cosmos = (await session.scalars(select(CosmosRow))).one()
    assert creation is not None and creation.status is EntityStatus.CANON
    assert verdict is None or verdict.verdict is not Verdict.REJECTED
    assert threads == []
    assert cosmos.fate_debt_epoch is None
