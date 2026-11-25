from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.session import Database
from aerona.db.tables.divine_will import (
    DivineWillArtifactNodeRow,
    DivineWillArtifactRow,
    DivineWillArtifactVersionRow,
    DivineWillAttachmentRow,
    DivineWillChunkRow,
    DivineWillConfirmationRow,
    DivineWillCycleRow,
    DivineWillEventRow,
    DivineWillForecastRow,
    DivineWillHandleRow,
    DivineWillPlanRow,
    DivineWillPlanStepRow,
    DivineWillSessionRow,
)
from aerona.domain.enums.divine_will import (
    ArtifactFormat,
    ArtifactKind,
    ArtifactStatus,
    AttachmentKind,
    AttachmentStatus,
    ChunkSource,
    ConfirmationReason,
    ConfirmationStatus,
    CycleEventKind,
    CycleStatus,
    DivineWillMode,
    ForecastStatus,
    PlanStatus,
    StepImpact,
    StepStatus,
)
from aerona.rules.registry import Rules
from aerona.services.books import book_page, codex_markdown
from aerona.services.books.render import CodexLinks
from aerona.services.player.catalog import run_ledgered
from aerona.services.player.scope import PlayerScope
from tests.services.app.factories import Cosmos
from tests.services.app.test_books import MARKUP, SNAKE_WORD, enum_keys

LONG_BODY = "\n\n".join(f"Paragraph {index} of the long account of the Velari Folk." for index in range(1, 1201)) + "\n\nThe last line of the account."
ANSWER = "The Velari Folk now honour the Creator in every town."
QUESTION = "Tell me who the Velari Folk honour and set my mood."
THOUGHT = "First read the people, then act."
CLOSED_QUESTION = "What was the first age called?"
OLD_ANSWER = "It was the first age."
PEOPLE_TEXT = "Velari Folk entry"
HANDLE = "handle-one"
REFUSED = "The note was refused."
PAGE_BODY = "<h1>The Velari almanac</h1><p>Every season of the folk.</p>"


async def stirred(session: AsyncSession, world: Cosmos) -> dict[str, int]:
    acted = await run_ledgered(PlayerScope(session, Rules()), "creator:mood", {"contentment": 80})
    assert acted.ledger_entry_id is not None
    closed = DivineWillSessionRow(title="First counsel", opened_epoch=1, closed_epoch=2, closed_at=datetime(2026, 11, 1, tzinfo=UTC))
    active = DivineWillSessionRow(title="", opened_epoch=2)
    session.add_all([closed, active])
    await session.flush()
    old = DivineWillCycleRow(
        session_id=closed.id,
        ordinal=1,
        mode=DivineWillMode.ASK_LORE,
        epoch=1,
        status=CycleStatus.DONE,
        player_text=CLOSED_QUESTION,
        final_text="It was the first age.",
    )
    cycle = DivineWillCycleRow(
        session_id=active.id,
        ordinal=1,
        mode=DivineWillMode.COMMAND,
        epoch=2,
        status=CycleStatus.DONE,
        player_text=QUESTION,
        final_text=ANSWER,
        model="test-model",
        input_tokens=1200,
        output_tokens=300,
        steps=4,
    )
    session.add_all([old, cycle])
    await session.flush()
    session.add(DivineWillHandleRow(key=HANDLE, cycle_id=cycle.id, tool="read_node", query={"node_id": world.people.id, "page": 1}, total=12))
    session.add_all(
        [
            DivineWillEventRow(cycle_id=cycle.id, ordinal=1, kind=CycleEventKind.PLAYER, payload={"text": QUESTION}),
            DivineWillEventRow(cycle_id=cycle.id, ordinal=2, kind=CycleEventKind.THOUGHT, payload={"text": THOUGHT}),
            DivineWillEventRow(
                cycle_id=cycle.id, ordinal=3, kind=CycleEventKind.TOOL_CALL, tool="read_node", payload={"arguments": {"node_id": world.people.id}}
            ),
            DivineWillEventRow(cycle_id=cycle.id, ordinal=4, kind=CycleEventKind.TOOL_RESULT, tool="read_node", payload={"text": PEOPLE_TEXT}, handle=HANDLE),
            DivineWillEventRow(
                cycle_id=cycle.id,
                ordinal=5,
                kind=CycleEventKind.TOOL_RESULT,
                tool="perform_action",
                payload={"text": "The mood of the Creator is set.", "ledger_entry_id": acted.ledger_entry_id, "created_ids": [world.people.id]},
            ),
            DivineWillEventRow(cycle_id=cycle.id, ordinal=6, kind=CycleEventKind.TEXT, payload={"text": ANSWER}),
        ]
    )
    session.add(
        DivineWillConfirmationRow(
            cycle_id=cycle.id,
            action_id="creator:mood",
            input={"contentment": 80},
            reason=ConfirmationReason.COSTLY,
            preview={"essence": 40, "tallies": [{"operation": "update", "table": "creator", "count": 1}]},
            status=ConfirmationStatus.APPROVED,
            decided_at=datetime(2026, 11, 2, tzinfo=UTC),
            ledger_entry_id=acted.ledger_entry_id,
        )
    )
    story = DivineWillArtifactRow(
        title="The Long Account",
        kind=ArtifactKind.CHRONICLE,
        format=ArtifactFormat.MARKDOWN,
        status=ArtifactStatus.FINAL,
        language="english",
        mode=DivineWillMode.CREATIVE_WORK,
        tags=["folk", "account"],
        created_cycle_id=cycle.id,
        current_version=2,
    )
    page = DivineWillArtifactRow(
        title="The Almanac Page", kind=ArtifactKind.HTML_PAGE, format=ArtifactFormat.HTML, language="english", mode=DivineWillMode.CREATIVE_WORK, tags=[]
    )
    session.add_all([story, page])
    await session.flush()
    session.add_all(
        [
            DivineWillArtifactVersionRow(artifact_id=story.id, version=1, body="A first short draft.", summary="First draft", cycle_id=cycle.id),
            DivineWillArtifactVersionRow(artifact_id=story.id, version=2, body=LONG_BODY, summary="Written out in full", cycle_id=cycle.id),
            DivineWillArtifactVersionRow(artifact_id=page.id, version=1, body=PAGE_BODY, summary="The page"),
            DivineWillArtifactNodeRow(artifact_id=story.id, node_id=world.people.id),
        ]
    )
    plan = DivineWillPlanRow(cycle_id=cycle.id, artifact_id=story.id, title="Raise the folk", status=PlanStatus.DONE)
    session.add(plan)
    await session.flush()
    session.add_all(
        [
            DivineWillPlanStepRow(
                plan_id=plan.id,
                ordinal=1,
                title="Lift the mood of the folk",
                action_id="creator:mood",
                input={"contentment": 80},
                status=StepStatus.DONE,
                declared_impact=StepImpact.SAFE,
                ledger_entry_id=acted.ledger_entry_id,
                result_text="The mood rose.",
            ),
            DivineWillPlanStepRow(
                plan_id=plan.id,
                ordinal=2,
                title="Second step",
                action_id="creator:note",
                depends_on=[1],
                status=StepStatus.FAILED,
                error=REFUSED,
            ),
            DivineWillForecastRow(
                cycle_id=cycle.id,
                epochs=2,
                status=ForecastStatus.DONE,
                eta_seconds=70,
                interventions=[{"action_id": "creator:mood", "input": {"contentment": 80}}],
                report={"baseline_population": 5000, "intervened_population": 5300},
            ),
            DivineWillAttachmentRow(
                cycle_id=cycle.id,
                kind=AttachmentKind.DOCUMENT,
                filename="folk-notes.pdf",
                mime="application/pdf",
                size=2048,
                media_key="divine-will/folk-notes.pdf",
                status=AttachmentStatus.INDEXED,
                seen_by_model=True,
            ),
            DivineWillChunkRow(
                source=ChunkSource.ENTITY, source_id=str(world.people.id), node_id=world.people.id, text="Velari", tokens=3, vector=b"", digest=HANDLE
            ),
        ]
    )
    await session.flush()
    return {"entry": acted.ledger_entry_id, "plan": plan.id}


async def test_the_book_and_the_codex_hold_every_divine_will_record_in_full(database: Database, session: AsyncSession, rules: Rules, world: Cosmos) -> None:
    ids = await stirred(session, world)
    page = await book_page(database, session, rules)
    codex = await codex_markdown(session, rules, CodexLinks())
    for text in (page.html, codex):
        assert "The Divine Will" in text and "Writings of the Divine Will" in text
        assert "First counsel" in text and CLOSED_QUESTION in text
        assert QUESTION in text and ANSWER in text and THOUGHT in text
        assert "Command" in text and "Ask Lore" in text
        assert HANDLE in text and "12 items in all" in text
        assert f"ledger entry {ids['entry']}" in text
        assert "It spends much essence" in text and "Approved" in text
        assert "Raise the folk" in text and "Lift the mood of the folk" in text and REFUSED in text
        assert "intervened_population" not in text and "5300" in text
        assert "The Long Account" in text and "Written out in full" in text and "First draft" in text
        assert "Paragraph 1200 of the long account" in text and "The last line of the account." in text
        assert "folk-notes.pdf" in text and "Converted and indexed" in text
        assert "1 passage" in text
        assert sorted(set(SNAKE_WORD.findall(MARKUP.sub(" ", text))) & enum_keys()) == []
    assert "&lt;h1&gt;The Velari almanac&lt;/h1&gt;" in page.html
    assert PAGE_BODY in codex
    assert page.html.index("The Divine Will") < page.html.index('id="cosmos"')
    assert codex.index("### The Divine Will") < codex.index("## The Heavens")
    assert codex.index("## Writings of the Divine Will") < codex.index("## Records of the Cosmos")


async def test_divine_will_rows_never_spill_into_the_generic_records(database: Database, session: AsyncSession, rules: Rules, world: Cosmos) -> None:
    await stirred(session, world)
    codex = await codex_markdown(session, rules, CodexLinks())
    records = codex[codex.index("## Records of the Cosmos") :] if "## Records of the Cosmos" in codex else ""
    assert "Divine will" not in records
