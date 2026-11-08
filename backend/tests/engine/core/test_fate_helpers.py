from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.fate.facts import entities_in_text, usable
from aerona.agents.fate.name_check import renamed_item
from aerona.agents.fate.threads import thread_closable
from aerona.db.tables.lore import ThreadLinkRow, ThreadRow
from aerona.domain.enums.chronicle import ThreadLinkRole, ThreadStatus
from aerona.domain.enums.entity import EntityStatus
from aerona.prompts.schemas.shared import NamingItemOutput
from tests.engine.core.factories import CoreWorld, settlement, tuned_rules


async def test_things_named_in_a_text_are_found_by_their_whole_names(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Brookhold", world, world.regions[0])
    inside = await settlement(session, "Brook", world, world.regions[0])
    found = await entities_in_text(session, "Riders left Brookhold at dawn.", world.world.id, exclude=world.people.id)
    assert town in found and inside not in found
    assert await entities_in_text(session, "", world.world.id, exclude=0) == []
    assert usable(town) and not usable(None)
    town.status, town.end_epoch = EntityStatus.DESTROYED, 2
    assert not usable(town)


async def test_a_story_closes_once_it_has_advanced_or_lain_still_long_enough(session: AsyncSession, world: CoreWorld) -> None:
    rules = tuned_rules(fate={"zero_progress_close_epochs": 3})
    story = ThreadRow(epoch=1, text="An open story", status=ThreadStatus.OPEN, progress=0)
    session.add(story)
    await session.flush()
    assert not await thread_closable(session, rules, story, 2)
    assert await thread_closable(session, rules, story, 4)
    session.add(ThreadLinkRow(thread_id=story.id, entity_id=world.people.id, role=ThreadLinkRole.ADVANCED, epoch=2))
    await session.flush()
    assert await thread_closable(session, rules, story, 2)


def test_a_renamed_item_carries_its_new_name_into_its_description() -> None:
    item = NamingItemOutput.model_construct(
        id=1, name="Old Crown", subtype="crown", description="The Old Crown was found in the hills.", image_prompt="", motifs=[]
    )
    renamed = renamed_item(item, "Brass Circlet")
    assert renamed.name == "Brass Circlet" and "Brass Circlet" in renamed.description and "Old Crown" not in renamed.description
