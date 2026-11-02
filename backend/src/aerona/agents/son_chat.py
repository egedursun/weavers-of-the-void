from dataclasses import dataclass

from sqlalchemy import and_, or_, select

from aerona.agents.ask import ask
from aerona.agents.context.scope import load_scope
from aerona.agents.context.son_memory import son_memory
from aerona.agents.council import member_of
from aerona.agents.roles import AgentRole
from aerona.agents.runtime import AgentRuntime
from aerona.agents.text import sanitize
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.lore import MessageRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.agent import MessageIntent
from aerona.domain.enums.son import SonStatus
from aerona.events.kinds import EventKind
from aerona.prompts import PromptId
from aerona.prompts.contexts.council import ChatLine, SonChatContext
from aerona.prompts.schemas.council import ChatAttitude, SonChatOutput

PERCENT = 100


@dataclass(frozen=True)
class ChatReply:
    reply: str
    attitude: ChatAttitude
    loyalty: int
    change: int


async def chat_with_son(runtime: AgentRuntime, son_id: int, text: str) -> ChatReply:
    runtime.require_llm("son chat")
    async with runtime.database.read() as session:
        rules = await runtime.rules(session)
        scope = await load_scope(session, rules)
        son = await session.get(SonRow, son_id)
        if son is None:
            raise NotFoundError("Son not found.")
        if son.status is SonStatus.DEAD:
            raise ValidationFailedError(f"{son.name} is dead; your voice does not reach his bones.")
        said = text.strip()[: rules.council.chat_max_chars]
        if not said:
            raise ValidationFailedError("Say something.")
        creator = scope.creator.id
        between = or_(
            and_(MessageRow.sender_node_id == creator, MessageRow.recipient_node_id == son.id),
            and_(MessageRow.sender_node_id == son.id, MessageRow.recipient_node_id == creator),
        )
        history = list(
            await session.scalars(
                select(MessageRow)
                .where(between, MessageRow.intent == MessageIntent.CHAT)
                .order_by(MessageRow.id.desc())
                .limit(rules.council.chat_history_messages)
            )
        )
        council = rules.council
        context = SonChatContext(
            lore_language=scope.cosmos.lore_language,
            rules=rules,
            member=member_of(rules, scope, son),
            world_name=scope.cosmos.name,
            creator_name=scope.creator.name,
            multi_world=scope.multi_world,
            appearance=son.personality.appearance[: council.chat_appearance_chars],
            fear=son.personality.fear[: council.chat_fear_secret_chars],
            secret=son.personality.secret[: council.chat_fear_secret_chars],
            memory=(await son_memory(scope, son))[: council.chat_memory_chars],
            history=[ChatLine(from_father=message.sender_node_id == creator, text=message.text) for message in reversed(history)],
            text=said,
        )
    output = await ask(
        runtime.model,
        rules,
        label=AgentRole.SON_CHAT,
        system=(PromptId.SON_CHAT_SYSTEM, context),
        user=(PromptId.SON_CHAT_USER, context),
        output=SonChatOutput,
        time_limit=rules.council.chat_timeout,
    )
    limit = rules.council.chat_loyalty_max_change
    change = max(-limit, min(limit, int(output.loyalty_change)))
    reply = sanitize(output.reply)
    async with runtime.database.write() as session:
        son = await session.get(SonRow, son_id)
        if son is None:
            raise NotFoundError("Son not found.")
        son.loyalty = max(0, min(PERCENT, son.loyalty + change))
        epoch = (await load_scope(session, rules)).epoch
        session.add(MessageRow(epoch=epoch, sender_node_id=creator, recipient_node_id=son.id, intent=MessageIntent.CHAT, text=said, is_read=True))
        session.add(
            MessageRow(epoch=epoch, sender_node_id=son.id, recipient_node_id=creator, intent=MessageIntent.CHAT, text=reply, is_read=True, answered=True)
        )
        loyalty = son.loyalty
    runtime.publish(EventKind.SON_CHAT_REPLIED, {"son_id": son_id, "attitude": output.attitude.value, "change": change})
    return ChatReply(reply, output.attitude, loyalty, change)
