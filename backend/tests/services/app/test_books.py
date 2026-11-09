import re
from dataclasses import replace

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import NotFoundError
from aerona.db.repositories.chronicle import ChronicleDraft, ChronicleRepository
from aerona.db.tables.cosmography import GalaxyRow
from aerona.db.tables.epochs import EpochRunRow
from aerona.db.tables.job import JobRow
from aerona.db.tables.ledger import LedgerChangeRow, LedgerEntryRow
from aerona.db.tables.lore import LexemeRow, ThreadRow
from aerona.db.tables.mind import AttributeRow, FacetRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.rule_override import RuleOverrideRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.meta import LedgerOperation
from aerona.domain.enums.mind import Attribute, Facet
from aerona.domain.enums.node import ActorKind
from aerona.domain.models.profiles import EntityDepth
from aerona.engine.cosmos.ladder import ensure_ladder
from aerona.rules.registry import Rules
from aerona.services.books import book_page, codex_markdown
from aerona.services.books.model import build_book, roman
from aerona.services.books.render import CodexLinks, render_book
from aerona.services.codex import cosmic_chronicle, guide_markdown, traveller_guide
from tests.services.app.factories import Cosmos, bond, make_entity, make_world


async def enrich(session: AsyncSession, world: Cosmos) -> int:
    language = await make_entity(session, "Velari Tongue", EntityType.LANGUAGE, world_id=world.world.id)
    await bond(session, world.people.id, language.id, BondKind.SPEAKS)
    session.add(LexemeRow(language_entity_id=language.id, word="vael|a", meaning="water", added_by_kind=ActorKind.SON, epoch=1))
    session.add(ThreadRow(epoch=1, text="Who rang the drowned bell?"))
    await ChronicleRepository(session).append(
        ChronicleDraft(epoch=1, kind=ChronicleKind.WAR, text="The Velari Folk went to war.", entity_ids=[world.people.id], world_id=world.world.id)
    )
    await session.flush()
    return language.id


def test_roman() -> None:
    assert roman(14) == "XIV"


async def test_full_book_and_codex(session: AsyncSession, rules: Rules, world: Cosmos) -> None:
    await enrich(session, world)
    other = await make_world(session, "Dusk")
    await make_entity(session, "Ashfield", EntityType.REGION, world_id=other.id)
    page = await book_page(session, rules)
    assert page.nonce in page.html
    assert "Velari Folk" in page.html
    assert 'id="entity-' in page.html
    assert "The Velari Folk went to war." in page.html
    assert "{#" not in page.html
    codex = await codex_markdown(session, rules, CodexLinks())
    assert codex.startswith("# Aerona")
    assert any(line.startswith("#") and line.endswith(" Dusk") for line in codex.splitlines())
    assert "| vael\\|a | noun |" not in codex
    assert "vael\\|a" in codex
    assert "## The Epochs" in codex
    assert "The Velari Folk went to war." in codex


async def test_single_entry_page(session: AsyncSession, rules: Rules, world: Cosmos) -> None:
    await enrich(session, world)
    page = await book_page(session, rules, entity_id=world.people.id)
    assert "In the chronicle" in page.html
    assert 'href="?entity=' in page.html or "Velari Folk" in page.html
    son_page = await book_page(session, rules, son_id=world.son.id)
    assert world.son.name in son_page.html
    with pytest.raises(NotFoundError):
        await book_page(session, rules, entity_id=99999)


async def test_empty_book(session: AsyncSession, rules: Rules) -> None:
    assert await build_book(session, rules) is None
    assert "There is no world yet." in render_book(None, rules).html
    assert (await codex_markdown(session, rules, CodexLinks())).strip() == "# There is no world yet"


async def test_traveller_guide_and_cosmic(session: AsyncSession, rules: Rules, world: Cosmos) -> None:
    await enrich(session, world)
    guide = await traveller_guide(session, rules, world.world.id)
    assert guide.peoples[0].name == "Velari Folk"
    assert guide.peoples[0].language == "Velari Tongue"
    text = guide_markdown(guide)
    assert text.startswith("**Ordinary world**")
    assert "**Peoples:**" in text
    cosmic = await cosmic_chronicle(session, rules)
    assert cosmic[0].worlds[0].headlines == ["The Velari Folk went to war."]


async def test_book_and_codex_write_the_creators_hand_and_fates(session: AsyncSession, rules: Rules, world: Cosmos) -> None:
    session.add(
        LedgerEntryRow(
            epoch=1,
            actor_kind=ActorKind.CREATOR,
            actor_node_id=world.creator.id,
            actor_name=world.creator.name,
            tool="miracle",
            action_kind=ActionKind.MIRACLE,
            input_summary="healed the Velari Folk",
            undone=True,
        )
    )
    await ChronicleRepository(session).append(ChronicleDraft(epoch=1, kind=ChronicleKind.CREATOR_HAND, text="The sky dimmed over the salt."))
    await session.flush()
    page = await book_page(session, rules)
    assert "The Creator&#39;s hand" in page.html or "The Creator's hand" in page.html
    assert "healed the Velari Folk" in page.html
    assert "(undone)" in page.html
    codex = await codex_markdown(session, rules, CodexLinks())
    assert "### The Creator's hand" in codex
    assert "The sky dimmed over the salt." in codex
    assert "**Fate**" in codex
    assert "- Status: active" in codex


async def test_book_is_never_truncated(session: AsyncSession, rules: Rules, world: Cosmos) -> None:
    other = await make_world(session, "Dusk")
    tight = replace(rules, server=replace(rules.server, cosmic_chronicle_default=1), guide=replace(rules.guide, people_list=0, danger_list=0))
    long_line = "The Velari Folk went to war " + "again and again " * 20
    for epoch in (1, 2, 3):
        for index in range(6):
            await ChronicleRepository(session).append(
                ChronicleDraft(epoch=epoch, kind=ChronicleKind.WAR, text=f"{long_line}{epoch}-{index}", entity_ids=[world.people.id], world_id=world.world.id)
            )
    await make_entity(session, "Ashfield", EntityType.REGION, world_id=other.id)
    await session.flush()
    assert len(await cosmic_chronicle(session, tight)) == 1
    assert (await traveller_guide(session, tight, world.world.id)).peoples == []
    book = await build_book(session, tight)
    assert book is not None
    assert [epoch.epoch for epoch in book.cosmic] == [1, 2, 3]
    headlines = book.cosmic[0].worlds[0].headlines
    assert len(headlines) == 6
    assert headlines[-1] == " ".join(f"{long_line}1-5".split())
    guide = next(article.guide for section in book.stars for article in section.worlds if article.world.id == world.world.id)
    assert [people.name for people in guide.peoples] == ["Velari Folk"]
    page = render_book(book, tight).html
    assert " ".join(f"{long_line}3-5".split()) in page


async def test_every_record_reaches_the_book_and_the_codex(session: AsyncSession, rules: Rules, world: Cosmos) -> None:
    await enrich(session, world)
    hero = await make_entity(session, "Orrin", EntityType.MORTAL, world_id=world.world.id)
    session.add(AttributeRow(node_id=hero.id, attribute=Attribute.ANALYTICAL_ABILITY, value=71))
    session.add(FacetRow(node_id=world.son.id, facet=Facet.CURIOSITY, value=33))
    session.add(RuleOverrideRow(namespace="ideas", key="slots", value=3))
    await session.flush()
    page = await book_page(session, rules)
    codex = await codex_markdown(session, rules, CodexLinks())
    for text in (page.html, codex):
        assert "Mind attributes" in text and "analytical ability" in text
        assert "Mind facets" in text and "curiosity" in text
        assert "Records of the Cosmos" in text and "Rule overrides" in text


RAW_DUMP = re.compile(r"[A-Za-z] None\b|\[\]|\{|\}")


async def test_records_and_the_ledger_never_dump_raw_rows(session: AsyncSession, rules: Rules, world: Cosmos) -> None:
    hero = await make_entity(session, "Orrin", EntityType.MORTAL, world_id=world.world.id)
    entry = LedgerEntryRow(
        epoch=1,
        actor_kind=ActorKind.CREATOR,
        actor_node_id=world.creator.id,
        actor_name=world.creator.name,
        tool="entity:edit",
        action_kind=ActionKind.MIRACLE,
    )
    session.add(entry)
    session.add(EpochRunRow(epoch=1, engine_since_chronicle_id=hero.id, engine_notes=[]))
    session.add(JobRow(id="job-1", kind="completion", status="succeeded", params={}, result={"failed": [], "items": [{"node": hero.id, "note": None}]}))
    await session.flush()
    session.add_all(
        [
            LedgerChangeRow(
                entry_id=entry.id,
                table_name="entities",
                row_key=f'{{"id": {hero.id}}}',
                operation=LedgerOperation.UPDATE,
                before={"id": hero.id, "name": "Orrin", "importance": 1, "created_at": "2026-01-01 00:00:00"},
                after={"id": hero.id, "name": "Orrin the Tall", "importance": 1, "created_at": "2026-01-01 00:00:00"},
            ),
            LedgerChangeRow(
                entry_id=entry.id,
                table_name="mind_attributes",
                row_key=f'{{"node_id": {hero.id}}}',
                operation=LedgerOperation.INSERT,
                after={"node_id": hero.id, "attribute": "analytical_ability", "value": 71},
            ),
        ]
    )
    await session.flush()
    book = await build_book(session, rules)
    assert book is not None
    assert "Ledger changes" not in [table.title for table in book.records]
    renamed, added = book.ledger_changes[entry.id]
    assert (renamed.verb, renamed.target, renamed.details) == ("Changed", "Orrin in entities", ["Name: Orrin → Orrin the Tall"])
    assert (added.verb, added.target) == ("Created", "Orrin in mind attributes")
    assert "Attribute: analytical ability" in added.details
    runs = next(table for table in book.records if table.title == "Epoch runs")
    assert "Orrin" not in [cell for row in runs.rows for cell in row]
    jobs = next(table for table in book.records if table.title == "Jobs")
    assert any("Items (" in cell and "Failed none" in cell for row in jobs.rows for cell in row)
    for table in book.records:
        for row in table.rows:
            assert not [cell for cell in row if RAW_DUMP.search(cell)], table.title
    page = render_book(book, rules).html
    assert "Orrin → Orrin the Tall" in page
    codex = await codex_markdown(session, rules, CodexLinks())
    assert "**Changed** Orrin in entities — Name: Orrin → Orrin the Tall" in codex


async def test_every_node_reference_in_the_book_is_named(session: AsyncSession, rules: Rules, world: Cosmos) -> None:
    await enrich(session, world)
    await ensure_ladder(session, rules)
    galaxy = await session.scalar(select(GalaxyRow))
    assert galaxy is not None
    galaxy.depth = EntityDepth(epoch=1, history="It turned first.")
    await session.flush()
    book = await build_book(session, rules)
    assert book is not None
    nodes = {node_id for (node_id,) in await session.execute(select(NodeRow.id))}
    unnamed = sorted(node_id for node_id in nodes if node_id not in book.names)
    assert unnamed == []
    codex = await codex_markdown(session, rules, CodexLinks())
    page = await book_page(session, rules)
    raw = sorted(set(re.findall(r"(?<![\w&])#\d+\b", codex)) | set(re.findall(r"(?<![\w&])#\d+\b", page.html)))
    assert raw == []
    assert codex.count("It turned first.") == 1
