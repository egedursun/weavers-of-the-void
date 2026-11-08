from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.agency import CreationRewardRow
from aerona.db.tables.lore import ThreadRow
from aerona.domain.enums.chronicle import ThreadStatus
from aerona.domain.enums.entity import EntityType
from aerona.domain.models.entity_stats import ItemStats
from aerona.engine.gods.rewards import RewardDraft, adjust_reward, burn_after_undo, record_reward, snapshot
from tests.engine.core.factories import CoreWorld, entity, tuned_rules
from tests.engine.society.factories import son as make_son

RULES = tuned_rules(son_tools={"reject_take_back_pct": 50, "reject_reverts_thread": 0})


async def made(session: AsyncSession, world: CoreWorld, name: str) -> int:
    found = await entity(session, name, EntityType.ITEM, ItemStats(might=5), world_id=world.world.id)
    return found.id


async def thread(session: AsyncSession) -> ThreadRow:
    row = ThreadRow(epoch=1, text="An open story", status=ThreadStatus.OPEN, progress=2)
    session.add(row)
    await session.flush()
    return row


async def test_an_undone_creation_keeps_half_its_reward_pays_its_cost_and_moves_its_story_on(session: AsyncSession, world: CoreWorld) -> None:
    story = await thread(session)
    son = world.son
    son.xp, son.fame, son.essence = 0, 0, 20
    draft = RewardDraft(entity_id=await made(session, world, "Lost Crown"), son_id=son.id, epoch=1, xp=10, renown=6, essence=8, cost=3, thread_id=story.id)
    change = await burn_after_undo(session, RULES, draft, "Fate rejected")
    assert (son.xp, son.fame, son.essence) == (5, 3, 20 + 4 - 3)
    assert story.progress == 3 and change.thread == -1
    row = await session.get(CreationRewardRow, draft.entity_id)
    assert row is not None and row.taken_back_pct == 50 and not row.thread_reverted and row.reason == "Fate rejected"


async def test_a_partner_keeps_its_share_and_pays_its_own_cost(session: AsyncSession, world: CoreWorld) -> None:
    partner = await make_son(session, "Velm", world.world.id)
    partner.xp, partner.essence = 0, 10
    draft = RewardDraft(
        entity_id=await made(session, world, "Twin Crown"),
        son_id=world.son.id,
        epoch=1,
        xp=0,
        renown=0,
        essence=0,
        cost=0,
        partner_son_id=partner.id,
        partner_xp=8,
        partner_renown=4,
        partner_cost=6,
    )
    await burn_after_undo(session, RULES, draft, "Fate rejected")
    assert partner.xp == 4 and partner.essence == 4


async def test_taking_back_a_reward_returns_its_share_and_can_reopen_its_story(session: AsyncSession, world: CoreWorld) -> None:
    story = await thread(session)
    son = world.son
    son.xp = 50
    draft = RewardDraft(entity_id=await made(session, world, "Seal"), son_id=son.id, epoch=1, xp=20, renown=0, essence=0, cost=0, thread_id=story.id)
    row = record_reward(session, draft)
    await session.flush()
    assert snapshot(row) == draft
    change = await adjust_reward(session, RULES, draft.entity_id, 50, thread=True, reason="taken")
    assert change is not None and change.xp == 10 and son.xp == 40
    assert story.progress == 1 and row.thread_reverted
    assert await adjust_reward(session, RULES, draft.entity_id, 50, thread=True) is None
    assert await adjust_reward(session, RULES, draft.entity_id, 10, raise_only=True) is None
    back = await adjust_reward(session, RULES, draft.entity_id, 0, thread=False)
    assert back is not None and son.xp == 50 and story.progress == 2
    assert await adjust_reward(session, RULES, -1, 50) is None
