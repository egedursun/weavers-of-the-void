from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.ledger_undo import creating_entry_id, undo_entry
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.agency import CreationRewardRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EntityStatus
from aerona.engine.gods.rewards import adjust_reward, burn_after_undo, snapshot
from aerona.rules.registry import Rules

REJECTED_REASON = "Fate rejected"


async def roll_back_rejection(session: AsyncSession, rules: Rules, entity_id: int) -> bool:
    reward = await session.get(CreationRewardRow, entity_id)
    draft = snapshot(reward) if reward is not None else None
    entry_id = await creating_entry_id(session, entity_id)
    if entry_id is None:
        if draft is not None:
            await adjust_reward(
                session,
                rules,
                entity_id,
                rules.son_tools.reject_take_back_pct,
                thread=bool(rules.son_tools.reject_reverts_thread),
                raise_only=True,
                reason=REJECTED_REASON,
            )
        return False
    cosmos = await CosmosRepository(session).require_cosmos()
    await undo_entry(session, entry_id, cosmos.epoch)
    entity = await session.get(EntityRow, entity_id, populate_existing=True)
    if entity is not None:
        entity.status = EntityStatus.REJECTED
    if draft is not None:
        await burn_after_undo(session, rules, draft, REJECTED_REASON)
    return True
