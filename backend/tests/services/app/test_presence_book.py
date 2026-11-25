from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.foreign_gods import ForeignGodDraft, ForeignGodRepository
from aerona.db.session import Database
from aerona.db.tables.changes import StateChangeRow
from aerona.db.tables.presence import PresenceEventRow, PresenceExchangeRow, PresenceSessionRow
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.presence import PresenceEventKind, PresenceExchangeStatus, PresenceGuise, PresenceRecord, PresenceStatus
from aerona.domain.models.stats import StatBlock
from aerona.rules.registry import Rules
from aerona.services.books import book_page, codex_markdown
from aerona.services.books.render import CodexLinks
from tests.services.app.factories import Cosmos, make_entity
from tests.services.app.test_books import MARKUP, SNAKE_WORD, enum_keys

KEPT_WORDS = {
    "son": ("Tell me what you saw at the shore.", "I saw the tide turn twice.", "The Creator asked me of the shore."),
    "god": ("Why do you stay apart from the pantheon?", "Because my people asked it of me.", "A voice without a name asked why I stay apart."),
    "mortal": ("What do you fear most?", "That the harvest fails again.", "In a dream a voice asked what I fear."),
}
UNKEPT_WORDS = ("Whisper the secret of the vault.", "The vault holds nothing but my oath.", "A secret never to be kept.")
LATE_WORDS = ("Speak again, now that you are dead.", "I remember the arrow and the cold.")
TOOL = "look_around"
TOOL_OUTCOME = "Saw the harbour of the region"


async def audience(
    session: AsyncSession, node_id: int, record: PresenceRecord, guise: PresenceGuise, words: tuple[str, ...], *, dead: bool = False, title: str = ""
) -> PresenceSessionRow:
    row = PresenceSessionRow(
        node_id=node_id,
        guise=guise,
        record=record,
        status=PresenceStatus.CLOSED,
        dead_when_summoned=dead,
        title=title,
        opened_epoch=2,
        closed_at=datetime(2026, 11, 20, tzinfo=UTC),
    )
    session.add(row)
    await session.flush()
    said = PresenceExchangeRow(
        session_id=row.id,
        ordinal=1,
        epoch=2,
        player_text=words[0],
        reply_text=words[1],
        remember_text=words[2] if len(words) > 2 else "",
        status=PresenceExchangeStatus.DONE,
        model="scripted",
        input_tokens=120,
        output_tokens=40,
        steps=2,
    )
    session.add(said)
    await session.flush()
    session.add_all(
        [
            PresenceEventRow(exchange_id=said.id, ordinal=1, kind=PresenceEventKind.TOOL_CALL, tool=TOOL, payload={"arguments": {"radius": 2}}),
            PresenceEventRow(exchange_id=said.id, ordinal=2, kind=PresenceEventKind.TOOL_RESULT, tool=TOOL, payload={"outcome": TOOL_OUTCOME}),
            PresenceEventRow(exchange_id=said.id, ordinal=3, kind=PresenceEventKind.TEXT, payload={"text": words[1]}),
        ]
    )
    await session.flush()
    return row


async def summoned(session: AsyncSession, world: Cosmos) -> dict[str, int]:
    god = await ForeignGodRepository(session).create(
        ForeignGodDraft(name="Ulmar", world_id=world.world.id, domain_primary=Domain.SEA, power=30, stats=StatBlock.uniform(40), created_epoch=1)
    )
    mortal = await make_entity(session, "Teskar Vane", EntityType.MORTAL, world_id=world.world.id, location_id=world.region.id)
    await audience(session, world.son.id, PresenceRecord.ON_RECORD, PresenceGuise.CREATOR, KEPT_WORDS["son"], title="At the shore")
    await audience(session, god.id, PresenceRecord.ON_RECORD, PresenceGuise.UNNAMED_POWER, KEPT_WORDS["god"])
    await audience(session, mortal.id, PresenceRecord.ON_RECORD, PresenceGuise.DREAM_VOICE, KEPT_WORDS["mortal"])
    await audience(session, mortal.id, PresenceRecord.ON_RECORD, PresenceGuise.ORDINARY, LATE_WORDS, dead=True)
    await audience(session, world.son.id, PresenceRecord.OFF_RECORD, PresenceGuise.CREATOR, UNKEPT_WORDS)
    await audience(session, mortal.id, PresenceRecord.OFF_RECORD, PresenceGuise.DREAM_VOICE, UNKEPT_WORDS)
    return {"god": god.id, "mortal": mortal.id}


async def test_every_speaker_entry_holds_its_audiences_on_the_record_and_never_off_it(
    database: Database, session: AsyncSession, rules: Rules, world: Cosmos
) -> None:
    await summoned(session, world)
    page = await book_page(database, session, rules)
    codex = await codex_markdown(session, rules, CodexLinks())
    for text in (page.html, codex):
        assert "Audiences" in text
        for words in KEPT_WORDS.values():
            assert all(line in text for line in words)
        assert all(line in text for line in LATE_WORDS)
        assert "At the shore" in text
        assert "Its Creator, revealed" in text and "A divine presence that gave no name" in text and "A voice in a dream" in text
        assert "Someone of its own world, nothing divine" in text
        assert "On the record: kept for good and remembered" in text
        assert "Summoned from death" in text
        assert "Tool call" in text and "Tool result" in text and TOOL_OUTCOME in text
        assert "What Teskar Vane kept in memory" in text and "Teskar Vane answered" in text
        assert "Ulmar answered" in text
        assert all(line not in text for line in UNKEPT_WORDS)
        assert "Off the record" not in text
        assert "presence sessions record" not in text and "presence exchanges record" not in text and "presence events record" not in text
        assert sorted(set(SNAKE_WORD.findall(MARKUP.sub(" ", text))) & enum_keys()) == []


async def test_each_audience_sits_in_its_own_speaker_entry(database: Database, session: AsyncSession, rules: Rules, world: Cosmos) -> None:
    ids = await summoned(session, world)
    codex = await codex_markdown(session, rules, CodexLinks())
    son_at = codex.index(f'<a id="son-{world.son.id}"></a>')
    god_at = codex.index(f'<a id="foreign-god-{ids["god"]}"></a>')
    mortal_at = codex.index(f'<a id="entity-{ids["mortal"]}"></a>')
    assert codex.index(KEPT_WORDS["son"][0]) > son_at
    assert codex.index(KEPT_WORDS["god"][0]) > god_at
    assert codex.index(KEPT_WORDS["mortal"][0]) > mortal_at
    records = codex[codex.index("## Records of the Cosmos") :] if "## Records of the Cosmos" in codex else ""
    assert "Presence" not in records


async def test_no_audience_leaves_a_trace_in_the_record_of_changes(session: AsyncSession, world: Cosmos) -> None:
    await summoned(session, world)
    tables = (PresenceSessionRow.__tablename__, PresenceExchangeRow.__tablename__, PresenceEventRow.__tablename__)
    traced = await session.scalar(select(func.count()).select_from(StateChangeRow).where(StateChangeRow.table_name.in_(tables)))
    assert traced == 0
