import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import NotFoundError
from aerona.db.repositories.chronicle import ChronicleDraft, ChronicleRepository
from aerona.db.tables.ledger import LedgerEntryRow
from aerona.db.tables.lore import LexemeRow, ThreadRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.node import ActorKind
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
