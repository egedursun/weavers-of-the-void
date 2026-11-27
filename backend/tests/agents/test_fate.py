import pytest
from sqlalchemy import select

from aerona.agents.chronicler import complete_chronicle, lost_chronicle_epochs, record_age, write_chronicle
from aerona.agents.context.scope import load_scope
from aerona.agents.fate.judge import run_fate
from aerona.agents.fate.naming import name_pending_records, requeue_engine_drafts
from aerona.agents.fate.rollback import roll_back_rejection
from aerona.agents.runtime import AgentRuntime
from aerona.constants.agents import LEGACY_ENGINE_DESCRIPTION_PREFIX
from aerona.db.ledger_capture import LedgerDraft, capture_changes
from aerona.db.repositories.entities import EntityDraft, EntityRepository
from aerona.db.session import Database
from aerona.db.tables.cosmos import CosmosRow
from aerona.db.tables.entities import CreationVerdictRow, EntityRow
from aerona.db.tables.epochs import EpochRow
from aerona.db.tables.ledger import LedgerEntryRow
from aerona.db.tables.lore import CanonFactRow, ChronicleRow, FateRewardRow, LexemeRow, ThreadRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import Verdict
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityFlag, EntityOrigin, EntityStatus, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.world import FateMode
from aerona.domain.models.entity_stats import ItemStats
from aerona.engine.primitives.manual import manual_context
from aerona.engine.recording.record import record
from aerona.prompts.schemas.fate import ChronicleOutput, FateJudgmentOutput, NamingsOutput, VerdictDecision
from aerona.rules.registry import Rules
from aerona.services.integrity.kept_name_texts import requeue_kept_names
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


async def test_legacy_engine_draft_left_unflagged_is_caught_and_written(runtime: AgentRuntime, model: FakeModel, database: Database, world: AgentWorld) -> None:
    async with database.write() as session:
        stray = await session.get(EntityRow, world.pending.id)
        assert stray is not None
        stray.pending_name = False
        stray.description = f"{LEGACY_ENGINE_DESCRIPTION_PREFIX} Peace Oath, a peace oath."
    model.script(NamingsOutput, NamingsOutput(namings=[naming(world.pending.id, "Teskara")]))
    report = await name_pending_records(runtime)
    async with database.read() as session:
        written = await session.get(EntityRow, world.pending.id)
    assert report.named == 1
    assert written is not None and not written.pending_name
    assert written.description.startswith("A tale the river people tell")


async def test_unwritten_draft_stays_pending_and_is_retried_next_time(runtime: AgentRuntime, model: FakeModel, database: Database, world: AgentWorld) -> None:
    model.script(NamingsOutput, NamingsOutput(namings=[]), NamingsOutput(namings=[]), NamingsOutput(namings=[]), NamingsOutput(namings=[]))
    report = await name_pending_records(runtime)
    async with database.read() as session:
        draft = await session.get(EntityRow, world.pending.id)
    assert report.named == 0 and report.left == 1
    assert draft is not None and draft.pending_name
    model.script(NamingsOutput, NamingsOutput(namings=[naming(world.pending.id, "Teskara")]))
    again = await name_pending_records(runtime)
    assert again.named == 1 and again.left == 0


async def test_fixed_name_survives_the_writer(runtime: AgentRuntime, model: FakeModel, database: Database, world: AgentWorld) -> None:
    async with database.write() as session:
        await EntityRepository(session).add_flag(world.pending.id, EntityFlag.FIXED_NAME)
    model.script(NamingsOutput, NamingsOutput(namings=[naming(world.pending.id, "Teskara")]))
    await name_pending_records(runtime)
    async with database.read() as session:
        written = await session.get(EntityRow, world.pending.id)
    assert written is not None and written.name == "Unnamed Tale" and not written.pending_name
    assert written.description.startswith("A tale the river people tell")


async def test_a_kept_name_is_marked_for_the_writer_and_its_text_calls_the_record_by_it(
    runtime: AgentRuntime, model: FakeModel, database: Database, world: AgentWorld
) -> None:
    async with database.write() as session:
        await EntityRepository(session).add_flag(world.pending.id, EntityFlag.NAME_FROM_LANGUAGE)
    renamed = naming(world.pending.id, "Teskara").model_copy(
        update={"description": "Teskara is a tale the river people tell. It ends with a well.", "image_prompt": "Teskara told beside a dry well"}
    )
    model.script(NamingsOutput, NamingsOutput(namings=[renamed]))
    await name_pending_records(runtime)
    assert any("Unnamed Tale" in call.prompt and "name kept" in call.prompt for call in model.calls)
    async with database.read() as session:
        written = await session.get(EntityRow, world.pending.id)
    assert written is not None and written.name == "Unnamed Tale"
    assert written.description.startswith("Unnamed Tale is a tale") and "Teskara" not in written.description
    assert written.image_prompt == "Unnamed Tale told beside a dry well"


async def test_kept_names_described_under_another_name_are_written_again_once(database: Database, world: AgentWorld) -> None:
    async with database.write() as session:
        await EntityRepository(session).add_flag(world.creation.id, EntityFlag.NAME_FROM_LANGUAGE)
        named = await session.get(EntityRow, world.creation.id)
        assert named is not None
        named.description = "Dorvel is a seer whose warnings were heard."
        assert await requeue_kept_names(session) == 1
        assert named.pending_name and named.naming_attempts == 0
        named.pending_name = False
        assert await requeue_kept_names(session) == 0


async def test_requeue_only_touches_engine_drafts(database: Database, world: AgentWorld) -> None:
    async with database.write() as session:
        assert await requeue_engine_drafts(session) == 0
        named = await session.get(EntityRow, world.creation.id)
        assert named is not None and not named.pending_name


async def test_chronicler_writes_and_records_a_unique_age(runtime: AgentRuntime, model: FakeModel, database: Database, rules: Rules, world: AgentWorld) -> None:
    async with database.write() as session:
        session.add(EpochRow(epoch=0, name="Age of Dry Wells"))
    model.script(ChronicleOutput, chronicle())
    written = await write_chronicle(runtime, 1, [])
    await complete_chronicle(runtime, written, 1)
    told = written.age_name.removeprefix("The ")
    written.narrative = f"In the {told} the wells ran low. {written.age_name} ended."
    async with database.write() as session:
        row = await record_age(await load_scope(session, rules), written, 1)
    assert row.name == "Second Age of Dry Wells"
    assert row.narrative == "In Second Age of Dry Wells the wells ran low. Second Age of Dry Wells ended."
    assert row.chronicler_name == "Ehmel"
    assert (row.year_start, row.year_end) == (0, rules.time.years_per_epoch - 1)


async def test_an_age_the_god_named_keeps_its_name_and_an_age_the_god_cleared_is_not_rewritten(
    runtime: AgentRuntime, model: FakeModel, database: Database, rules: Rules, world: AgentWorld
) -> None:
    async with database.write() as session:
        session.add(EpochRow(epoch=1, name="The Long Quiet"))
        ctx = await manual_context(session, "test_fate", rules)
        session.add(ChronicleRow(epoch=1, year=1, kind=ChronicleKind.WORLD, text="A line of the first age.", world_id=world.core.world.id))
        await record(
            ctx,
            "player.canon.epoch_edited",
            roles={IncidentRole.AUTHORITY: world.core.creator.id},
            facts={"epoch": 1, "fields": "narrative"},
            kind=ChronicleKind.CREATOR_HAND,
        )
        (await session.scalars(select(CosmosRow))).one().epoch = 3
    model.script(ChronicleOutput, chronicle())
    written = await write_chronicle(runtime, 1, [])
    written.narrative = f"{written.age_name} began when the river left."
    async with database.write() as session:
        scope = await load_scope(session, rules)
        row = await record_age(scope, written, 1)
        assert row.name == "The Long Quiet"
        assert row.narrative == "The Long Quiet began when the river left."
        row.narrative = None
        await session.flush()
        assert 1 not in await lost_chronicle_epochs(scope, 10)


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
