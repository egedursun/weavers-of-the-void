import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.lore import MessageRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import MessageIntent
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.son import SonStatus
from aerona.rules.registry import Rules
from aerona.services.player import death, messages
from aerona.services.player.scope import PlayerScope
from tests.services.player.factories import PlayerWorld, action_kinds, make_entity, make_son


async def test_kill_and_resurrect_son(scope: PlayerScope, session: AsyncSession, world: PlayerWorld, rules: Rules) -> None:
    world.creator.essence = 1000
    son = await make_son(session, "Velkar", world.world.id)
    killed = await death.kill_son(scope, death.KillSon(son_id=son.id, reason="pride"))
    assert son.status is SonStatus.DEAD
    assert killed.essence_spent == rules.death.creator_kill_son_cost
    revived = await death.resurrect_son(scope, death.ResurrectSon(son_id=son.id))
    assert son.status is not SonStatus.DEAD
    assert revived.essence_spent == rules.balance.resurrection
    assert await action_kinds(session) == [ActionKind.KILL_SON, ActionKind.RESURRECT_SON]


async def test_take_life_is_certain(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    mortal = await make_entity(session, "Asha", EntityType.MORTAL, world_id=world.world.id)
    await death.take_life(scope, death.TakeLife(entity_id=mortal.id, how="by a falling star"))
    assert mortal.status is EntityStatus.DEAD
    with pytest.raises(ValidationFailedError):
        await death.take_life(scope, death.TakeLife(entity_id=mortal.id))


async def test_dream_validates_length_and_charges(scope: PlayerScope, session: AsyncSession, world: PlayerWorld, rules: Rules) -> None:
    mortal = await make_entity(session, "Asha", EntityType.MORTAL, world_id=world.world.id)
    with pytest.raises(ValidationFailedError):
        await messages.send_dream(scope, messages.SendDream(entity_id=mortal.id, text="hi"))
    outcome = await messages.send_dream(scope, messages.SendDream(entity_id=mortal.id, text="Walk to the sea."))
    assert outcome.essence_spent == rules.balance.dream
    message = await session.scalar(select(MessageRow).where(MessageRow.recipient_node_id == mortal.id))
    assert message is not None and message.intent is MessageIntent.DREAM


async def test_command_son_and_dead_refusal(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    son = await make_son(session, "Velkar", world.world.id)
    await messages.command_son(scope, messages.CommandSon(son_id=son.id, text="Guard the sea."))
    assert son.standing_order == "Guard the sea." and not son.order_absolute
    await messages.command_son(scope, messages.CommandSon(son_id=son.id))
    assert son.standing_order is None
    son.status = SonStatus.DEAD
    son.death_epoch = 1
    with pytest.raises(ValidationFailedError):
        await messages.command_son(scope, messages.CommandSon(son_id=son.id, text="Rise."))


async def test_answer_son_prayer(scope: PlayerScope, session: AsyncSession, world: PlayerWorld, rules: Rules) -> None:
    son = await make_son(session, "Velkar", world.world.id, essence=10)
    prayer = MessageRow(epoch=2, sender_node_id=son.id, recipient_node_id=world.creator.id, intent=MessageIntent.PRAYER, text="Help me.")
    session.add(prayer)
    await session.flush()
    loyalty = son.loyalty
    outcome = await messages.answer_prayer(scope, messages.AnswerPrayer(message_id=prayer.id, text="Be strong.", essence=20))
    assert prayer.answered
    assert son.essence == 30
    assert son.loyalty == loyalty + rules.god_actions.prayer_reply_loyalty + 20 // rules.god_actions.prayer_essence_per_loyalty
    assert outcome.essence_spent == 20
    with pytest.raises(ValidationFailedError):
        await messages.answer_prayer(scope, messages.AnswerPrayer(message_id=prayer.id))
    with pytest.raises(NotFoundError):
        await messages.answer_prayer(scope, messages.AnswerPrayer(message_id=9999))


async def test_answer_mortal_prayer(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    mortal = await make_entity(session, "Asha", EntityType.MORTAL, world_id=world.world.id)
    prayer = MessageRow(epoch=2, sender_node_id=mortal.id, recipient_node_id=world.creator.id, intent=MessageIntent.PRAYER, text="Rain.")
    session.add(prayer)
    await session.flush()
    await messages.answer_prayer(scope, messages.AnswerPrayer(message_id=prayer.id, essence=5))
    assert prayer.answered
    assert await action_kinds(session) == [ActionKind.ANSWER_PRAYER]
