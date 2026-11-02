from aerona.catalog.stats import max_essence
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.repositories.sons import SonRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import MessageRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import MessageIntent
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityType
from aerona.engine.primitives.numbers import clamp_percent
from aerona.services.gods import creator_mood
from aerona.services.player import guards
from aerona.services.player.chronicle import tell
from aerona.services.player.lines import ADDRESS_ORDERED, COMMAND_CLEARED, COMMANDED, DREAM_SENT, SON_PRAYER_ANSWERED
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action
from aerona.tools.son.kin import SpokenIntent, intent_delta
from aerona.tools.son.lines import MESSAGE_PHRASES

DREAMER_TYPES = frozenset(COMMUNITY_TYPES | {EntityType.MORTAL})


class SendDream(Command):
    entity_id: int
    text: str


class CommandSon(Command):
    son_id: int
    text: str = ""


class AddressSibling(Command):
    son_id: int
    sibling_id: int
    intent: SpokenIntent
    text: str


class AnswerPrayer(Command):
    message_id: int
    text: str = ""
    essence: int = 0


@player_action("dream", ActionKind.DREAM)
async def send_dream(scope: PlayerScope, command: SendDream) -> Effect:
    council = scope.rules.council
    target = guards.of_types(
        await guards.canon_entity(scope.session, command.entity_id), DREAMER_TYPES, "Only a thinking being (a community or a named mortal) can dream."
    )
    text = command.text.strip()
    if not council.dream_min_chars <= len(text) <= council.dream_max_chars:
        raise ValidationFailedError(
            f"A dream is between {council.dream_min_chars} and {council.dream_max_chars} characters "
            "(world rules council.dream_min_chars and council.dream_max_chars)."
        )
    creator = await scope.creator()
    spent = guards.charge(creator, scope.rules.balance.dream, "balance.dream")
    epoch = await scope.epoch()
    scope.session.add(MessageRow(epoch=epoch, sender_node_id=creator.id, recipient_node_id=target.id, intent=MessageIntent.DREAM, text=text))
    ctx = await scope.context("dream")
    message = await tell(ctx, DREAM_SENT, ids=[target.id], kind=ChronicleKind.DREAM, creator=creator.name, entity=target.name)
    return Effect(message, target.id, essence_spent=spent)


@player_action("command", ActionKind.COMMAND)
async def command_son(scope: PlayerScope, command: CommandSon) -> Effect:
    son = await guards.son(scope.session, command.son_id)
    text = command.text.strip()
    if text and not son.alive:
        raise ValidationFailedError(f"{son.name} is dead; dead sons take no commands.")
    son.standing_order = text or None
    son.order_absolute = False
    creator = await scope.creator()
    ctx = await scope.context("command")
    if not text:
        return Effect(await tell(ctx, COMMAND_CLEARED, son_id=son.id, kind=ChronicleKind.ORDER, creator=creator.name, son=son.name), son.id)
    scope.session.add(MessageRow(epoch=ctx.epoch, sender_node_id=creator.id, recipient_node_id=son.id, intent=MessageIntent.COMMAND, text=text))
    message = await tell(ctx, COMMANDED, son_id=son.id, kind=ChronicleKind.ORDER, creator=creator.name, son=son.name, text=text)
    return Effect(message, son.id)


async def _answer_son(scope: PlayerScope, prayer: MessageRow, son: SonRow, command: AnswerPrayer) -> Effect:
    actions = scope.rules.god_actions
    creator = await scope.creator()
    gift = guards.charge(creator, command.essence, "god_actions.prayer_essence_cap")
    text = command.text.strip()
    son.essence = min(max_essence(scope.rules, son.might), son.essence + gift)
    son.loyalty = clamp_percent(son.loyalty + (actions.prayer_reply_loyalty if text else 0) + gift // actions.prayer_essence_per_loyalty)
    son.existence = clamp_percent(son.existence + actions.prayer_existence)
    ctx = await scope.context("answer_son_prayer")
    prayer.answered = True
    prayer.is_read = True
    prayer.answered_epoch = ctx.epoch
    prayer.answer_essence = gift
    if text:
        scope.session.add(MessageRow(epoch=ctx.epoch, sender_node_id=creator.id, recipient_node_id=son.id, intent=MessageIntent.ANSWER, text=text))
    detail = f" and gave him {gift} essence" if gift else ""
    message = await tell(ctx, SON_PRAYER_ANSWERED, son_id=son.id, kind=ChronicleKind.PRAYER, creator=creator.name, son=son.name, gift=detail)
    return Effect(message, son.id, essence_spent=gift)


@player_action("answer_prayer", ActionKind.ANSWER_PRAYER)
async def answer_prayer(scope: PlayerScope, command: AnswerPrayer) -> Effect:
    prayer = await scope.session.get(MessageRow, command.message_id)
    creator = await scope.creator()
    if prayer is None or prayer.recipient_node_id != creator.id:
        raise NotFoundError("No such prayer to the Creator.")
    if prayer.answered:
        raise ValidationFailedError("This prayer was already answered.")
    cap = scope.rules.god_actions.prayer_essence_cap
    if not 0 <= command.essence <= cap:
        raise ValidationFailedError(f"A prayer can receive between 0 and {cap} essence (world rule god_actions.prayer_essence_cap).")
    son = await scope.session.get(SonRow, prayer.sender_node_id)
    if son is not None:
        return await _answer_son(scope, prayer, son, command)
    if await scope.session.get(EntityRow, prayer.sender_node_id) is None:
        raise ValidationFailedError("The one who prayed no longer exists.")
    entity = await creator_mood.answer_mortal_prayer(scope.session, scope.rules, prayer.id, command.text, command.essence)
    return Effect(f"{creator.name} heard {entity.name}'s prayer.", entity.id, essence_spent=command.essence)


@player_action("son:address_sibling", ActionKind.COMMAND)
async def address_sibling(scope: PlayerScope, command: AddressSibling) -> Effect:
    son = await guards.son(scope.session, command.son_id)
    sibling = await guards.son(scope.session, command.sibling_id)
    if son.id == sibling.id:
        raise ValidationFailedError("A son cannot address himself.")
    if not son.alive or not sibling.alive:
        raise ValidationFailedError("Only living sons can speak to each other.")
    text = command.text.strip()
    if not text:
        raise ValidationFailedError("Give the words the son must say.")
    delta = intent_delta(scope.rules, son.charisma, command.intent)
    value = await SonRepository(scope.session).change_relation(son.id, sibling.id, delta, None)
    epoch = await scope.epoch()
    scope.session.add(MessageRow(epoch=epoch, sender_node_id=son.id, recipient_node_id=sibling.id, intent=MessageIntent(command.intent.value), text=text))
    ctx = await scope.context("address_sibling")
    phrase = MESSAGE_PHRASES[command.intent.value]
    message = await tell(ctx, ADDRESS_ORDERED, son_id=son.id, kind=ChronicleKind.MESSAGE, son=son.name, phrase=phrase, sibling=sibling.name, message=text)
    return Effect(message, son.id, values={"relation": value, "delta": delta})
